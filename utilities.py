from r1cs_scripts.constraint import Constraint
from typing import Iterable, Dict, List, Set
from itertools import chain
from collections import deque

def getvars(con: Constraint) -> set:
    return set(filter(lambda x : x != 0, chain(con.A.keys(), con.B.keys(), con.C.keys())))

def count_ints(lints : Iterable[int]) -> Dict[int, int]:
    res = {}
    for i in lints:
        res[i] = res.setdefault(i, 0) + 1
    return sorted(res.items())

def _signal_data_from_cons_list(cons: List[Constraint], names: List[int] = None):
    signal_to_cons = {}

    for i, con in zip(names if names is not None else range(len(cons)), cons):
        for signal in getvars(con):
            signal_to_cons.setdefault(signal, []).append(i)

    return signal_to_cons

class UnionFind():

    def __init__(self, representative_tracking: bool = False):

        self.parent = {}

        self.representatives = set([]) if representative_tracking else None
    
    def find_noupdate(self, i: int) -> bool:
        """
        If key in parents, returns the key, otherwise returns i
        """
        if i in self.parent.keys():
            return self.find(i)
        else:
            return i

    def find(self, i:int) -> int:
        assert i >= 0, "invalid i"
        
        if self.representatives is not None and i not in self.parent.keys(): self.representatives.add(i)

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
            if self.representatives is not None : self.representatives.remove(repr)
            self.parent[repr] = representatives[0]
    
    def get_representatives(self) -> Set[int]:
        return self.representatives

def is_not_none(x) -> bool: 
    """
    Returns if x is not None.
    Just used to make some maps/filters nicer to read
    """
    return x is not None

def BFS_shortest_path(s: int, t: int, adjacencies: List[List[int]]) -> List[int]:
    """
    simple implementation of targeted BFS that assumes adjacencies only contains the adjacent indices
    """

    parent = {s: None}
    reached_t = False
    queue = deque([s])

    while not reached_t:
        curr = queue.popleft()
        queue.extend(filter(lambda adj : parent.setdefault(adj, curr) == curr, adjacencies[curr]))
        reached_t = t in parent.keys()

        if len(queue) == 0:
            return []
    
    path = [t]
    while path[-1] != s:
        path.append(parent[path[-1]])
    return path[::-1]