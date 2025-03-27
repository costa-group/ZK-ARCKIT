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

from bij_encodings.assignment import Assignment
from comparison_v2.fingerprinting_v2 import fingerprint, switch, back_and_forth_preprocessing

from utilities import getvars, count_ints

def coefficient_only_fingerprinting(names: List[str], normalised_constraints: Dict[str, List[Constraint]]) -> Dict[str, Dict[int, List[int]]]:
    
    def cons_to_coef(C: Constraint):
        return tuple(map(lambda part: tuple(part.values()), [C.A, C.B, C.C]))

    classes = {name: {} for name in names}
    coef_hash = Assignment(assignees=1)

    deque(
        maxlen=0, 
        iterable=itertools.starmap(lambda name, normi : classes[name].setdefault(coef_hash.get_assignment(cons_to_coef(normalised_constraints[name][normi]), []).append(normi), 
                                itertools.chain(*map(lambda name: itertools.product([name], range(len(normalised_constraints)), names)))))
    )

    return classes

def sanity_check_and_revert(
        names: List[str],
        index_to_fingerprints: Dict[str, List[Tuple[int,int]]],
        fingerprints_to_index: Dict[str, Dict[Tuple[int,int], List[int]]],
        prev_index_to_fingerprints: Dict[str, List[Tuple[int,int]]]
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
                                filter(lambda key : len(key_to_names[key]) == 1 or len(fingerprints_to_index[names[0]][key]) != len(fingerprints_to_index[names[1]][key])),
                                key_to_names.keys()
    ))

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
    ## TODO refactor this so that we're not copying so much code from fingerprinting_v2

    fingerprint_mode = initial_mode
    norm_fingerprints = {name: [None for _ in range(len(normalised_constraints[name]))] for name in names}
    signal_fingerprints = {name: [None for _ in range(circ.nWires)] for name, circ in in_pair}
    
    num_singular_norm_fingerprints, norms_to_update = back_and_forth_preprocessing(names, fingerprints_to_normi, norm_fingerprints, -2 if initial_mode else -1)
    num_singular_signal_fingerprints, signals_to_update = back_and_forth_preprocessing(names, fingerprints_to_signals, signal_fingerprints, -2 if not initial_mode else -1)

    if all(map(lambda iterable: len(iterable) == 0, norms_to_update.values())) and all(map(lambda iterable: len(iterable) == 0, signals_to_update.values())):
        if return_index_to_fingerprint: return fingerprints_to_normi, fingerprints_to_signals, norm_fingerprints, signal_fingerprints # avoids unnescessary work
        return fingerprints_to_normi, fingerprints_to_signals

    previous_distinct_norm_fingerprints, previous_distinct_signal_fingerprints = { name :  len(fingerprints_to_normi[name]) for name in names}, { name : len(fingerprints_to_signals[name]) for name in names }
    break_on_next_norm, break_on_next_signal = False, False

    norm_assignment, signal_assignment = Assignment(assignees=1, offset=num_singular_norm_fingerprints), Assignment(assignees=1, offset=num_singular_signal_fingerprints)
    
    fingerprints_to_normi, fingerprints_to_signals = {name: {} for name in names}, {name: {} for name in names}

    num_singular_norm_fingerprints, num_singular_signal_fingerprints = {-2 if initial_mode else -1: num_singular_norm_fingerprints}, {-2 if not initial_mode else -1: num_singular_norm_fingerprints}

    prev_fingerprints_to_normi_count, prev_fingerprints_to_signals_count = {name: {} for name in names}, {name: {} for name in names}
    prev_fingerprints_to_normi, prev_fingerprints_to_signals = {name: {} for name in names}, {name: {} for name in names}
    prev_normi_to_fingerprints, prev_signals_to_fingerprints = {name: None for name in names}, {name: None for name in names}
    # normi_has_changed, signal_has_changed = {name: [True for _ in range(len(normalised_constraints))] for name in names}, {name: [True for _ in range(circ.nWires)] for name, circ in in_pair}

    get_to_update_normi = lambda normi, name : getvars(normalised_constraints[name][normi])
    get_to_update_signal = lambda sig, name : signal_to_normi[name][sig]

    ## TODO: introduce new/prev assignment behaviour with a pipe to reduce the number of checks

    # important -- fingerprint_key now includes round it was made on -- to avoid interference

    # on switch -- check to_update
    #   get the two fingerprints for a signal, check if the set of indices is different -- this indicates a different value
    #       indicates that we need to check it's children

    round_num = 0
    while not ( all(map(lambda iterable: len(iterable) == 0, norms_to_update.values())) and all(map(lambda iterable: len(iterable) == 0, signals_to_update.values())) ):        
        # things to update in the next update

        # print(round_num, fingerprint_mode)

        if fingerprint_mode:
            if break_on_next_norm: break

            for name in names:
                for normi in norms_to_update[name]:
                    fingerprint(True, normalised_constraints[name][normi], normi, norm_assignment, norm_fingerprints[name], fingerprints_to_normi[name], 
                                [signal_fingerprints[name]], round_num)
            
            # norms_to_update = {name: set([]) for name in names}

            sanity_check_and_revert(names, norm_fingerprints, fingerprints_to_normi, prev_normi_to_fingerprints)
                
            break_on_next_norm = all(map(lambda name : num_singular_norm_fingerprints[round_num-2] + len(fingerprints_to_normi[name].keys()) == previous_distinct_norm_fingerprints[name], names))
            previous_distinct_norm_fingerprints = { name : num_singular_norm_fingerprints[round_num-2] + len(fingerprints_to_normi[name].keys()) for name in names}

            if test_data is not None:
                ints = count_ints(map(len, fingerprints_to_normi[names[0]].values()))
                test_data.setdefault("fingerprinting_steps", []).append({
                    "sqr_weight": sum([x[0]**2 * x[1] for x in ints]),
                    "sizes": [x[0] for x in ints],
                    "counts": [x[1] for x in ints]
                })

            if not break_on_next_norm and not break_on_next_signal:
                 # return assignment fingerprints fingerprints_to_index other_prev_fingerprints prev_fingerprints_to_index, num_singular_fingerprints, to_update 
                norm_assignment, norm_fingerprints, fingerprints_to_normi, prev_signals_to_fingerprints, prev_fingerprints_to_normi, prev_fingerprints_to_normi_count, num_singular_norm_fingerprints, signals_to_update = switch(
                    norm_assignment, norm_fingerprints, fingerprints_to_normi, num_singular_norm_fingerprints, prev_normi_to_fingerprints, prev_fingerprints_to_normi, prev_fingerprints_to_normi_count, norms_to_update, get_to_update_normi, 
                    signal_fingerprints, num_singular_signal_fingerprints, round_num
                )
              
        else:
            if break_on_next_signal: break

            for name in names:
                for signal in signals_to_update[name]:
                    fingerprint(False, signal, signal, signal_assignment, signal_fingerprints[name], fingerprints_to_signals[name], 
                                [norm_fingerprints[name], signal_to_normi[name], normalised_constraints[name]], round_num)
            
            sanity_check_and_revert(names, signal_fingerprints, fingerprints_to_signals, prev_signals_to_fingerprints)
            # signals_to_update = {name: set([]) for name in names}

            # if we haven't made a new class - update signals then break
            break_on_next_signal = all(map(lambda name : num_singular_signal_fingerprints[round_num-2] + len(fingerprints_to_signals[name].keys()) == previous_distinct_signal_fingerprints[name], names))
            previous_distinct_signal_fingerprints = { name : num_singular_signal_fingerprints[round_num-2] + len(fingerprints_to_signals[name].keys()) for name in names}

            if not break_on_next_norm and not break_on_next_signal:
                signal_assignment, signal_fingerprints, fingerprints_to_signals, prev_normi_to_fingerprints, prev_fingerprints_to_signals, prev_fingerprints_to_signals_count, num_singular_signal_fingerprints, norms_to_update = switch(
                    signal_assignment, signal_fingerprints, fingerprints_to_signals, num_singular_signal_fingerprints, prev_signals_to_fingerprints, prev_fingerprints_to_signals, prev_fingerprints_to_signals_count, signals_to_update, get_to_update_signal, 
                    norm_fingerprints, num_singular_norm_fingerprints, round_num
                )
        
        fingerprint_mode = not fingerprint_mode
        round_num += 1