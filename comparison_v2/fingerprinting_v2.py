from typing import List, Dict, Set, Tuple, Callable
from collections import deque
import itertools

from bij_encodings.assignment import Assignment

from r1cs_scripts.circuit_representation import Circuit
from r1cs_scripts.constraint import Constraint

from utilities import getvars, count_ints

def back_and_forth_preprocessing(names, label_to_indices, index_to_label):
    nonsingular_keys = {name : [] for name in names}

    singular_remapping = Assignment(assignees=1)

    for name in names:
        for key in label_to_indices[name].keys():
            if len(label_to_indices[name][key]) == 1:
                index_to_label[name][label_to_indices[name][key][0]] = (-1, singular_remapping.get_assignment(key))
            else:
                nonsingular_keys[name].append(key)

    to_update = {name: [] for name in names}
    num_singular = len(singular_remapping.inv_assignment) - 1

    nonsingular_remapping = Assignment(assignees=1, offset=num_singular)

    for name in names:
        for key in nonsingular_keys[name]:
            new_key = nonsingular_remapping.get_assignment(key)
            to_update[name].extend(label_to_indices[name][key])

            for index in label_to_indices[name][key]: index_to_label[name][index] = (-1, new_key)

    return num_singular, {name: set(to_update[name]) for name in names}


