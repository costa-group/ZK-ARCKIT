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
import json

from comparison.cluster_preprocessing import circuit_clusters

from r1cs_scripts.circuit_representation import Circuit

from bij_encodings.encoder import Encoder
from bij_encodings.assignment import Assignment
from bij_encodings.reduced_encoding.red_pseudoboolean_encoding import ReducedPseudobooleanEncoder

def count_ints(lints : Iterable[int]) -> Dict[int, int]:
    res = {}
    for i in lints:
        res[i] = res.setdefault(i, 0) + 1
    return sorted(res.items())

# Typing throwing warnings for unknown classes, I think this is easier for a human to read though
def circuit_equivalence(
        S1: Circuit, 
        S2: Circuit,
        info_preprocessing: Callable[["In_pair", Assignment], "Signal_Info"] = None,
        cons_clustering: Callable = None,
        cons_grouping: Callable[["In_pair", "Clusters", "Signal_Info", Assignment], "Groups"] = None,
        cons_preprocessing: Callable = None,
        encoder: Encoder = ReducedPseudobooleanEncoder,
        debug: bool = False,
        **encoder_kwargs
        ) -> Tuple[bool, List[Tuple[int, int]]]:
    """
    Currently assumes A*B + C = 0, where each A, B, C are equivalent up to renaming/factor
    """

    test_data = {
        "result": None
    }

    start = time.time()

    try: 
        N = S1.nConstraints
        K = S1.nWires

        if K != S2.nWires:
            raise AssertionError("Different number of wires in circuits")

        if N != S2.nConstraints:
            raise AssertionError("Different number of constraints in circuits")
        
        in_pair = [('S1', S1), ('S2', S2)]

        mapp = Assignment()
        assumptions = set([])
        formula = CNF()
        ckmapp = Assignment(assignees=3, link = mapp)

        signal_info = None

        if info_preprocessing is not None: signal_info = info_preprocessing(in_pair, mapp)
        info_preprocessing_time = time.time()

        clusters = None

        if cons_clustering is not None: clusters = circuit_clusters(in_pair, cons_clustering, calculate_adjacency = True)
        clustering_time = time.time()

        groups = {name: {"1": circ.constraints} for name, circ in in_pair}

        if cons_grouping is not None: groups = cons_grouping(in_pair, clusters, signal_info, mapp)
        grouping_time = time.time()

        # groups early exit
        for key in set(groups["S1"].keys()).union(groups["S2"].keys()):
            for name, _ in in_pair:
                if key not in groups[name].keys():
                    raise AssertionError(f"Group with fingerprint {key} not in circuit {name}")
            
            if len(groups["S1"][key]) != len(groups["S2"][key]):
                raise AssertionError(f"Group with fingerorint {key} has size {len(groups['S1'][key])} in 'S1', and {len(groups['S2'][key])} in 'S2'")

        if cons_preprocessing is not None: 
            groups, signal_info = cons_preprocessing(
                in_pair, groups, clusters, mapp, 
                ckmapp, assumptions, formula, signal_info
            )
        cons_preprocessing_time = time.time()

        formula, assumptions = encoder().encode(
            in_pair, groups, clusters, return_signal_mapping = False, return_constraint_mapping = False, debug = debug,
            formula = formula, mapp = mapp, ckmapp = ckmapp, assumptions = assumptions, signal_info = signal_info, 
            **encoder_kwargs
        )

        solver = Solver(name='cadical195', bootstrap_with=formula)
        encoding_time = time.time()

        result = solver.solve(assumptions)
        solving_time = time.time()

        test_data["result"] = result

        if result:
            test_data["result_explanation"] = ""
        else:
            test_data["result_explanation"] = "Unsatisfiable"
        
        test_data["timing"] = {}
        for time_title, time_bool, later_time, earlier_time in zip(
            ["info_preprocessing_time", "clustering_time", "grouping_time", "cons_preprocessing_time", "encoding_time", "solving_time"], 
            [info_preprocessing, cons_clustering, cons_grouping, cons_preprocessing, True, True],
            [info_preprocessing_time, clustering_time, grouping_time, cons_preprocessing_time, encoding_time, solving_time], 
            [start, info_preprocessing_time, clustering_time, grouping_time, cons_preprocessing_time, encoding_time]
        ):
            if time_bool is not None:
                test_data["timing"][time_title] = later_time - earlier_time

    except AssertionError as e:

        test_data["result"] = result
        test_data["result_explanation"] = e
    
    return test_data