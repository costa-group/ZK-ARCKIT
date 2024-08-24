from r1cs_scripts.constraint import Constraint
from typing import Iterable, Dict, List
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
    signal_to_degree = {}

    for i, con in enumerate(cons):
        for signal in getvars(con):
            signal_to_cons.setdefault(signal, []).append(i)
            signal_to_degree[signal] = signal_to_degree.setdefault(signal, 0) + 1

    degree_to_signal = {}

    for signal, degree in signal_to_degree.items():
        degree_to_signal.setdefault(degree, []).append(signal)

    return degree_to_signal, signal_to_cons
    