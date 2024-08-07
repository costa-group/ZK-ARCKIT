
from typing import List, Tuple, Dict, Callable, Set
from functools import reduce

from r1cs_scripts.constraint import Constraint


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

def cluster_from_list(cons: List[Constraint], 
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