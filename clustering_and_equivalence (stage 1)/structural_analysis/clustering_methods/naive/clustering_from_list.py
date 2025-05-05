
from typing import List, Tuple, Dict, Callable, Set, Iterable
from functools import reduce
import itertools
import tracemalloc

from r1cs_scripts.circuit_representation import Circuit
from r1cs_scripts.constraint import Constraint
from utilities.utilities import _signal_data_from_cons_list, getvars, UnionFind

def cluster(
    complete_subraphs: Iterable[List[int]],
    vertices: Iterable[int] | None = None
    ) -> UnionFind | Dict[int, List[int]]:
    """
    Given a set of complete subgraphs returns the connected components of a graph

    The complete_subraphs provide every complete subgraph in the graph on the vertices, note this improves the traditional unionfind 
    clustering by reducing the number of union operations from |E| to the number of complete subgraphs. Assumes every k_n in 
    complete_subgraphs is a subset of vertices.
    
    Parameters
    ----------
        complete_subgraphs : Iterable[List[int]]
            An iterator for the the maximal complete subgraphs in a graph G. 
        vertices: Iterable[int] | None
            A list of the vertices that are to be clustered. If None the UnionFind object is returned instead
    
    Returns
    ----------
    UnionFind | Dict[int, List[int]]
        Returns either the a dictionary of clusters indexed by an arbitrary element in the cluster or the UnionFind object of the clusters
    """
    clusters = UnionFind()

    for k_n in complete_subraphs: clusters.union(*k_n)

    # TODO: maybe try to do this again, but without looping over everything? -- will cause problems at larger circuit sizes
    if vertices is None: return clusters
    else:
        cluster_lists = {}
        for v in vertices: cluster_lists.setdefault(clusters.find(v), []).append(v)
        return cluster_lists

