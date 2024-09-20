
from typing import List, Tuple, Dict, Callable, Set, Iterable
from functools import reduce
import itertools
import tracemalloc

from r1cs_scripts.circuit_representation import Circuit
from r1cs_scripts.constraint import Constraint
from utilities import _signal_data_from_cons_list, getvars, UnionFind

def cluster(
    complete_subraphs: Iterable[List[int]],
    vertices: Iterable[int] = None,
    ) -> UnionFind:
    """
    The complete_subraphs provide every complete subgraph in the graph on the vertices, note this improves the traditional unionfind clustering
    by reducing the number of union operations from |E| to the number of complete subgraphs.

    Assumes every k_n in complete_subgraphs is a subset of vertices.
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
    ) -> Tuple[List[List[int]], List[List[int]], List[int]]:

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

    # TODO: this version seems correct but seems to cause errors in the it_adj_recl done in the clustering stage. dunno why.

    keep_func = lambda coni : not ignore_func(coni)

    vertices = list(filter(keep_func, range(circ.nConstraints)))
    adjacency = {}
    removed = list(filter(ignore_func, range(circ.nConstraints)))

    sig_vertices = range(circ.nWires)
    sig_complete_subgraphs = [getvars(circ.constraints[coni]) for coni in vertices]

    sig_clusters = cluster(sig_vertices, sig_complete_subgraphs)
    
    cluster_lists = {} 
    for coni in vertices: cluster_lists.setdefault(sig_clusters.find(next(iter(getvars(circ.constraints[coni])))), []).append(coni)

    if calculate_adjacency:

            # TODO: retest with power plugged in and later? -- seems same as old (but cleaner so valuable)

        unclustered_sig = cluster(sig_vertices, [map(sig_clusters.find, getvars(circ.constraints[coni])) for coni in removed])
        unclustered_sig_lists = {}
        for repr in cluster_lists.keys():
            unclustered_sig_lists.setdefault(unclustered_sig.find(repr), []).append(repr)

        for complete_subgraph in unclustered_sig_lists.values():
            for repr in complete_subgraph:
                adjacency.setdefault(repr, []).extend(filter(lambda orepr : orepr != repr, complete_subgraph))
        
        for repr, adj in adjacency.items():
            # remove duplicates
            adjacency[repr] = set(adj)

    # cons = circ.constraints
    # signal_to_coni = _signal_data_from_cons_list(cons)

    # keep_func = lambda coni : not ignore_func(coni)

    # vertices = list(filter(keep_func, range(len(cons))))
    # complete_subgraphs = {sig: filter(keep_func, k_n) for sig, k_n in signal_to_coni.items()}

    # clusters = cluster(vertices, complete_subgraphs.values())
    # adjacency = {}
    # removed = list(filter(ignore_func, range(len(cons))))

    # if calculate_adjacency:
    #     # cluster_adjacency only possible over ignored constraints

    #     # get clusters of removed -- these provide adjacencies 
    #     removed_complete_subgraphs = map(lambda k_n : filter(ignore_func, k_n), signal_to_coni.values())
    #     removed_clusters = cluster(removed, removed_complete_subgraphs, return_lists=True)

    #     # each cluster of removed is an provides adjacencies of prev
    #     # repr -> removed coni -> signals -> kept complete_subgraphs -> remove duplicates
    #     cluster_to_complete_subgraph = lambda repr: set(itertools.chain(
    #         *map(
    #             complete_subgraphs.__getitem__,
    #             itertools.chain(*map(
    #                 getvars,
    #                 map(cons.__getitem__, removed_clusters[repr])
    #             ))
    #         )
    #     ))

    #     for repr in removed_clusters.keys():
    #         complete_subgraph = cluster_to_complete_subgraph(repr)

    #         for coni in complete_subgraph:
    #             adjacency.setdefault(coni, []).extend(filter(lambda oconi: oconi != coni, complete_subgraph))
        
    #     for coni, adj in adjacency.items():
    #         # remove duplicates
    #         adjacency[coni] = set(adj)
    
    # cluster_lists = {}
    # for coni in vertices: cluster_lists.setdefault(clusters.find(coni), []).append(coni)

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
        Manager for the various methods to ignore values
        TODO: maybe just get rid of this alltogether and have each clustering call a specific case
    """

    match ignore_method:

        case IgnoreMethod.ignore_signal_from_list: return cluster_by_ignoring_signals(circ, ignore_tool, calculate_adjacency)
        case IgnoreMethod.ignore_constraint_from_list:
            to_ignore = [False for _ in circ.constraints]
            for coni in ignore_tool: to_ignore[coni] == True
            return cluster_by_ignoring_constraints(circ, to_ignore.__getitem__, calculate_adjacency)
        case IgnoreMethod.ignore_constraint_from_function: 
            return cluster_by_ignoring_constraints(circ, lambda coni: ignore_tool(circ.constraints[coni]), calculate_adjacency)
        case _: raise AssertionError(f"invalid ignore method: {ignore_method}")

def cluster_from_list_old(circ: Circuit, 
                      to_ignore: List[int] = None, 
                      ignore_func: Callable[[Constraint], bool] = None,
                      calculate_adjacency: bool = True) -> List[List[int]]:

    assert to_ignore is not None or ignore_func is not None, "no removal method given"
    use_function = ignore_func is not None

    # TODO: calculate adjacency information

    cons = circ.constraints
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