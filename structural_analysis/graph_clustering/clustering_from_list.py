
from typing import List, Tuple, Dict, Callable, Set
from functools import reduce
import itertools

from r1cs_scripts.constraint import Constraint
from utilities import _signal_data_from_cons_list

def getvars(con) -> set:
    return set(con.A.keys()).union(con.B.keys()).union(con.C.keys()).difference(set([0]))

class UnionFind():

    def __init__(self):

        self.parent = {}
        self.representatives = set([])
    
    def find(self, i:int) -> int:
        assert i >= 0, "invalid i"
        
        if i not in self.parent.keys(): self.representatives.add(i)

        if self.parent.setdefault(i, -1) < 0:
            return i
        else:
            # path compression optimisation
            self.parent[i] = self.find(self.parent[i])
            return self.parent[i]

    def union(self, *args: int) -> None:

        representatives = sorted(set([self.find(i) for i in args]), key = lambda x: self.parent[x])

        if len(representatives) > 1 and self.parent[representatives[0]] == self.parent[representatives[1]]:
            self.parent[representatives[0]] -= 1

        for repr in representatives[1:]:
            self.representatives.remove(repr)
            self.parent[repr] = representatives[0]
    
    def get_representatives(self) -> Set[int]:
        return self.representatives
    
def cluster_from_list(
        cons: List[Constraint],
        constraints_to_ignore: List[int] = [],
        signals_to_ignore: List[int] = [],
        ignore_func: Callable[[int, Constraint], bool] = None,
        calculate_adjacency: bool = True,
    ) -> List[List[int]]:

    assert len(constraints_to_ignore) > 0  or len(signals_to_ignore) > 0 or ignore_func is not None, "no removal method given"

    if ignore_func is None: 
        # O(N) memory, O(1) time
        ignoring = [ False for _ in range(len(cons)) ]
        for i in constraints_to_ignore: ignoring[i] = True

        keep = lambda coni : not ignoring[coni]
        removed = constraints_to_ignore
    else:
        keep = lambda coni : not ignore_func(cons[coni])
        removed = list(filter(lambda coni : not keep(coni), range(len(cons))))

    clusters = UnionFind()
    for i in range(len(cons)): clusters.find(i)
    
    _, signal_to_coni = _signal_data_from_cons_list(cons)

    for signal in set(signal_to_coni.keys()).difference(signals_to_ignore):
        clusters.union(*filter(keep, signal_to_coni[signal]))

    cluster_lists = {}
    for i in filter(keep, range(len(cons))):
        cluster_lists.setdefault(clusters.find(i), []).append(i)

    ### Adjacency Calculation

    # Modifications to previous mean that some clusters may have direct adjacencies
    # 1 step passthrough 

    adjacency = {}

    if calculate_adjacency:
        removed_adjacencies = {}

        # get coni -> get signals - > get adjacent coni -> get repr -> make unique
        coni_to_adjacent_coni = lambda coni : set(map(
                clusters.find, 
                itertools.chain(*map(
                    lambda sig : signal_to_coni[sig],
                    getvars(cons[coni])
                ))
            ))
            
        for coni in removed: removed_adjacencies[coni] = list(filter(keep, coni_to_adjacent_coni(coni)))

        for key, cluster in cluster_lists.items():
            adjacent_repr = set(itertools.chain(*map(
                coni_to_adjacent_coni,
                cluster
            )))
            
            adjacency[key] = list(itertools.chain(*map(
                lambda coni :  [coni] if keep(coni) else removed_adjacencies[coni],
                adjacent_repr
            )))

    return cluster_lists, adjacency, removed

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