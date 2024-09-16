
from typing import List, Tuple, Dict, Callable, Set, Iterable
from functools import reduce
import itertools

from r1cs_scripts.constraint import Constraint
from utilities import _signal_data_from_cons_list, getvars, UnionFind

def cluster(
    vertices: Iterable[int],
    complete_subraphs: Iterable[List[int]],
    return_lists: bool = False
    ) -> UnionFind:
    """
    The complete_subraphs provide every complete subgraph in the graph on the vertices, note this improves the traditional unionfind clustering
    by reducing the number of union operations from |E| to the number of complete subgraphs.

    Assumes every k_n in complete_subgraphs is a subset of vertices.
    """
    clusters = UnionFind()

    for k_n in complete_subraphs: clusters.union(*k_n)

    if not return_lists: return clusters
    else:
        cluster_lists = {}
        for v in vertices: cluster_lists.setdefault(clusters.find(v), []).append(v)
        return cluster_lists

def cluster_by_ignoring_signals(
        cons: List[Constraint],
        signals_to_ignore: List[int],
        calculate_adjacency: bool
    ) -> Tuple[List[List[int]], List[List[int]], List[int]]:

    signal_to_coni = _signal_data_from_cons_list(cons)

    vertices = range(len(cons))
    complete_subgraphs = [signal_to_coni[sig] for sig in set(signal_to_coni.keys()).difference(signals_to_ignore)]

    clusters = cluster(vertices, complete_subgraphs)
    adjacency = {}

    if calculate_adjacency:
        # only possible adjacencies are via removed signals
        
        for sig in signals_to_ignore:
            complete_subgraph = set(map(clusters.find, signal_to_coni[sig]))
            for coni in complete_subgraph:
                adjacency.setdefault(coni, []).extend(filter(lambda oconi : oconi != coni, complete_subgraph))
        
        for coni, adj in adjacency.items():
            # remove duplicates
            adjacency[coni] = set(adj)

    cluster_lists = {}
    for coni in vertices: cluster_lists.setdefault(clusters.find(coni), []).append(coni)

    return cluster_lists, adjacency, []

def cluster_by_ignoring_constraints(
        cons: List[Constraint],
        ignore_func: Callable[[int], bool],
        calculate_adjacency: bool
    ) -> Tuple[List[List[int]], List[List[int]], List[int]]:

    signal_to_coni = _signal_data_from_cons_list(cons)

    keep_func = lambda coni : not ignore_func(coni)

    vertices = list(filter(keep_func, range(len(cons))))
    complete_subgraphs = {sig: filter(keep_func, k_n) for sig, k_n in signal_to_coni.items()}

    clusters = cluster(vertices, complete_subgraphs.values())
    adjacency = {}
    removed = list(filter(ignore_func, range(len(cons))))

    if calculate_adjacency:
        # cluster_adjacency only possible over ignored constraints

        # get clusters of removed -- these provide adjacencies 
        removed_complete_subgraphs = map(lambda k_n : filter(ignore_func, k_n), signal_to_coni.values())
        removed_clusters = cluster(removed, removed_complete_subgraphs, return_lists=True)

        # each cluster of removed is an provides adjacencies of prev
        # repr -> removed coni -> signals -> kept complete_subgraphs -> remove duplicates
        cluster_to_complete_subgraph = lambda repr: set(itertools.chain(
            *map(
                complete_subgraphs.__getitem__,
                itertools.chain(*map(
                    getvars,
                    map(cons.__getitem__, removed_clusters[repr])
                ))
            )
        ))

        for repr in removed_clusters.keys():
            complete_subgraph = cluster_to_complete_subgraph(repr)

            for coni in complete_subgraph:
                adjacency.setdefault(coni, []).extend(filter(lambda oconi: oconi != coni, complete_subgraph))
        
        for coni, adj in adjacency.items():
            # remove duplicates
            adjacency[coni] = set(adj)
    
    cluster_lists = {}
    for coni in vertices: cluster_lists.setdefault(clusters.find(coni), []).append(coni)

    return cluster_lists, adjacency, removed

