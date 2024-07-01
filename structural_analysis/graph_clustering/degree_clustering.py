from typing import List, Tuple, Dict
from functools import reduce

from r1cs_scripts.constraint import Constraint
from structural_analysis.graph_clustering.clustering_from_list import cluster_from_list

def getvars(con) -> set:
    return set(con.A.keys()).union(con.B.keys()).union(con.C.keys()).difference(set([0]))

def _signal_data_from_cons_list(cons: List[Constraint]):
    signal_to_cons = {}
    signal_to_degree = {}

    for i, con in enumerate(cons):
        for signal in getvars(con):
            signal_to_cons.setdefault(signal, []).append(i)
            signal_to_degree[signal] = signal_to_degree.setdefault(signal, 0) + 1

    degree_to_signal = {}

    for signal, degree in signal_to_degree.items():
        degree_to_signal.setdefault(degree, []).append(signal)

    return degree_to_signal, signal_to_cons


def twice_average_degree(cons: List[Constraint]) -> List[List[int]]:
    
    degree_to_signal, signal_to_cons = _signal_data_from_cons_list(cons)

    mode_num_signals = max(degree_to_signal.keys(), key = lambda k : len(degree_to_signal[k]))

    to_remove = set([])

    signalset = reduce(
        lambda acc, degree : acc.union(degree_to_signal[degree]),
        filter(lambda k : k >= 2 * mode_num_signals, degree_to_signal.keys()),
        set([])
    )

    coniset = reduce(
        lambda acc, signal : acc.union(signal_to_cons[signal]),
        signalset,
        set([])
    )

    return cluster_from_list(cons, to_ignore=coniset)

    
