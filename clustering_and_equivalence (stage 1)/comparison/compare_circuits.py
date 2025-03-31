"""
The idea is that we have two circuis S_1, S_2, which are equivalent up to renaming of variables and constant factor
    A proof of equivalence is a bijection mapping the variable names from S_1, to S_2 under the conditions of equivalent constraints
    This bijection will eventually require some SAT solve (most likely) so to reduce the search space we divide the constraints
        into classes based on how many variables there are in the class, whether it does/does not have a constant/quadratic term
        then whether the normalisation sets are the same -- problems with this up to norm..?
            -- maybe will need more work here
        then finally we build the SAT logic that will return the bijection
"""
from typing import Tuple, List, Callable, Dict, Set, Iterable
from pysat.formula import CNF
from pysat.solvers import Solver
import time

from r1cs_scripts.circuit_representation import Circuit

from structural_analysis.utilities.connected_preprocessing import connected_preprocessing

from bij_encodings.encoder import Encoder
from bij_encodings.assignment import Assignment
from bij_encodings.reduced_encoding.red_pseudoboolean_encoding import ReducedPseudobooleanEncoder

from utilities import getvars

def count_ints(lints : Iterable[int]) -> Dict[int, int]:
    res = {}
    for i in lints:
        res[i] = res.setdefault(i, 0) + 1
    return sorted(res.items())

# Typing throwing warnings for unknown classes, I think this is easier for a human to read though
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
    """
    The manager function for circuit comparison

    Takes as input the input pair of circuits to compare, and a set of functions that will perform each step of the equivalence comparison
    Returns a dictionary in json format that contains the test data, all timings, intermediate class sizes and the result/reason of the comparison
    
    Parameters
    ----------
        in_pair: List[Tuple[str, Circuit]]
            name / circuit tuples for the input circuits.
        info_preprocessing: In_Pair, Assignment -> Signal_Info | None
            A preprocessing step to generate some signal pair information. If None this step is skipped.
        cons_grouping: "In_Pair", "Clusters", "Signal_Info", Assignment -> "Classes" | None
            The method to determine the initial constraint equivalence classes. If None this a single equivalence class is created.
        cons_preprocessing: Callable | None
            A method to improve the constraint equivalence classes. If this is None then this step is skipped.
        enoder: Encoder
            The specific encoder to turn the constraint classes and signal_info into a pysat.CNF formula.
        test_data: Dict[str, any]
            The test data dictionary passed to the function to add its data to.
        debug: Bool
            Flag that determines if progress updates are printed to terminal
        encoder_kwargs: Dict
            kwargs passed to the encoder
    
    Returns
    ----------
    Dict[str, any]
        The data of the test. Includes the results and timing data.
    """

    def _check_early_exit(classes):
        for key in set(classes[in_pair[0][0]].keys()).union(classes[in_pair[1][0]].keys()):
            for name, _ in in_pair:
                if key not in classes[name].keys():
                    raise AssertionError(f"EE: Group with fingerprint {key} not in circuit {name}")
            
            if len(classes[in_pair[0][0]][key]) != len(classes[in_pair[1][0]][key]):
                raise AssertionError(f"EE: Group with fingerprint {key} has size {len(classes['S1'][key])} in 'S1', and {len(classes['S2'][key])} in 'S2'")

    for key, init in [("result", None), ("timing", {}), ("result_explanation", None), ("formula_size", None), ("group_sizes", {})]:
        test_data[key] = init

    S1 = in_pair[0][1]
    S2 = in_pair[1][1]
    start = time.time()

    S1 = connected_preprocessing(S1)
    S2 = connected_preprocessing(S2)

    in_pair = [(in_pair[0][0], S1), (in_pair[1][0], S2)]

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

        mapp = Assignment()
        assumptions = set([])
        formula = CNF()
        ckmapp = Assignment(assignees=3, link = mapp)

        signal_info = None

        if info_preprocessing is not None: 
            signal_info = info_preprocessing(in_pair, mapp)
            info_preprocessing_time = time.time()

            test_data["timing"]["info_preprocessing_time"] = info_preprocessing_time - last_time
            last_time = info_preprocessing_time
      
            if debug: print("Finished info preprocessing", end='\r')
        
        clusters = None # deprecated TODO -- clean up
        classes = {name: {"1": circ.constraints} for name, circ in in_pair}

        if cons_grouping is not None: 
            classes = cons_grouping(in_pair, clusters, signal_info, mapp)
            grouping_time = time.time()

            test_data["timing"]["grouping_time"] = grouping_time - last_time
            last_time = grouping_time

            ints = count_ints(map(len, classes["S1"].values()))
            test_data["group_sizes"]["initial_sizes"] = {
                "sqr_weight": sum([x[0]**2 * x[1] for x in ints]),
                "sizes": [x[0] for x in ints],
                "counts": [x[1] for x in ints]
            }
            if debug: print("Finished building classes  ", end='\r')

        # classes early exit
        _check_early_exit(classes)

        if cons_preprocessing is not None: 
            classes, signal_info = cons_preprocessing(
                in_pair, classes, clusters, mapp, 
                ckmapp, assumptions, formula, signal_info,
                debug = debug
            )

            cons_preprocessing_time = time.time()
            test_data["timing"]["cons_preprocessing_time"] = cons_preprocessing_time - last_time
            last_time = cons_preprocessing_time

            ints = count_ints(map(len, classes["S1"].values()))

            test_data["group_sizes"]["post_processing"] = {
                "sqr_weight": sum([x[0]**2 * x[1] for x in ints]),
                "sizes": [x[0] for x in ints],
                "counts": [x[1] for x in ints]
            }

            if debug: print("Finished preprocessing constraint classes", end='\r')

        # TODO: early exit here too.
        _check_early_exit(classes)

        formula, assumptions, encoded_classes = encoder().encode(
            in_pair, classes, clusters, return_signal_mapping = False, return_constraint_mapping = False, return_encoded_classes = True, debug = debug,
            formula = formula, mapp = mapp, ckmapp = ckmapp, assumptions = assumptions, signal_info = signal_info, 
            **encoder_kwargs
        )

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

        test_data["formula_size"] = len(formula.clauses)    

        test_data["group_sizes"]["encoded_classes"] = {
                "sqr_weight": sum([x[0]**2 * x[1] for x in encoded_classes]),
                "sizes": [x[0] for x in encoded_classes],
                "counts": [x[1] for x in encoded_classes]
            }

        if debug: print("Finished encoding                                     ", end='\r')

    except AssertionError as e:

        test_data["result"] = False
        test_data["result_explanation"] = repr(e)
    
    return test_data