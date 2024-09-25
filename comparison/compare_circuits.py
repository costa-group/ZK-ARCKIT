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

from comparison.cluster_preprocessing import circuit_clusters

from r1cs_scripts.circuit_representation import Circuit

from structural_analysis.connected_preprocessing import connected_preporcessing

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
        info_preprocessing: Callable[["In_Pair", Assignment], "Signal_Info"] = None,
        cons_clustering: Callable[["In_Pair"], Tuple["Clusters", "Adjacency", "Removed"]] = None,
        cons_grouping: Callable[["In_Pair", "Clusters", "Signal_Info", Assignment], "Classes"] = None,
        cons_preprocessing: Callable = None,
        encoder: Encoder = ReducedPseudobooleanEncoder,
        test_data: Dict[str, any] = {},
        debug: bool = False,
        clustering_kwargs: dict = {},
        encoder_kwargs: dict = {}
        ) -> Tuple[bool, List[Tuple[int, int]]]:
    """
    The manager function for circuit comparison

    Takes as input the input pair of circuits to compare, and a set of functions that will perform each step of the equivalence comparison
    Returns a dictionary in json format that contains the test data, all timings, intermediate class sizes and the result/reason of the comparison
    
    """

    for key, init in [("result", None), ("timing", {}), ("result_explanation", None), ("formula_size", None), ("group_sizes", {})]:
        test_data[key] = init

    S1 = in_pair[0][1]
    S2 = in_pair[1][1]
    start = time.time()

    connected_preporcessing(S1)
    connected_preporcessing(S2)

    connected_preprocessing_time = time.time()
    last_time = connected_preprocessing_time
    test_data["timing"]["connected_preprocessing"] = connected_preprocessing_time - start

    try: 
        N = S1.nConstraints
        K = S1.nWires

        if K != S2.nWires:
            raise AssertionError(f"Different number of wires in circuits: S1 has {S1.nWires}, S2 has {S2.nWires}")

        if N != S2.nConstraints:
            raise AssertionError(f"Different number of constraints in circuits: S1 has {S1.nConstraints}, S2 has {S2.nConstraints}")

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

        clusters = None

        if cons_clustering is not None: 
            
            clusters = circuit_clusters(in_pair, cons_clustering, **clustering_kwargs)
            clustering_time = time.time()

            test_data["timing"]["clustering_time"] = clustering_time - last_time
            last_time = clustering_time

            if debug: print("Finished circuit clustering", end='\r')

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
        for key in set(classes[in_pair[0][0]].keys()).union(classes[in_pair[1][0]].keys()):
            for name, _ in in_pair:
                if key not in classes[name].keys():
                    raise AssertionError(f"EE: Group with fingerprint {key} not in circuit {name}")
            
            if len(classes[in_pair[0][0]][key]) != len(classes[in_pair[1][0]][key]):
                raise AssertionError(f"EE: Group with fingerprint {key} has size {len(classes['S1'][key])} in 'S1', and {len(classes['S2'][key])} in 'S2'")

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

        formula, assumptions, encoded_classes = encoder().encode(
            in_pair, classes, clusters, return_signal_mapping = False, return_constraint_mapping = False, return_encoded_classes = True, debug = debug,
            formula = formula, mapp = mapp, ckmapp = ckmapp, assumptions = assumptions, signal_info = signal_info, 
            **encoder_kwargs
        )

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