from typing import List, Dict, Set, Tuple
from collections import deque
import itertools

from bij_encodings.assignment import Assignment

from r1cs_scripts.circuit_representation import Circuit
from r1cs_scripts.constraint import Constraint

from utilities import getvars

def back_and_forth_preprocessing(names, label_to_indices, index_to_label):
    early_exit(label_to_indices)
    num_singular, nonsingular_keys = 0, []

    for key in label_to_indices[names[0]].keys():
        if len(label_to_indices[names[0]][key]) == 1:
            num_singular += 1
            for name in names:
                for index in label_to_indices[name][key]: index_to_label[name][index] = num_singular
        else:
            nonsingular_keys.append(key)

    to_update = {name: [] for name in names}
    for i, key in enumerate(nonsingular_keys):
        for name in names:
            for index in label_to_indices[name][key]:
                to_update[name].append(index)
                index_to_label[name][index] = num_singular + 1 + i
    
    return num_singular, {name: set(to_update[name]) for name in names}


def back_and_forth_fingerprinting(
            names: List[str],
            in_pair: List[Tuple[str, Circuit]],
            normalised_constraints: Dict[str, List[Constraint]],
            signal_to_normi: Dict[str, List[List[int]]],
            fingerprints_to_normi: Dict[str, Dict[int, List[int]]],
            fingerprints_to_signals: Dict[str, Dict[int, List[int]]],
            initial_mode: bool = True,
            return_index_to_fingerprint: bool = False
        ):
    
    # TODO: think about if we can keep a last_assignment to then check if the assignment has changed and use the pipe that way... this should hopefully reduce the number of checks...

    fingerprint_mode = initial_mode
    norm_fingerprints = {name: [None for _ in range(len(normalised_constraints[name]))] for name in names}
    signal_fingerprints = {name: [None for _ in range(circ.nWires)] for name, circ in in_pair}
    
    num_singular_norm_fingerprints, norms_to_update = back_and_forth_preprocessing(names, fingerprints_to_normi, norm_fingerprints)
    num_singular_signal_fingerprints, signals_to_update = back_and_forth_preprocessing(names, fingerprints_to_signals, signal_fingerprints)

    if len(norms_to_update) == len(signals_to_update) == 0: 
        if return_index_to_fingerprint: return fingerprints_to_normi, fingerprints_to_signals, norm_fingerprints, signal_fingerprints # avoids unnescessary work
        return fingerprints_to_normi, fingerprints_to_signals

    previous_distinct_norm_fingerprints, previous_distinct_signal_fingerprints = len(fingerprints_to_normi[names[0]]), len(fingerprints_to_signals[names[0]]) ## dummy values
    break_on_next_norm, break_on_next_signal = False, False

    norm_assignment, signal_assignment = Assignment(assignees=1, offset=num_singular_norm_fingerprints), Assignment(assignees=1, offset=num_singular_signal_fingerprints)
    
    fingerprints_to_normi, fingerprints_to_signals = {name: {} for name in names}, {name: {} for name in names}

    ## TODO: introduce new/prev assignment behaviour with a pipe to reduce the number of checks

    while len(norms_to_update) > 0 or len(signals_to_update) > 0: # greater than 1 due to 'switch'

        # things to update in the next update
        next_to_update = {name: set([]) for name in names}

        if fingerprint_mode:
            if break_on_next_norm: break

            for name in names:
                for normi in norms_to_update[name]:
                    fingerprint(True, normalised_constraints[name][normi], normi, norm_assignment, norm_fingerprints[name], fingerprints_to_normi[name], 
                                signal_fingerprints[name], num_singular_signal_fingerprints, signals_to_update[name], [signal_fingerprints[name]])
            
            norms_to_update = {name: set([]) for name in names}
                
            break_on_next_norm = num_singular_norm_fingerprints + len(fingerprints_to_normi[names[0]].keys()) == previous_distinct_norm_fingerprints
            previous_distinct_norm_fingerprints = num_singular_norm_fingerprints + len(fingerprints_to_normi[names[0]].keys())

            if not break_on_next_norm and not break_on_next_signal:
                norm_assignment, norm_fingerprints, fingerprints_to_normi, num_singular_norm_fingerprints = switch(
                                 norm_assignment, norm_fingerprints, fingerprints_to_normi, num_singular_norm_fingerprints)
              
        else:
            if break_on_next_signal: break

            for name in names:
                for signal in signals_to_update[name]:
                    fingerprint(False, signal, signal, signal_assignment, signal_fingerprints[name], fingerprints_to_signals[name], 
                                norm_fingerprints[name], num_singular_norm_fingerprints, norms_to_update[name], 
                                [norm_fingerprints[name], signal_to_normi[name], normalised_constraints[name]])
            
            signals_to_update = {name: set([]) for name in names}

            # if we haven't made a new class - update signals then break
            break_on_next_signal = num_singular_signal_fingerprints + len(fingerprints_to_signals[names[0]].keys()) == previous_distinct_signal_fingerprints
            previous_distinct_signal_fingerprints = num_singular_signal_fingerprints + len(fingerprints_to_signals[names[0]].keys())

            if not break_on_next_norm and not break_on_next_signal:
                signal_assignment, signal_fingerprints, fingerprints_to_signals, num_singular_signal_fingerprints = switch(
                                   signal_assignment, signal_fingerprints, fingerprints_to_signals, num_singular_signal_fingerprints)
        
        fingerprint_mode = not fingerprint_mode

    ## label_to_vertex gets reset every loop and hence we need to build a final ver to return
    fingerprints_to_normi, fingerprints_to_signals = {name: {} for name in names},  {name: {} for name in names}
    for name in names:
        for normi in range(len(norm_fingerprints[name])): fingerprints_to_normi[name].setdefault(norm_fingerprints[name][normi], []).append(normi)
        for signal in range(len(signal_fingerprints[name])): fingerprints_to_signals[name].setdefault(signal_fingerprints[name][signal], []).append(signal)
    
    if return_index_to_fingerprint: return fingerprints_to_normi, fingerprints_to_signals, norm_fingerprints, signal_fingerprints

    return fingerprints_to_normi, fingerprints_to_signals


