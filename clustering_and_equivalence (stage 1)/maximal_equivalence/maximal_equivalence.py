from typing import Tuple, List, Callable, Dict, Set, Iterable
from pysat.formula import CNF
from pysat.solvers import Solver
from pysat.examples.lsu import LSU
from threading import Timer
import time
import itertools
from collections import deque 

from normalisation import r1cs_norm

from utilities.utilities import _signal_data_from_cons_list, getvars, count_ints

from r1cs_scripts.circuit_representation import Circuit
from comparison_v2.constraint_encoding_v2 import encode_classes_v2

from maximal_equivalence.iterated_fingerprints_with_pausing import iterated_fingerprints_w_reverting, coefficient_only_fingerprinting

# TODO: tomorrow

def maximum_equivalence(
        in_pair: List[Tuple[str, Circuit]],
        test_data: Dict[str, any] = {},
        debug: bool = False,
        fingerprints_to_normi: Dict[str, Dict[int, List[int]]] | None = None,
        fingerprints_to_signals: Dict[str, Dict[int, List[int]]] | None = None,
        solver_timeout: float | None = None
        ) -> Dict[str, any]:
    
    names = [in_pair[0][0], in_pair[1][0]]

    for key, init in [("result", None), ("timing", {}), ("result_explanation", None), ("formula_size", None), ("group_sizes", {})]:
        test_data[key] = init

    S1 = in_pair[0][1]
    S2 = in_pair[1][1]
    start = time.time()
    last_time = start

    # No preprocessing here as we no longer care about inputs/outputs

    try: 
        # N = S1.nConstraints
        # K = S1.nWires

        # for lval, rval, val_name,  in [
        #     (S1.nWires, S2.nWires, "wires"), (S1.nConstraints, S2.nConstraints, "constraints"),(S1.nPubOut, S2.nPubOut, "output constraints"), 
        #     (S1.nPubIn + S1.nPrvIn, S2.nPubIn + S2.nPrvIn, "input constraints")]:
        #     if lval != rval: raise AssertionError(f"Different number of {val_name} in circuits: S1 has {lval}, S2 has {rval}")

        assumptions = set([])
        formula = CNF()

        # the norms for each constraint
        normalised_constraints = { name : [] for name in names}
        normi_to_coni = {name : [] for name in names}

        def _normalised_constraint_building_step(name, con):
            coni, cons = con
            norms = r1cs_norm(cons)
            normalised_constraints[name].extend(norms)
            normi_to_coni[name].extend(coni for _ in range(len(norms)))

        deque(
            maxlen=0,
            iterable = itertools.starmap(_normalised_constraint_building_step, itertools.chain(*itertools.starmap(lambda name, circ : itertools.product([name], enumerate(circ.constraints)), in_pair)))
        )

        ## parameters deal with signals in no constraint (i.e. used input signal case)
        signal_to_normi = {name: _signal_data_from_cons_list(normalised_constraints[name], signal_to_cons=[[] for _ in range(circ.nWires)], is_dict=False) for name, circ in in_pair}

        norm_signal_data_calculation_time = time.time()
        test_data["timing"]["norm_signal_data_calculation"] = norm_signal_data_calculation_time - last_time
        last_time = norm_signal_data_calculation_time

        # if len(normalised_constraints[names[0]]) != len(normalised_constraints[names[1]]): 
        #     raise AssertionError(f"EE: Different number of normalised constraints, {names[0]} had {len(normalised_constraints[names[0]])} where {names[1]} had {len(normalised_constraints[names[1]])}")

        if fingerprints_to_normi is None: 
            fingerprints_to_normi = coefficient_only_fingerprinting(names, normalised_constraints)
        # signals initially classed on input / output / neither
    
        if fingerprints_to_signals is None:
            fingerprints_to_signals = {name: { 0: [0], 1 : list(range(1, circ.nWires))} for name, circ in in_pair}

        # encode initial fingerprints but norms now have signal class in norm
        fingerprints_to_normi, fingerprints_to_signals, _, signal_to_fingerprints = iterated_fingerprints_w_reverting(
            names, in_pair, normalised_constraints, signal_to_normi, fingerprints_to_normi, fingerprints_to_signals, return_index_to_fingerprint=True,
            initial_mode = False
        )

        ## SatEncoding needs same classes

        fingerprints_key_intersection = set(fingerprints_to_normi[names[0]].keys()).intersection(fingerprints_to_normi[names[1]].keys())
        signals_key_intersection = set(fingerprints_to_signals[names[0]].keys()).intersection(fingerprints_to_signals[names[1]].keys())

        fingerprints_to_normi = {name: {key : fingerprints_to_normi[name][key] for key in fingerprints_key_intersection} for name in names}
        fingerprints_to_signals = {name: {key : fingerprints_to_signals[name][key] for key in signals_key_intersection} for name in names}

        back_and_forth_fingerprinting_time = time.time()
        test_data["timing"]["back_and_forth_fingerprinting"] = back_and_forth_fingerprinting_time - last_time
        last_time = back_and_forth_fingerprinting_time

        if debug: print("fingerprinting took : ", test_data["timing"]["back_and_forth_fingerprinting"] )

        ints = count_ints(map(len, fingerprints_to_normi[names[0]].values()))
        test_data["group_sizes"]["post_back_and_forth"] = {
                "sqr_weight": sum([x[0]**2 * x[1] for x in ints]),
                "sizes": [x[0] for x in ints],
                "counts": [x[1] for x in ints]
            }

        formula, _, norm_assignment, signal_assignment = encode_classes_v2(names, normalised_constraints, fingerprints_to_normi, signal_to_fingerprints, fingerprints_to_signals, weighted_cnf=True)
        test_data["formula_size"] = len(formula.hard) + len(formula.soft)

        solver = LSU(formula, solver='glucose4' if solver_timeout is not None else 'cadical195', expect_interrupt=solver_timeout is not None, verbose=debug, incr=solver_timeout is not None)
        # solver.oracle.solve_limited(expect_interrupt=solver.expect_interrupt) ## For some reason, running the oracle once here (which is done in the solve loop) makes it work??

        encoding_time = time.time()
        test_data["timing"]["encoding_time"] = encoding_time - last_time
        if debug: print("encoding took : ", test_data["timing"]["encoding_time"], " and formula size: ", test_data["formula_size"] )

        if solver_timeout is not None:
            timer = Timer(interval = solver_timeout, function = lambda lsu : lsu.interrupt(), args = [solver]) ## needs to be passed as an argument for some reason. Testing with solver.interrupt() gave weird behaviour -- TODO: understand
            timer.start()

        solver.solve()
        if solver_timeout is not None: timer.cancel()

        try:
            model = list(solver.get_model())
        except AttributeError:
            return [], []

        solving_time = time.time()
        test_data["timing"]["solving_time"] = solving_time - encoding_time
        test_data["timing"]["total_time"] = solving_time - start

        if debug: print("solving took : ", test_data["timing"]["solving_time"] )

        # TODO: make more efficient
        norm_vals = { val : True for val in itertools.chain(*map(lambda key : norm_assignment.assignment[key].values(), norm_assignment.assignment.keys()))}
        signal_vals = { val : True for val in itertools.chain(*map(lambda key : signal_assignment.assignment[key].values(), signal_assignment.assignment.keys()))}

        norm_pairs = list(itertools.chain( 
                # norm pairs from uniquely identified norms
             map(lambda key : (fingerprints_to_normi[names[0]][key][0], fingerprints_to_normi[names[1]][key][0]), filter(lambda key : len(fingerprints_to_normi[names[0]][key]) == 1 and len(fingerprints_to_normi[names[1]].setdefault(key, [])) == 1, fingerprints_to_normi[names[0]].keys()))
            , # norm pairs from MaxSAT solver
            map(norm_assignment.get_inv_assignment, filter(lambda lit : norm_vals.setdefault(lit, False), filter(lambda x : x > 0, model))) 
        ))
        signal_pairs = list(map(signal_assignment.get_inv_assignment, filter(lambda lit : signal_vals.setdefault(lit, False), filter(lambda x : x > 0, model))))

        coni_pairs = list(set(map(lambda pair : tuple(normi_to_coni[names[i]][pair[i]] for i in range(2)), norm_pairs)))

        return coni_pairs, signal_pairs

        early_exit(fingerprints_to_normi)
        early_exit(fingerprints_to_signals)

        back_and_forth_fingerprinting_time = time.time()
        test_data["timing"]["back_and_forth_fingerprinting"] = back_and_forth_fingerprinting_time - last_time
        last_time = back_and_forth_fingerprinting_time

        ints = count_ints(map(len, fingerprints_to_normi[names[0]].values()))
        test_data["group_sizes"]["post_back_and_forth"] = {
                "sqr_weight": sum([x[0]**2 * x[1] for x in ints]),
                "sizes": [x[0] for x in ints],
                "counts": [x[1] for x in ints]
            }
        # now do label passing for constraints

        formula, assumptions = encode_classes_v2(names, normalised_constraints, fingerprints_to_normi, signal_to_fingerprints, fingerprints_to_signals)

        test_data["formula_size"] = len(formula.clauses)
        solver = Solver(name='cadical195', bootstrap_with=formula)

        encoding_time = time.time()

        test_data["timing"]["encoding_time"] = encoding_time - last_time

        result = solver.solve(assumptions)
        solving_time = time.time()

        test_data["result"] = result
        test_data["result_explanation"] = "" if result else "Unsatisfiable Formula"

        test_data["timing"]["solving_time"] = solving_time - encoding_time
        test_data["timing"]["total_time"] = solving_time - start 

        if debug: print("Finished encoding                                     ", end='\r')

    except AssertionError as e:
        print(e)
        test_data["result"] = False
        test_data["result_explanation"] = repr(e)
    
    return test_data