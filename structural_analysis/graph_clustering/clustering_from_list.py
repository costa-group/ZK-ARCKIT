
from typing import List, Tuple, Dict, Callable
from functools import reduce

from r1cs_scripts.constraint import Constraint


def getvars(con) -> set:
    return set(con.A.keys()).union(con.B.keys()).union(con.C.keys()).difference(set([0]))

class UnionFind():

    def __init__(self):

        self.parent = {}
    
    def find(self, i:int) -> int:
        assert i >= 0, "invalid i"
        
        if self.parent.setdefault(i, -1) < 0:
            return i
        else:
            # path compression optimisation
            self.parent[i] = self.find(self.parent[i])
            return self.parent[i]

    def union(self, *args: int) -> None:

        # if a set representative is itself, then
        parents = sorted([self.find(i) for i in args], key = lambda x: self.parent[x])

        if len(parents) > 1 and self.parent[parents[0]] == self.parent[parents[1]]:
            self.parent[parents[0]] -= 1

        for repr in parents[1:]:
            self.parent[repr] = parents[0]

def cluster_from_list(cons: List[Constraint], to_ignore: List[int] = None, ignore_func: Callable[[Constraint], bool] = None) -> List[List[int]]:

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
                
    return list(cluster_lists.values()), removed_clusters