def fingerprint(is_norm: bool, item: Constraint | int, index: int, assignment: Assignment, index_to_fingerprint: List[int], 
                fingerprints_to_indices: Dict[int, List[int]], other_index_to_fingerprint: List[int], other_num_singular: int, 
                to_update: Set[int], fingerprint_data):

    if is_norm:
        fingerprint = fingerprint_norms(item, *fingerprint_data)
        if_to_update = getvars(item)
    else:       
        fingerprint = fingerprint_signals(item, *fingerprint_data)
        if_to_update = fingerprint_data[1][item]

    new_hash = assignment.get_assignment(fingerprint)

    # update pipe with new items
    if new_hash != index_to_fingerprint[index]: 
        to_update.update(filter(lambda ind : other_index_to_fingerprint[ind] > other_num_singular, if_to_update))

    new_hash = assignment.get_assignment(fingerprint) 
    index_to_fingerprint[index] = new_hash
    fingerprints_to_indices.setdefault(new_hash, []).append(index)    


def fingerprint_norms(norm : Constraint, signal_fingerprints: List[int]) -> int:
    # norm fingerprint is characteristic of each part
    #   i.e. for each part the values taken by the signals -- given to the fingerprints

    is_ordered = not ( len(norm.A) > 0 and len(norm.B) > 0 and sorted(norm.A.values()) == sorted(norm.B.values()) )

    if is_ordered:
        fingerprint = tuple(map(lambda part : tuple(sorted(map(lambda sig : (signal_fingerprints[sig], part[sig]), part.keys()))), [norm.A, norm.B, norm.C]))
    else:
        # set operations pretty slow ... better way of doing this? -- faster just to check each?
        lsignals, rsignals = norm.A.keys(), norm.B.keys()

        in_both = set(lsignals).intersection(rsignals)
        only_left, only_right = set(lsignals).difference(in_both), set(rsignals).difference(in_both)    

        fingerprint = (tuple(sorted(map(lambda sig : (signal_fingerprints[sig], tuple(sorted(map(lambda part : part[sig], [norm.A, norm.B])))), in_both))), # both parts
                       tuple(sorted(itertools.chain(*itertools.starmap(lambda part, signals : map(lambda sig : (signal_fingerprints[sig], part[sig]), signals) , [(norm.A, only_left), (norm.B, only_right)])))), 
                       tuple(sorted(map(lambda sig : (signal_fingerprints[sig], norm.C[sig]), norm.C.keys()))))

    return fingerprint

