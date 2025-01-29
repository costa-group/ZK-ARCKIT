from typing import Tuple, List, Callable, Dict, Set, Iterable
from pysat.formula import CNF
from pysat.solvers import Solver
import time
import itertools
from collections import deque 

from normalisation import r1cs_norm

from utilities import _signal_data_from_cons_list, getvars, count_ints

from r1cs_scripts.circuit_representation import Circuit

from structural_analysis.utilities.connected_preprocessing import connected_preprocessing

from bij_encodings.encoder import Encoder
from bij_encodings.assignment import Assignment
from bij_encodings.reduced_encoding.red_pseudoboolean_encoding import ReducedPseudobooleanEncoder
from bij_encodings.preprocessing.iterated_adj_reclassing import iterated_label_propagation

from comparison_v2.fingerprinting_v2 import back_and_forth_fingerprinting
from comparison_v2.constraint_encoding_v2 import encode_classes_v2

# TODO: tomorrow

def circuit_equivalence(
        in_pair: List[Tuple[str, Circuit]],
        info_preprocessing: Callable[["In_Pair", Assignment], "Signal_Info"] | None = None,
        cons_grouping: Callable[["In_Pair", "Clusters", "Signal_Info", Assignment], "Classes"] | None = None,
        cons_preprocessing: Callable | None = None,
        encoder: Encoder = ReducedPseudobooleanEncoder,
        test_data: Dict[str, any] = {},
        debug: bool = False,
        encoder_kwargs: dict = {}
        ) -> Dict[str, any]:
    
    names = [in_pair[0][0], in_pair[1][0]]

    def _check_early_exit(classes):
        for key in set(classes[names[0]].keys()).union(classes[names[1]].keys()):
            for name, _ in in_pair:
                if key not in classes[name].keys():
                    raise AssertionError(f"EE: Group with fingerprint {key} not in circuit {name}")
            
            if len(classes[names[0]][key]) != len(classes[names[1]][key]):
                raise AssertionError(f"EE: Group with fingerprint {key} has size {len(classes['S1'][key])} in 'S1', and {len(classes['S2'][key])} in 'S2'")

    for key, init in [("result", None), ("timing", {}), ("result_explanation", None), ("formula_size", None), ("group_sizes", {})]:
        test_data[key] = init

    S1 = in_pair[0][1]
    S2 = in_pair[1][1]
    start = time.time()

    S1 = connected_preprocessing(S1)
    S2 = connected_preprocessing(S2)

    in_pair = [(names[0], S1), (names[1], S2)]

    connected_preprocessing_time = time.time()
    last_time = connected_preprocessing_time
    test_data["timing"]["connected_preprocessing"] = connected_preprocessing_time - start

    try: 
        N = S1.nConstraints
        K = S1.nWires

        for lval, rval, val_name,  in [
            (S1.nWires, S2.nWires, "wires"), (S1.nConstraints, S2.nConstraints, "constraints"),(S1.nPubOut, S2.nPubOut, "output constraints"), 
            (S1.nPubIn + S1.nPrvIn, S2.nPubIn + S2.nPrvIn, "input constraints")]:
            if lval != rval: raise AssertionError(f"Different number of {val_name} in circuits: S1 has {lval}, S2 has {rval}")

        assumptions = set([])
        formula = CNF()

        # the norms for each constraint
        normalised_constraints = { name : list(itertools.chain(*map(r1cs_norm, circ.constraints))) for name, circ in in_pair}
        signal_to_normi = {name: _signal_data_from_cons_list(normalised_constraints[name]) for name in names}

        if len(normalised_constraints[names[0]]) != len(normalised_constraints[names[1]]): 
            raise AssertionError(f"EE: Different number of normalised constraints, {names[0]} had {len(normalised_constraints[names[0]])} where {names[1]} had {len(normalised_constraints[names[1]])}")


        fingerprints_to_normi = {name: { 1 : list(range(len(normalised_constraints[name])))} for name in names}

        # signals initially classed on input / output / neither
        fingerprints_to_signals = {name : {0 : [0], 
                                           1 : list(range(1,circ.nPubOut+1)), 
                                           2 : list(range(circ.nPubOut+1, circ.nPubOut + circ.nPrvIn + circ.nPubIn + 1)), 
                                           3 : list(range(circ.nPubOut + circ.nPrvIn + circ.nPubIn + 1, circ.nWires))} 
                                   for name, circ in in_pair}

        # encode initial fingerprints but norms now have signal class in norm
        fingerprints_to_normi, fingerprints_to_signals, _, signal_to_fingerprints = back_and_forth_fingerprinting(
            names, in_pair, normalised_constraints, signal_to_normi, fingerprints_to_normi, fingerprints_to_signals, return_index_to_fingerprint=True
        )

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

        ## TODO: double check early exits

        if len(fingerprints_to_normi[names[0]]) != len(normalised_constraints[names[0]]):

            normi_to_adj_normi = {
                name: [
                        set(filter(lambda x : x != normi, itertools.chain(*map(signal_to_normi[name].__getitem__, getvars(con)))))
                        for normi, con in enumerate(normalised_constraints[name])
                    ]
                    for name in names
            }

            fingerprints_to_normi = iterated_label_propagation(
                names, 
                {name: range(len(normalised_constraints[name])) for name in names}, 
                normi_to_adj_normi, 
                fingerprints_to_normi, 
                input_inverse=True, return_inverse=True
            )

            label_passing_time = time.time()
            test_data["timing"]["label_passing"] = label_passing_time - last_time
            last_time = label_passing_time

            ints = count_ints(map(len, fingerprints_to_normi[names[0]].values()))
            test_data["group_sizes"]["post_label_propagation"] = {
                    "sqr_weight": sum([x[0]**2 * x[1] for x in ints]),
                    "sizes": [x[0] for x in ints],
                    "counts": [x[1] for x in ints]
            }
        
            # repeat previous step (with non-unique classes obviously) -- maybe use pipe?
            fingerprints_to_normi, fingerprints_to_signals, _, signal_to_fingerprints = back_and_forth_fingerprinting(
                names, in_pair, normalised_constraints, signal_to_normi, fingerprints_to_normi, fingerprints_to_signals, initial_mode=False, return_index_to_fingerprint=True
            )

            back_and_forth_fingerprinting_time = time.time()
            test_data["timing"]["back_and_forth_redux"] = back_and_forth_fingerprinting_time - last_time
            last_time = back_and_forth_fingerprinting_time

            ints = count_ints(map(len, fingerprints_to_normi[names[0]].values()))
            test_data["group_sizes"]["post_back_and_forth_redux"] = {
                    "sqr_weight": sum([x[0]**2 * x[1] for x in ints]),
                    "sizes": [x[0] for x in ints],
                    "counts": [x[1] for x in ints]
            }

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

        test_data["result"] = False
        test_data["result_explanation"] = repr(e)
    
    return test_data