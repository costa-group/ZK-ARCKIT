"""
Propagates, and maintains, two internal rules about bijections:
    1. if only one of (l, r) has the other as a potential pair the pair is invalid
    2. if either of (l, r) has only (l, r) as a potential pair then (l, r) is forced in the other
"""


from typing import List, Tuple, Dict, Set

from r1cs_scripts.circuit_representation import Circuit

from bij_encodings.assignment import Assignment

def internal_consistency(
    in_pair: List[Tuple[str, Circuit]],
    mapp: Assignment,
    assumptions: Set[int],
    signal_info: Dict[str, Dict[int, Set[int]]],
    pipe: List[Tuple[int, int]] = None
) -> None:
    
    if pipe is None:
        pipe = list(
            (i, sig) for i in range(2) for sig in range(1, in_pair[i][1].nWires)
        )
    
    while len(pipe) > 0:

        i, signal = pipe.pop()

        # name, signal type value
        name, oname = in_pair[i][0], in_pair[1-i][0]

        # if the other signal doesn't have the value then it isn't a valid assignment
        inconsistent_assignments = [
            ass for ass in signal_info[name][signal]
            if ass not in signal_info[oname][mapp.get_inv_assignment(ass)[1-i]]
        ]
        assumptions.update(map(lambda x : -x, inconsistent_assignments))

        signal_info[name][signal].difference_update(inconsistent_assignments)

        if len(signal_info[name][signal]) == 0:
            raise AssertionError(f"Found signal {name, signal} with no mapping after removing {inconsistent_assignments}")
        elif len(signal_info[name][signal]) == 1:
            # if there is only 1 value, then that is a 'correct' assignment

            ass = next(iter(signal_info[name][signal]))
            osignal = mapp.get_inv_assignment(ass)[1-i]

            pipe.extend(
                map(lambda x : (i, mapp.get_inv_assignment(x)[i]), 
                filter(lambda x : x != ass, signal_info[oname][osignal]))
            )
            signal_info[oname][osignal] = set([ass])