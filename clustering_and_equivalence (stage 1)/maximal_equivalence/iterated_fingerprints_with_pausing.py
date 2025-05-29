"""
as iterated fingerprinting

but every fingerprint iterations has a sanity check:
 - any fingerprints not in the other are now reverted to the previous
 - any fingerprints that have different sizes are reverted to the previous

Once we don't change post-revert we complete 1 more iteration (no reverts) up to constraints
 - then encode the classes with MaxSAT. And run the MaxSAT returning the maximal equivalent subgraphs
"""

from typing import List, Tuple, Dict
from collections import deque
import itertools

from r1cs_scripts.circuit_representation import Circuit
from r1cs_scripts.constraint import Constraint

from utilities.assignment import Assignment
from comparison_v2.fingerprinting_v2 import back_and_forth_fingerprinting

from utilities.utilities import getvars, count_ints

def coefficient_only_fingerprinting(names: List[str], normalised_constraints: Dict[str, List[Constraint]]) -> Dict[str, Dict[int, List[int]]]:
    
    def cons_to_coef(C: Constraint):
        return tuple(map(lambda part: tuple(part.values()), [C.A, C.B, C.C]))

    classes = {name: {} for name in names}
    coef_hash = Assignment(assignees=1)

    deque(
        maxlen=0, 
        iterable=itertools.starmap(lambda name, normi : classes[name].setdefault(coef_hash.get_assignment(cons_to_coef(normalised_constraints[name][normi])), []).append(normi), 
                                itertools.chain(*map(lambda name: itertools.product([name], range(len(normalised_constraints[name]))), names)))
    )

    return classes

def sanity_check_and_revert(
        names: List[str],
        index_to_fingerprints: Dict[str, List[Tuple[int,int]]],
        fingerprints_to_index: Dict[str, Dict[Tuple[int,int], List[int]]],
        prev_index_to_fingerprints: Dict[str, List[Tuple[int,int]]],
        *args
    ):
    # identify keys to be reverted.
        # keys not in other circuit
        # keys of different sizes

    assert len(names) == 2
    
    key_to_names = {}

    deque(maxlen=0, iterable=itertools.starmap(lambda name, key : key_to_names.setdefault(key, []).append(name), 
                                 itertools.chain(*map(lambda name : itertools.product([name], fingerprints_to_index[name].keys()), names))))

    def revert(key: Tuple[int, int]):
        for name in key_to_names[key]:
            indexset = fingerprints_to_index[name][key]
            prev_key = prev_index_to_fingerprints[name][next(iter(indexset))]
            for index in indexset: index_to_fingerprints[name][index] = prev_key
            del fingerprints_to_index[name][key]

    deque(maxlen=0, iterable =  map(revert, 
                                filter(lambda key : len(key_to_names[key]) == 1 or len(fingerprints_to_index[names[0]][key]) != len(fingerprints_to_index[names[1]][key]),
                                key_to_names.keys()
    )))

    return index_to_fingerprints, fingerprints_to_index, prev_index_to_fingerprints

def iterated_fingerprints_w_reverting(
    names: List[str],
    in_pair: List[Tuple[str, Circuit]],
    normalised_constraints: Dict[str, List[Constraint]],
    signal_to_normi: Dict[str, List[List[int]]],
    fingerprints_to_normi: Dict[str, Dict[int, List[int]]],
    fingerprints_to_signals: Dict[str, Dict[int, List[int]]],
    initial_mode: bool = True,
    return_index_to_fingerprint: bool = False,
    test_data: dict | None = None 
    ):
    return back_and_forth_fingerprinting(
        names, in_pair, normalised_constraints, signal_to_normi, fingerprints_to_normi, fingerprints_to_signals, initial_mode = initial_mode, 
        per_iteration_postprocessing = sanity_check_and_revert, return_index_to_fingerprint = return_index_to_fingerprint, test_data = test_data, strict_unique=True
    )