class IgnoreMethod():
    "enum for method picking"
    ignore_signal_from_list = 0
    ignore_constraint_from_list = 1
    ignore_constraint_from_function = 2

def cluster_by_ignore(
        cons: List[Constraint],
        ignore_method: IgnoreMethod,
        ignore_tool: List[int] | Callable[[Constraint], bool],
        calculate_adjacency: bool = True
    ) -> List[List[int]]:
    """
        Manager for the various methods to ignore values
        TODO: maybe just get rid of this alltogether and have each clustering call a specific case
    """

    match ignore_method:

        case IgnoreMethod.ignore_signal_from_list: return cluster_by_ignoring_signals(cons, ignore_tool, calculate_adjacency)
        case IgnoreMethod.ignore_constraint_from_list:
            to_ignore = [False for _ in cons]
            for coni in ignore_tool: to_ignore[coni] == True
            return cluster_by_ignoring_constraints(cons, to_ignore.__getitem__, calculate_adjacency)
        case IgnoreMethod.ignore_constraint_from_function: 
            return cluster_by_ignoring_constraints(cons, lambda coni: ignore_tool(cons[coni]), calculate_adjacency)
        case _: raise AssertionError(f"invalid ignore method: {ignore_method}")

def cluster_from_list_old(cons: List[Constraint], 
                      to_ignore: List[int] = None, 
                      ignore_func: Callable[[Constraint], bool] = None,
                      calculate_adjacency: bool = True) -> List[List[int]]:

    assert to_ignore is not None or ignore_func is not None, "no removal method given"
    use_function = ignore_func is not None

    # TODO: calculate adjacency information

    next = 0
    signal_to_cluster = {}
    clusters = UnionFind()

    if use_function: removed_clusters = []
    if not use_function: removed_clusters = to_ignore

    for i, con in enumerate(cons):

        if (use_function and ignore_func(con)) or (not use_function and i in to_ignore):
            if use_function: removed_clusters.append(i)
            continue

        member_of_clusters = set([])

        for signal in getvars(con):
            if signal_to_cluster.setdefault(signal, None) is not None:
                member_of_clusters.add( clusters.find(signal_to_cluster[signal]) )

        
        if len(member_of_clusters) > 0:
            clusters.union(i, *member_of_clusters)
        
        cluster = clusters.find(i)

        for signal in getvars(con):
            signal_to_cluster[signal] = cluster

    # change to lists
    cluster_lists = {}

    for i in clusters.parent.keys():
        cluster_lists.setdefault(clusters.find(i), []).append(i)

    ## Calculating Adjacency Information

    # For a given constraint
        # each signal either does/doesn't have an associated cluster.
        # for signals that don't have an associated cluster -- add the set of all signals (for current constraint) to that set.
        # For a constraint with no unknown signals it provides a direct adjacency
        # After all signals the signals with sets provide cliques connected through it.

    adjacency_information = {}
    unclustered_signals = {}

    # TODO: doesn't seem super efficient...
    if calculate_adjacency:
        for coni in removed_clusters:
            seen_clusters = set([])
            seen_unclustered_signals = []

            for signal in getvars(cons[coni]):
                if signal_to_cluster.setdefault(signal, None) is not None:
                    seen_clusters.add(clusters.find(signal_to_cluster[signal]))
                else:
                    seen_unclustered_signals.append(signal)
            
            for signal in seen_unclustered_signals:
                unclustered_signals.setdefault(signal, set([])).update(seen_clusters)
            
            if seen_unclustered_signals == []:
                for cluster in seen_clusters:
                    adjacency_information.setdefault(cluster, set([])).update(seen_clusters.difference([cluster]))

        for signal in unclustered_signals.keys():
            for cluster in unclustered_signals[signal]:
                adjacency_information.setdefault(cluster, set([])).update(unclustered_signals[signal].difference([cluster]))

    return cluster_lists, adjacency_information, removed_clusters