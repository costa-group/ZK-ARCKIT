"""
Function that propagates signal pair rules
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
    """
    Maintains the internal consistency of the signal_info construct.

    Propagates, and maintains, two internal rules about bijections. Given a signal pair (l, r):
    1. a pair is valid only if **both** l, and r have the other as a potential pair
    2. if either of l, **or** r has only (l, r) as the only potential pair so should the other

    Parameters
    ----------
        in_pair: List[Tuple[str, Circuit]]
            Pair of circuit/name pairs for the input circuits
        mapp: Assignment
            Signal pair assigment mapping
        assumptions: Set[int]
            Set of known forced assignments. Here to be mutated
        signal_info: Dict[str, Dict[int, Set[int]]]
            For each circuit name, and for each signal, a mapping to the set of signals in the other 
            constraint amongst which it must be paired with at least one.
        pipe: List[Tuple[int, int]] | None
            The list of signals to check. Saves time when calling with a pipe, if None checks every signal.
    
    Returns
    ---------
    None
        Mutates the assumptions, and signal_info to maintain the consistency rules.
    
    """
    
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