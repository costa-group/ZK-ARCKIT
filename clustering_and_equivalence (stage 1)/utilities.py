"""
Set of utility function used throughout the entire codebase
"""

from r1cs_scripts.constraint import Constraint
from typing import Iterable, Dict, List, Set, Tuple
from itertools import chain
from collections import deque

def _is_nonlinear(con: Constraint) -> bool:
        return len(con.A) > 0 and len(con.B) > 0

def getvars(con: Constraint) -> Set[int]:
    """For a given constraint, returns the set of non-constant signals that appear in it"""
    return set(filter(lambda x : x != 0, chain(con.A.keys(), con.B.keys(), con.C.keys())))

def count_ints(lints : Iterable[int]) -> List[Tuple[int, int]]:
    """
    Given an iterable of integers, returns a list of tuples of the form (n, num_occurrences_n). 
    Used primarily in debugging
    """
    res = {}
    for i in lints:
        res[i] = res.setdefault(i, 0) + 1
    return sorted(res.items())

def _signal_data_from_cons_list(cons: List[Constraint], names: List[int] = None) -> Dict[int, List[int]]:
    """
    Given an list of constraint, it returns a dictionary mapping signal -> list of constraints signal appears in

    If names is None then the indexes are the order of cons, otherwise the indexes are zipped with cons.
    """
    signal_to_cons = {}

    for i, con in zip(names if names is not None else range(len(cons)), cons):
        for signal in getvars(con):
            signal_to_cons.setdefault(signal, []).append(i)

    return signal_to_cons

class UnionFind():
    """
    A class holding a UnionFind data structure with path compression

    attributes:
        - parent: Dict[int, int]
            
            Maps each non-negative integer in the domain to it's parent or the negative size if it is the parent
        - self.representatives: Set[int] | None
            
            If representative_tracking is True, then this is set is maintained as all indices that are parents 
    """

    def __init__(self, representative_tracking: bool = False):
        """
        Constructor for UnionFind
        
        parameters:
            representative_tracking: Bool
                If True then the class will maintain a list of representatives in self.representatives
                Note that this incurs additional hashing costs for all operations
        """

        self.parent = {}

        self.representatives = set([]) if representative_tracking else None
    
    def find_noupdate(self, i: int) -> bool:
        """
        If key in parents, returns the key, otherwise returns i.
        Does not add i to the keys if not already present
        """
        if i in self.parent.keys():
            return self.find(i)
        else:
            return i

    def find(self, i:int) -> int:
        """
        find method of UnionFind datastructure

        recursively finds parent of input i
            path compression optimisation means multiple calls to find(i) are amortised O(1)
        """
        assert i >= 0, "invalid i"
        
        if self.representatives is not None and i not in self.parent.keys(): self.representatives.add(i)

        if self.parent.setdefault(i, -1) < 0:
            return i
        else:
            # path compression optimisation
            self.parent[i] = self.find(self.parent[i])
            return self.parent[i]

    def union(self, *args: int) -> None:
        """
        union method of UnionFind datastructure

        determines representative from inputs by largest class size (smallest negative parent)
            This minimises the depth of later find operations
        """

        representatives = sorted(set(map(self.find, args)), key = lambda x: self.parent[x])

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

def dist_to_source_set(source_set: Iterable[int], adjacencies: List[List[int]]) -> Dict[int, int]:
    """
    Given a source_set and adjacencies it returns a dictionary mapping index -> distance to source_set
        the index set of the returned dictionary will be the indices of the connected componens that source_set is in
    """

    distance = {s : 0 for s in source_set}
    queue = deque(source_set)

    while len(queue) > 0:

        curr = queue.popleft()
        
        unseen = list(filter(lambda vert : distance.setdefault(vert, None) is None, adjacencies[curr]))

        queue.extend(unseen)
        for adj in unseen: distance[adj] = distance[curr] + 1

    return distance

def BFS_shortest_path(s: int, t: int, adjacencies: List[List[int]]) -> List[int]:
    """
    simple implementation of targeted BFS
    """

    parent = {s: None}
    reached_t = t == s
    queue = deque([s])

    while not reached_t:
        curr = queue.popleft()
        to_add = list(filter(lambda adj : parent.setdefault(adj, curr) == curr, adjacencies[curr]))

        queue.extend(to_add)
        reached_t = t in to_add

        if len(queue) == 0:
            return []
    
    path = [t]
    while path[-1] != s:
        path.append(parent[path[-1]])
    return path[::-1]

def DFS_reachability(S: int | List[int], T: int | List[int], adjacencies: List[List[int]]) -> bool:
    """
    simple implementation of targeted DFS
    """

    if type(S) == int: S = [S]
    if type(S) == int: T = [T]

    to_check = {s: True for s in S}
    stack = list(S)
    reached_T = any(map(lambda t : t in S, T))


    while not reached_T and len(stack) > 0:
        curr = stack.pop()

        if to_check[curr]: 

            to_check[curr] = False
            to_add = filter(lambda adj : to_check.setdefault(adj, True), adjacencies[curr])
            stack.extend(to_add)
            reached_T = any(map(lambda t : t in to_add, T))
    
    return reached_T