def cluster_by_ignoring_signals(
        circ: Circuit,
        signals_to_ignore: List[int],
        calculate_adjacency: bool
    ) -> Tuple[Dict[int, List[int]], Dict[int, List[int]], List[int]]:
    """
    Subordinate function to :func:`cluster_by_ignore`. 
    
    Clusters the connected components of the shared signal graph ignoring the given list of signals

    Parameters
    ----------
        circ: Circuit
            The input circuit to be clustered
        signals_to_ignore: List[int]
            The list of signals to ignore
        calculate_adjacency: bool
            A flag for whether the program should calculate an adjacency dictionary otherwise the adjacency dictionary is empty
    
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

    cons = circ.constraints
    ignore_signal_list = [False for _ in range(circ.nWires)]
    for sig in signals_to_ignore: ignore_signal_list[sig] = True

    signal_to_coni = _signal_data_from_cons_list(cons)

    complete_subgraphs = map(signal_to_coni.__getitem__, set(signal_to_coni.keys()).difference(signals_to_ignore))

    clusters = cluster(complete_subgraphs)
    adjacency = {}

    cluster_lists = {}
    for coni in range(len(cons)): cluster_lists.setdefault(clusters.find(coni), []).append(coni)

    if calculate_adjacency:
        # only possible adjacencies are via removed signals -- seems like the adjacency calc is too memory intensive
        #   specifically the adjacency matrix tends to be near n^2 i.e. the clusters are completely connected

        # 476 -> 3929 (in 2 steps?) then starts memory swapping so it gets killed. (million) -- is the below one wrong? how is it more?
        
        # for sig in signals_to_ignore:
        #     complete_subgraph = set(map(clusters.find, signal_to_coni[sig]))
        #     for coni in complete_subgraph:
        #         adjacency.setdefault(coni, set([])).update(filter(lambda oconi : oconi != coni, complete_subgraph))

        # this ver goes 376 -> 3384 (million) on O1, but the O2 test_ecdsa_verify still goes to memory swaps.
        coni_to_adjacent_coni = lambda coni : set(map(
                clusters.find, 
                itertools.chain(*map(
                    signal_to_coni.__getitem__,
                    filter(ignore_signal_list.__getitem__,
                    getvars(cons[coni]))
                ))
            ))

        for key, value in cluster_lists.items():
            
            adjacency[key] = list(filter(lambda repr : repr != key, set(itertools.chain(*map(
                coni_to_adjacent_coni,
                value
            )))))

    return cluster_lists, adjacency, []

def cluster_by_ignoring_constraints(
        circ: Circuit,
        ignore_func: Callable[[int], bool],
        calculate_adjacency: bool
    ) -> Tuple[List[List[int]], List[List[int]], List[int]]:
    """
    Subordinate function to :func:`cluster_by_ignore`. 
    
    Clusters the connected components of the shared signal graph ignoring the given list of constraints

    Parameters
    ----------
        circ: Circuit
            The input circuit to be clustered
        signals_to_ignore: List[int]
            The list of signals to ignore
        calculate_adjacency: bool
            A flag for whether the program should calculate an adjacency dictionary otherwise the adjacency dictionary is empty
    
    Returns
    ---------
    (clusters, adjacency, removed)
        cluster: Dict[int, List[int]]
            Partition of the input graph given by connected components. Clusters are indexed by an arbitrary element of the cluster. 
            Dictionary used to later be able to remove and reindex elements without remapping indices.

        adjacency: Dict[int, List[int]]
            Maps cluster index to adjacent cluster indices. Empty if calculate_adjacency is False

        removed: List[int]
            List of removed constraints. Always equivalent to ignore_func
    """

    # also causes problems with the ignoring signals where it seems to use more memory, and I don't know why

    adjacency = {}
    vertices, removed = [], []
    for i in range(circ.nConstraints): (removed if ignore_func(i) else vertices).append(i)

    sig_clusters = cluster(map(lambda coni : getvars(circ.constraints[coni]), vertices))
    
    cluster_lists = {} 
    for coni in vertices: 
        cluster_lists.setdefault(sig_clusters.find(next(iter(getvars(circ.constraints[coni])))), []).append(coni)

    if calculate_adjacency:

        # want repr -> adjacent repr

        # unclustered_sig uses removed constraints to build unionfind
        #   by using original sig values we keep adjacencies, where the only connectives are the internal removed

        unclustered_sig = cluster(map(lambda coni : getvars(circ.constraints[coni]), removed))

        sig_clusters_list = {}
        unclustered_sig_lists = {}

        for sig in sig_clusters.parent.keys():
            sig_clusters_list.setdefault(sig_clusters.find(sig), []).append(sig)
            unclustered_sig_lists.setdefault(unclustered_sig.find(sig), []).append(sig_clusters.find(sig))

        # every value is in repr -> has unclustered_sig repr -> get elements of unclustered_sig repr

        for repr, values in sig_clusters_list.items():
            adjacency[repr] = set(filter(lambda orepr: orepr != repr, 
                itertools.chain(
                *map(
                    lambda sig : unclustered_sig_lists[unclustered_sig.find(sig)],
                    values
                ))
            ))

    return cluster_lists, adjacency, removed

class IgnoreMethod():
    "enum for method picking"
    ignore_signal_from_list = 0
    ignore_constraint_from_list = 1
    ignore_constraint_from_function = 2

def cluster_by_ignore(
        circ: Circuit,
        ignore_method: IgnoreMethod,
        ignore_tool: List[int] | Callable[[Constraint], bool],
        calculate_adjacency: bool = True
    ) -> List[List[int]]:
    """
    Subordinate function to :func:`cluster_by_ignore`. 
    
    Clusters the connected components of the shared signal graph ignoring the given list of constraints

    Parameters
    ----------
        circ: Circuit
            The input circuit to be clustered
        ignore_method: IgnoreMethod
            Choice of subordinate function via enumerator
        ignore_tool: List[int] | Constraint -> Bool
            The method of ignoring indices. Either a list of the indices to ignore or a filtering functions (constraint only)
        calculate_adjacency: bool
            A flag for whether the program should calculate an adjacency dictionary otherwise the adjacency dictionary is empty
    
    Returns
    ---------
    (clusters, adjacency, removed)
        cluster: Dict[int, List[int]]
            Partition of the input graph given by connected components. Clusters are indexed by an arbitrary element of the cluster. 
            Dictionary used to later be able to remove and reindex elements without remapping indices.

        adjacency: Dict[int, List[int]]
            Maps cluster index to adjacent cluster indices. Empty if calculate_adjacency is False

        removed: List[int]
            List of removed constraints.
    """

    match ignore_method:

        case IgnoreMethod.ignore_signal_from_list: return cluster_by_ignoring_signals(circ, ignore_tool, calculate_adjacency)
        case IgnoreMethod.ignore_constraint_from_list:
            to_ignore = [False for _ in circ.constraints]
            for coni in ignore_tool: to_ignore[coni] = True
            return cluster_by_ignoring_constraints(circ, to_ignore.__getitem__, calculate_adjacency)
        case IgnoreMethod.ignore_constraint_from_function: 
            return cluster_by_ignoring_constraints(circ, lambda coni: ignore_tool(circ.constraints[coni]), calculate_adjacency)
        case _: raise AssertionError(f"invalid ignore method: {ignore_method}")