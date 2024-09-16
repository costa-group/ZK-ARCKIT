from typing import List, Tuple, Dict
from functools import reduce

from r1cs_scripts.circuit_representation import Circuit
from r1cs_scripts.constraint import Constraint
from structural_analysis.graph_clustering.clustering_from_list import cluster_from_list_old, _signal_data_from_cons_list, cluster_by_ignore

def getvars(con) -> set:
    return set(con.A.keys()).union(con.B.keys()).union(con.C.keys()).difference(set([0]))

class Average():
    "Enum for averages"
    mean = 0
    median = 1
    mode = 2

# class ClusterMethod():
#     "enum for method picking"
#     edge_removal = 0
#     signal_removal = 1
#     old_signal_removal = 2

def twice_average_degree(
        circ: Circuit, 
        avg_type: int = Average.mode, 
        and_up: bool = True, 
        **kwargs) -> List[List[int]]:
    
    signal_to_conis = _signal_data_from_cons_list(circ.constraints)

    degree_to_signal = {}

    for signal, conis in signal_to_conis.items():
        degree_to_signal.setdefault(len(conis), []).append(signal)

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

    # Testing found no significant difference between methods, so simplest method chosen
    return cluster_by_ignore(circ, 0, signalset, **kwargs)

# NOT SURE IF ONLY USING DARKFOREST CIRCUITS IS THE BEST IDEA FOR THIS BUT TESTING SHOWS 0.36 signal ratio

def ratio_of_signals(circ: Circuit, nSignals = None, signal_ratio=0.36, **kwargs) -> List[List[int]]:
    assert 0 < signal_ratio < 1, "Invalid ratio"

    # doable but not recommended just pass nWires
    if nSignals is None:
        signals = set([])

        for con in circ.constraints:
            signals.update(getvars(con))
        
        nSignals = len(signals)

    signal_to_conis = _signal_data_from_cons_list(circ.constraints)

    degree_to_signal = {}

    for signal, conis in signal_to_conis.items():
        degree_to_signal.setdefault(len(conis), []).append(signal)

    signalset = set([])

    for key, val in sorted(degree_to_signal.items(), reverse=True):
        signalset.update(val)
        
        if len(signalset) / nSignals > 0.36:
            break

    coniset = reduce(
        lambda acc, signal : acc.union(signal_to_conis[signal]),
        signalset,
        set([])
    )

    return cluster_by_ignore(circ, 1, coniset, **kwargs)
