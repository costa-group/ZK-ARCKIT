from r1cs_scripts.constraint import Constraint
from typing import Iterable, Dict
from itertools import chain

def getvars(con: Constraint) -> set:
    return set(filter(lambda x : x != 0, chain(con.A.keys(), con.B.keys(), con.C.keys())))

def count_ints(lints : Iterable[int]) -> Dict[int, int]:
    res = {}
    for i in lints:
        res[i] = res.setdefault(i, 0) + 1
    return sorted(res.items())

    