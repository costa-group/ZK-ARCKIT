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

class Average():
    "Enum for averages"
    mean = 0
    median = 1
    mode = 2

def twice_average_degree(cons: List[Constraint], avg_type: int = Average.mode, and_up: bool = True) -> List[List[int]]:
    
    degree_to_signal, signal_to_cons = _signal_data_from_cons_list(cons)

    match avg_type:
        case Average.mean:
            avg_num_signals = sum(k * len(val) for k, val in degree_to_signal.items()) // sum(len(val) for val in degree_to_signal.values())
        
        case Average.median:
            total_num = sum(len(val) for val in degree_to_signal.values())
            median = total_num // 2
            count = 0
            for k, val in degree_to_signal.items():
                count += len(val)
                if count > median:
                    avg_num_signals = k
                    break
        
        case Average.mode:
            avg_num_signals = max(degree_to_signal.keys(), key = lambda k : len(degree_to_signal[k]))

        case _:
            raise ValueError("Invalid Avg Type")
    
    to_remove = set([])

    if and_up:

        signalset = reduce(
            lambda acc, degree : acc.union(degree_to_signal[degree]),
            filter(lambda k : k >= 2 * avg_num_signals, degree_to_signal.keys()),
            set([])
        )
    else:

        signalset = degree_to_signal[2 * avg_num_signals]

    coniset = reduce(
        lambda acc, signal : acc.union(signal_to_cons[signal]),
        signalset,
        set([])
    )

    return cluster_from_list(cons, to_ignore=coniset)

# NOT SURE IF ONLY USING DARKFOREST CIRCUITS IS THE BEST IDEA FOR THIS BUT TESTING SHOWS 0.36 signal ratio

def ratio_of_signals(cons: List[Constraint], nSignals = None, signal_ratio=0.36) -> List[List[int]]:
    assert 0 < signal_ratio < 1, "Invalid ratio"

    # doable but not recommended just pass nWires
    if nSignals is None:
        signals = set([])

        for con in cons:
            signals.update(getvars(con))
        
        nSignals = len(signals)

    degree_to_signal, signal_to_cons = _signal_data_from_cons_list(cons)

    signalset = set([])

    for key, val in sorted(degree_to_signal.items(), reverse=True):
        signalset.update(val)
        
        if len(signalset) / nSignals > 0.36:
            break

    coniset = reduce(
        lambda acc, signal : acc.union(signal_to_cons[signal]),
        signalset,
        set([])
    )

    return cluster_from_list(cons, to_ignore=coniset)