def back_and_forth_fingerprinting(
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
    
    # TODO: think about if we can keep a last_assignment to then check if the assignment has changed and use the pipe that way... this should hopefully reduce the number of checks...

    fingerprint_mode = initial_mode
    norm_fingerprints = {name: [None for _ in range(len(normalised_constraints[name]))] for name in names}
    signal_fingerprints = {name: [None for _ in range(circ.nWires)] for name, circ in in_pair}
    
    num_singular_norm_fingerprints, norms_to_update = back_and_forth_preprocessing(names, fingerprints_to_normi, norm_fingerprints)
    num_singular_signal_fingerprints, signals_to_update = back_and_forth_preprocessing(names, fingerprints_to_signals, signal_fingerprints)

    if all(map(lambda iterable: len(iterable) == 0, norms_to_update.values())) and all(map(lambda iterable: len(iterable) == 0, signals_to_update.values())):
        if return_index_to_fingerprint: return fingerprints_to_normi, fingerprints_to_signals, norm_fingerprints, signal_fingerprints # avoids unnescessary work
        return fingerprints_to_normi, fingerprints_to_signals

    previous_distinct_norm_fingerprints, previous_distinct_signal_fingerprints = { name :  len(fingerprints_to_normi[name]) for name in names}, { name : len(fingerprints_to_signals[name]) for name in names }
    break_on_next_norm, break_on_next_signal = False, False

    norm_assignment, signal_assignment = Assignment(assignees=1, offset=num_singular_norm_fingerprints), Assignment(assignees=1, offset=num_singular_signal_fingerprints)
    
    fingerprints_to_normi, fingerprints_to_signals = {name: {} for name in names}, {name: {} for name in names}

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
                
            break_on_next_norm = all(map(lambda name : num_singular_norm_fingerprints + len(fingerprints_to_normi[name].keys()) == previous_distinct_norm_fingerprints[name], names))
            previous_distinct_norm_fingerprints = { name : num_singular_norm_fingerprints + len(fingerprints_to_normi[name].keys()) for name in names}

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
            
            # signals_to_update = {name: set([]) for name in names}

            # if we haven't made a new class - update signals then break
            break_on_next_signal = all(map(lambda name : num_singular_signal_fingerprints + len(fingerprints_to_signals[name].keys()) == previous_distinct_signal_fingerprints[name], names))
            previous_distinct_signal_fingerprints = { name : num_singular_signal_fingerprints + len(fingerprints_to_signals[name].keys()) for name in names}

            if not break_on_next_norm and not break_on_next_signal:
                signal_assignment, signal_fingerprints, fingerprints_to_signals, prev_normi_to_fingerprints, prev_fingerprints_to_signals, prev_fingerprints_to_signals_count, num_singular_signal_fingerprints, norms_to_update = switch(
                    signal_assignment, signal_fingerprints, fingerprints_to_signals, num_singular_signal_fingerprints, prev_signals_to_fingerprints, prev_fingerprints_to_signals, prev_fingerprints_to_signals_count, signals_to_update, get_to_update_signal, 
                    norm_fingerprints, num_singular_norm_fingerprints, round_num
                )
        
        fingerprint_mode = not fingerprint_mode
        round_num += 1
    
    # print('left')

    ## label_to_vertex gets reset every loop and hence we need to build a final ver to return
    fingerprints_to_normi, fingerprints_to_signals = {name: {} for name in names},  {name: {} for name in names}
    for name in names:
        for normi in range(len(norm_fingerprints[name])): fingerprints_to_normi[name].setdefault(norm_fingerprints[name][normi], []).append(normi)
        for signal in range(len(signal_fingerprints[name])): fingerprints_to_signals[name].setdefault(signal_fingerprints[name][signal], []).append(signal)
    
    if return_index_to_fingerprint: return fingerprints_to_normi, fingerprints_to_signals, norm_fingerprints, signal_fingerprints

    return fingerprints_to_normi, fingerprints_to_signals


def fingerprint(is_norm: bool, item: Constraint | int, index: int, assignment: Assignment, index_to_fingerprint: List[int], 
                fingerprints_to_indices: Dict[int, List[int]], fingerprint_data, round_num: int):

    if is_norm:
        fingerprint = fingerprint_norms(item, *fingerprint_data)
    else:       
        fingerprint = fingerprint_signals(item, *fingerprint_data)

    new_hash = assignment.get_assignment(fingerprint)

    index_to_fingerprint[index] = (round_num, new_hash)
    fingerprints_to_indices.setdefault((round_num, new_hash), set([])).add(index)    


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

def switch(assignment: Assignment, fingerprints: Dict[str, List[int]], fingerprints_to_index: Dict[str, Dict[int, List[int]]], num_singular_fingerprints: int, 
           prev_fingerprints: Dict[str, List[int]], prev_fingerprints_to_index:  Dict[str, Dict[int, List[int]]], prev_fingerprints_to_index_count:  Dict[str, Dict[int, int]], to_update: Dict[str, Set[int]],
           get_to_update: Callable[[int, str], List[int]], other_fingerprints, other_num_singular, round_num: int):

    names = list(fingerprints_to_index.keys())
    next_to_update = {name: set([]) for name in names}

    add_to_update = lambda index, name : next_to_update[name].update(filter(lambda oind : other_fingerprints[name][oind][1] > other_num_singular, get_to_update(index, name)))

    # isolate singular classes
    nonsingular_fingerprints = {name: [] for name in names}
    singular_renaming = Assignment(assignees=1, offset=num_singular_fingerprints)

    for name in names:
        for key in fingerprints_to_index[name].keys():
            if len(fingerprints_to_index[name][key]) == 1:
                index = next(iter(fingerprints_to_index[name][key]))
                fingerprints[name][index] = (round_num, singular_renaming.get_assignment(key))
                add_to_update(index, name)

                if round_num > 1:
                    prev_fingerprints_to_index_count[name][prev_fingerprints[name][index]] -= 1
                    if prev_fingerprints_to_index_count[name][prev_fingerprints[name][index]] == 0: 
                        del prev_fingerprints_to_index[name][prev_fingerprints[name][index]]
                        del prev_fingerprints_to_index_count[name][prev_fingerprints[name][index]]

            else:
                nonsingular_fingerprints[name].append(key)

    num_singular_fingerprints += len(singular_renaming.inv_assignment) - 1

    ## needs to be new for if some key is singular in one but not the other
    new_assignment = Assignment(assignees=1, offset=num_singular_fingerprints)
    new_fingerprints_to_index = {name: {} for name in names}

    # now need to reset the nonsingular assignment so that we haven't accidentally overwritten anything
    for name in names:
        # assignment retains old hash info to ensure that we can check previous
        for key in nonsingular_fingerprints[name]:
            old_fingerprint = assignment.get_inv_assignment(key[1])
            new_key = new_assignment.get_assignment(old_fingerprint)

            new_fingerprints_to_index[name][(round_num, new_key)] = fingerprints_to_index[name][key]

            for index in fingerprints_to_index[name][key]:
                fingerprints[name][index] = (round_num, new_key)

    ## TODO: do this better, so not comparing each class multiple times
    ## TODO: when the prev_fingerprint was from a very old round -- this struggles

    num_skipped = {name: 0 for name in names}
    num_og_skipped = {name: 0 for name in names}

    for name in names:

        # only add actually new classes
        for key in new_fingerprints_to_index[name].keys():

            new_class = new_fingerprints_to_index[name][key]
            prev_fingerprints_to_index[name][key] = new_class
            prev_fingerprints_to_index_count[name][key] = len(new_class)

            if round_num <= 1:
                for index in new_fingerprints_to_index[name][key]: add_to_update(index, name)  
            else:
                
                an_old_key = prev_fingerprints[name][next(iter(new_fingerprints_to_index[name][key]))]
                prev_class = prev_fingerprints_to_index[name][an_old_key]

                if len(prev_class) != len(new_class) or prev_class != new_class:
                    for index in new_class: 
                        add_to_update(index, name)

                        # maintain prev to index
                        index_old_key = prev_fingerprints[name][index]
                        prev_fingerprints_to_index_count[name][index_old_key] -= 1

                        if prev_fingerprints_to_index_count[name][index_old_key] == 0: 
                            del prev_fingerprints_to_index[name][index_old_key]
                            del prev_fingerprints_to_index_count[name][index_old_key]
                    
                else:
                    num_og_skipped[name] += len(new_class)  
                    
                    # maintain prev to index
                    del  prev_fingerprints_to_index[name][an_old_key]
                    del  prev_fingerprints_to_index_count[name][an_old_key]

    print('round_num', round_num)
    print('num_skipped', num_skipped)
    print('num_og_skipped', num_og_skipped)
    print('num_to_update', list(map(len, next_to_update.values())))
    print(num_singular_fingerprints)
    # print(prev_fingerprints_to_index_count)
    print()
    # return assignment fingerprints fingerprints_to_index other_prev_fingerprints prev_fingerprints_to_index, num_singular_fingerprints, to_update

    return new_assignment, fingerprints, {name: {} for name in names}, {name: {index: other_fingerprints[name][index] for index in next_to_update[name]} for name in names}, prev_fingerprints_to_index, prev_fingerprints_to_index_count, num_singular_fingerprints, next_to_update

def early_exit(fingerprint_to_size: Dict[str, Dict[int, int]]):
    names = list(fingerprint_to_size.keys())

    if len(set(fingerprint_to_size[names[0]].keys()).symmetric_difference(fingerprint_to_size[names[1]].keys())) > 0:
        raise AssertionError(f"EE: different classes found, {set(fingerprint_to_size[names[0]].keys()).symmetric_difference(fingerprint_to_size[names[1]].keys())}")

    # enforce that the classes are the same
    for key in fingerprint_to_size[names[0]]:
        lsize, rsize = len(fingerprint_to_size[names[0]][key]), len(fingerprint_to_size[names[1]][key])
        assert lsize == rsize, f"EE: circuit {names[0]} had class {key} size {lsize} whereas circuit {names[1]} had size {rsize}"