def fingerprint_signals(signal : int, constraint_fingerprints: List[int], signal_to_normi: List[List[int]], norms: List[Constraint]) -> int:
    
    # signal fingerprint is characterstic in each norm indexed by norm fingerprint

    fingerprint = []

    for normi in signal_to_normi[signal]:

        norm = norms[normi]
        is_ordered = sorted(norm.A.values()) != sorted(norm.B.values()) ## mayne have ordered lookup (more memory usage ...)

        if is_ordered:       
            Aval, Bval, Cval = [0 if signal not in part.keys() else part[signal] for part in [norm.A, norm.B, norm.C]]
                                              # weird structure here so comparable to unordered
            fingerprint.append((constraint_fingerprints[normi], ((Aval, 0), Bval, Cval)))
        else:
            inA, inB, inC = tuple(map(lambda part : signal in part.keys(), [norm.A, norm.B, norm.C]))
            cVal = 0 if not inC else norm.C[signal]

            if inA and inB:
                fingerprint.append((constraint_fingerprints[normi], (tuple(sorted([norm.A[signal], norm.B[signal]])), 0, cVal)))
            else:
                fingerprint.append((constraint_fingerprints[normi], ((0, 0), norm.A[signal] if inA else (norm.B[signal] if inB else 0), cVal)))

    return tuple(sorted(fingerprint))

def switch(assignment: Assignment, fingerprints: Dict[str, List[int]], fingerprints_to_index: Dict[str, Dict[int, List[int]]], num_singular_fingerprints: int):

    names = list(fingerprints_to_index.keys())

    early_exit(fingerprints_to_index)

    # isolate singular classes
    singular_fingerprints = []
    nonsingular_fingerprints = []
    
    deque(maxlen=0, iterable=map(lambda key : singular_fingerprints.append(key) if len(fingerprints_to_index[names[0]][key]) == 1 else nonsingular_fingerprints.append(key), 
                                 fingerprints_to_index[names[0]].keys()))

    for i, fingerprint in enumerate(singular_fingerprints):
        for name in names:
            index = fingerprints_to_index[name][fingerprint][0]

            fingerprints[name][index] = num_singular_fingerprints + 1 + i

    num_singular_fingerprints = num_singular_fingerprints + len(singular_fingerprints)


    new_assignment = Assignment(assignees=1, offset=num_singular_fingerprints)

    # now need to reset the nonsingular assignment so that we haven't accidentally overwritten anything
    for name in names:
        # assignment retains old hash info to ensure that we can check previous

        for key in nonsingular_fingerprints:
            old_fingerprint = assignment.get_inv_assignment(key)
            new_key = new_assignment.get_assignment(old_fingerprint)

            for index in fingerprints_to_index[name][key]:
                fingerprints[name][index] = new_key
    
    return new_assignment, fingerprints, {name: {} for name in names}, num_singular_fingerprints

def early_exit(fingerprint_to_size: Dict[str, Dict[int, int]]):
    names = list(fingerprint_to_size.keys())

    if len(set(fingerprint_to_size[names[0]].keys()).symmetric_difference(fingerprint_to_size[names[1]].keys())) > 0:
        raise AssertionError(f"EE: different classes found, {set(fingerprint_to_size[names[0]].keys()).symmetric_difference(fingerprint_to_size[names[1]].keys())}")

    # enforce that the classes are the same
    for key in fingerprint_to_size[names[0]]:
        lsize, rsize = len(fingerprint_to_size[names[0]][key]), len(fingerprint_to_size[names[1]][key])
        assert lsize == rsize, f"EE: circuit {names[0]} had class {key} size {lsize} whereas circuit {names[1]} had size {rsize}"