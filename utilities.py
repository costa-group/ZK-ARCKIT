from r1cs_scripts.constraint import Constraint
from typing import Iterable, Dict, List, Set
from itertools import chain

def getvars(con: Constraint) -> set:
    return set(filter(lambda x : x != 0, chain(con.A.keys(), con.B.keys(), con.C.keys())))

def count_ints(lints : Iterable[int]) -> Dict[int, int]:
    res = {}
    for i in lints:
        res[i] = res.setdefault(i, 0) + 1
    return sorted(res.items())

def _signal_data_from_cons_list(cons: List[Constraint]):
    signal_to_cons = {}

    for i, con in enumerate(cons):
        for signal in getvars(con):
            signal_to_cons.setdefault(signal, []).append(i)

    return signal_to_cons

class UnionFind():

    def __init__(self, representative_tracking: bool = False):

        self.parent = {}

        self.representatives = set([]) if representative_tracking else None
    
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
    