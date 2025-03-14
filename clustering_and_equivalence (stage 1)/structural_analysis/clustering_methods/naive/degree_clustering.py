from typing import List, Tuple, Dict
from functools import reduce

from r1cs_scripts.circuit_representation import Circuit
from r1cs_scripts.constraint import Constraint
from structural_analysis.clustering_methods.naive.clustering_from_list import _signal_data_from_cons_list, cluster_by_ignore, getvars

class Average():
    "Enum for averages"
    mean = 0
    median = 1
    mode = 2

def twice_average_degree(
        circ: Circuit, 
        avg_type: int = Average.mode, 
        and_up: bool = True,
        **kwargs) -> List[List[int]]:
    """
    Clustering Method

    Clusters constraint in a circuit by the connected components achieved by ignoring all signals that have degree at least
    twice as large as the average

    Parameters
    ----------
        circ: Circuit
            The input circuit to cluster
        avg_type: Average
            Enumerator for which average method. 0 for Mean, 1 for Median, 2 for Mode
        and_up: Bool
            Boolean flag that determines at least twice as large / exactly twice as large. Default is True
        kwargs:
            Passed to `cluster_by_ignore`
    
    Returns
    ---------
    (clusters, adjacency, removed)
        cluster: Dict[int, List[int]]
            Partition of the input graph given by connected components. Clusters are indexed by an arbitrary element of the cluster. 
            Dictionary used to later be able to remove and reindex elements without remapping indices.

        adjacency: Dict[int, List[int]]
            Maps cluster index to adjacent cluster indices. Empty if calculate_adjacency is False

        removed: List[int]
            List of removed constraints. In this case always empty.
    """
    
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

def ratio_of_signals(circ: Circuit, signal_ratio=0.36, **kwargs) -> List[List[int]]:
    """
        Clustering Method

    Clusters constraint in a circuit by the connected components achieved by ignoring signals ordered from highest to lowest degree
    such that the signal set is signal_ratio of all signals.

    Parameters
    ----------
        circ: Circuit
            The input circuit to cluster
        signal_ratio: float
            0 < signal_ratio < 1. Determines at what signal ratio to stop.
        kwargs:
            Passed to `cluster_by_ignore`
    
    Returns
    ---------
    (clusters, adjacency, removed)
        cluster: Dict[int, List[int]]
            Partition of the input graph given by connected components. Clusters are indexed by an arbitrary element of the cluster. 
            Dictionary used to later be able to remove and reindex elements without remapping indices.

        adjacency: Dict[int, List[int]]
            Maps cluster index to adjacent cluster indices. Empty if calculate_adjacency is False

        removed: List[int]
            List of removed constraints. In this case always empty.
    """
    assert 0 < signal_ratio < 1, "Invalid ratio"

    signal_to_conis = _signal_data_from_cons_list(circ.constraints)

    degree_to_signal = {}

    for signal, conis in signal_to_conis.items():
        degree_to_signal.setdefault(len(conis), []).append(signal)

    signalset = set([])

    for key, val in sorted(degree_to_signal.items(), reverse=True):
        signalset.update(val)
        
        if len(signalset) / circ.nWires > signal_ratio:
            break

    coniset = reduce(
        lambda acc, signal : acc.union(signal_to_conis[signal]),
        signalset,
        set([])
    )

    return cluster_by_ignore(circ, 1, coniset, **kwargs)
