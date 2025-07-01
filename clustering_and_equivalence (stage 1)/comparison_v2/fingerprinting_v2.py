"""
    Methods for performing the fingerprinting for equivalent circuits
"""

from typing import List, Dict, Set, Tuple, Callable
from collections import deque
import itertools

from circuits_and_constraints.abstract_circuit import Circuit
from circuits_and_constraints.abstract_constraint import Constraint

from utilities.assignment import Assignment
from utilities.utilities import count_ints

def _key_is_unique(key, name, names, label_to_indices, strict: bool) -> bool:
    if strict:
        return all(len(label_to_indices[_name].get(key, [])) == 1 for _name in names)
    else:
        return len(label_to_indices[name].get(key, [])) == 1

def back_and_forth_preprocessing(names, label_to_indices, index_to_label, init_round, strict: bool):
    """
    Preprocessing for the back_and_forth labelling, to isolate singular classes.

    Classes with just one member do not need to be updated further, here we isolate keys of singular classes
    then remap these to come before all nonsingular keys.

    Parameters
    ----------
    names : List[str]
        Circuit names.
    label_to_indices : Dict[str, Dict[str, List[int]]]
        Reverse mapping from fingerprints to object indices. Assumed to be consistent with index_to_label.
    index_to_label : Dict[str, List[int]]
        Maps each index to a fingerprint label. Assumed to be consistent with label_to_indices.
    init_round: 0 | 1
        Wether this index set is done first or second, used in new name encoding.

    Returns
    -------
    Tuple[int, Dict[str, Set[int]]]
        Number of singular classes and set of indices that will updated.
    """
    nonsingular_keys = {name : [] for name in names}

    singular_remapping = Assignment(assignees=1)

    for name in names:
        for key in label_to_indices[name].keys():
            if _key_is_unique(key, name, names, label_to_indices, strict):
                index_to_label[name][label_to_indices[name][key][0]] = (init_round, singular_remapping.get_assignment(key))
            else:
                nonsingular_keys[name].append(key)

    to_update = {name: [] for name in names}
    num_singular = len(singular_remapping.inv_assignment) - 1

    nonsingular_remapping = Assignment(assignees=1, offset=num_singular)

    for name in names:
        for key in nonsingular_keys[name]:
            new_key = nonsingular_remapping.get_assignment(key)
            to_update[name].extend(label_to_indices[name][key])

            for index in label_to_indices[name][key]: index_to_label[name][index] = (init_round, new_key)

    return num_singular, {name: set(to_update[name]) for name in names}


def back_and_forth_fingerprinting(
            names: List[str],
            in_pair: List[Tuple[str, Circuit]],
            signal_to_normi: Dict[str, List[List[int]]],
            fingerprints_to_normi: Dict[str, Dict[int, List[int]]],
            fingerprints_to_signals: Dict[str, Dict[int, List[int]]],
            initial_mode: bool = True,
            signal_sets : Dict[str, List[int]] | None = None,
            per_iteration_postprocessing: Callable[[List[str], Dict[str, List[Tuple[int, int]]], Dict[str, Dict[Tuple[int, int], List[int]]], Dict, Dict], None] = lambda *args : None,
            return_index_to_fingerprint: bool = False,
            strict_unique: bool = False,
            test_data: dict | None = None,
            constraints_to_fingerprint: Dict[str, List[Constraint]] | None = None,
        ):
    """
    Executes the back-and-forth fingerprinting algorithm for matching equivalent circuit structures.

    Alternates between fingerprinting normalized constraints and signals until no further updates are needed.
    The algorithm refines equivalence classes iteratively to identify structural similarity.

    Parameters
    ----------
    names : List[str]
        Circuit names.
    in_pair : List[Tuple[str, Circuit]]
        List of named circuits to be compared.
    signal_to_normi : Dict[str, List[List[int]]]
        Maps each signal to the indices of the constraints it participates in.
    fingerprints_to_normi : Dict[str, Dict[int, List[int]]]
        Reverse mapping from fingerprints to constraint indices.
    fingerprints_to_signals : Dict[str, Dict[int, List[int]]]
        Reverse mapping from fingerprints to signal indices.
    initial_mode : bool, optional
        Whether to begin fingerprinting with normalized constraints if True, or signals if Falses.
    signal_sets : Optional[Dict[str, List[int]]], optional
        Optional signal set for each circuit.
    per_iteration_postprocessing : Callable[[List[str], Dict[str, List[Tuple[int, int]]], Dict[str, Dict[Tuple[int, int], List[int]]], Dict, Dict], None], optional
        Callback executed after each round for additional behaviour.
    return_index_to_fingerprint : bool, optional
        Whether to return mapping from indices to fingerprint keys.
    test_data : Optional[Dict], optional
        Container for storing test/benchmarking data.

    Returns
    -------
    Union[
        Tuple[Dict[str, Dict[int, List[int]]], Dict[str, Dict[int, List[int]]]],
        Tuple[Dict[str, Dict[int, List[int]]], Dict[str, Dict[int, List[int]]], Dict[str, List[Tuple[int, int]]], Dict[str, Dict[int, Tuple[int, int]]]]
    ]
        If `return_index_to_fingerprint` is True, returns mappings and fingerprint states; otherwise just final fingerprint mappings.
    """
    
    # TODO: think about if we can keep a last_assignment to then check if the assignment has changed and use the pipe that way... this should hopefully reduce the number of checks...

    if signal_sets is None: signal_sets = { name : circ.get_signals() for name, circ in in_pair}
    if constraints_to_fingerprint is None: constraints_to_fingerprint = {name : circ.normalised_constraints for name, circ in in_pair}

    fingerprint_mode = initial_mode
    norm_fingerprints = {name: [None for _ in range(len(constraints_to_fingerprint[name]))] for name in names}
    signal_fingerprints = {name: {sig : None for sig in signal_sets[name]} for name in names}
    
    num_singular_norm_fingerprints, norms_to_update = back_and_forth_preprocessing(names, fingerprints_to_normi, norm_fingerprints, -2 if initial_mode else -1, strict_unique)
    num_singular_signal_fingerprints, signals_to_update = back_and_forth_preprocessing(names, fingerprints_to_signals, signal_fingerprints, -2 if not initial_mode else -1, strict_unique)

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
    prev_normi_to_fingerprints = {name: [norm_fingerprints[name][normi] for normi in range(len(constraints_to_fingerprint[name]))] for name in names}
    prev_signals_to_fingerprints = {name: { sig : signal_fingerprints[name][sig] for sig in signal_sets[name]} for name in names}
    # normi_has_changed, signal_has_changed = {name: [True for _ in range(len(normalised_constraints))] for name in names}, {name: [True for _ in range(circ.nWires)] for name, circ in in_pair}

    get_to_update_normi = lambda normi, name : in_pair[names.index(name)][1].normalised_constraints[normi].signals()
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

            for name, circ in in_pair:
                for normi in norms_to_update[name]:
                    fingerprint(circ, True, constraints_to_fingerprint[name][normi], normi, norm_assignment, norm_fingerprints[name], fingerprints_to_normi[name], 
                                [signal_fingerprints[name]], round_num)
                    
            per_iteration_postprocessing(names, norm_fingerprints, fingerprints_to_normi, prev_normi_to_fingerprints, prev_fingerprints_to_normi, prev_fingerprints_to_normi_count)
            
            # norms_to_update = {name: set([]) for name in names}
                
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
                    signal_fingerprints, num_singular_signal_fingerprints, round_num, strict_unique
                )
              
        else:
            if break_on_next_signal: break

            for name, circ in in_pair:
                for signal in signals_to_update[name]:
                    if signal not in signal_sets[name]: raise AssertionError(f"signal {signal} not in {signal_sets[name]}")
                    fingerprint(circ, False, signal, signal, signal_assignment, signal_fingerprints[name], fingerprints_to_signals[name], 
                                [constraints_to_fingerprint[name], norm_fingerprints[name], prev_signals_to_fingerprints[name], signal_to_normi[name]], round_num)
            
            per_iteration_postprocessing(names, signal_fingerprints, fingerprints_to_signals, prev_signals_to_fingerprints, prev_fingerprints_to_signals, prev_fingerprints_to_signals_count)
            
            # signals_to_update = {name: set([]) for name in names}

            # if we haven't made a new class - update signals then break
            break_on_next_signal = all(map(lambda name : num_singular_signal_fingerprints[round_num-2] + len(fingerprints_to_signals[name].keys()) == previous_distinct_signal_fingerprints[name], names))
            previous_distinct_signal_fingerprints = { name : num_singular_signal_fingerprints[round_num-2] + len(fingerprints_to_signals[name].keys()) for name in names}

            if not break_on_next_norm and not break_on_next_signal:
                signal_assignment, signal_fingerprints, fingerprints_to_signals, prev_normi_to_fingerprints, prev_fingerprints_to_signals, prev_fingerprints_to_signals_count, num_singular_signal_fingerprints, norms_to_update = switch(
                    signal_assignment, signal_fingerprints, fingerprints_to_signals, num_singular_signal_fingerprints, prev_signals_to_fingerprints, prev_fingerprints_to_signals, prev_fingerprints_to_signals_count, signals_to_update, get_to_update_signal, 
                    norm_fingerprints, num_singular_norm_fingerprints, round_num, strict_unique
                )
        
        fingerprint_mode = not fingerprint_mode
        round_num += 1
    
    # print('left')

    ## label_to_vertex gets reset every loop and hence we need to build a final ver to return
    fingerprints_to_normi, fingerprints_to_signals = {name: {} for name in names},  {name: {} for name in names}
    for name in names:
        for normi in range(len(norm_fingerprints[name])): fingerprints_to_normi[name].setdefault(norm_fingerprints[name][normi], []).append(normi)
        for signal in signal_sets[name]: fingerprints_to_signals[name].setdefault(signal_fingerprints[name][signal], []).append(signal)
    
    if return_index_to_fingerprint: return fingerprints_to_normi, fingerprints_to_signals, norm_fingerprints, signal_fingerprints

    return fingerprints_to_normi, fingerprints_to_signals


def fingerprint(circ: Circuit, is_norm: bool, item: Constraint | int, index: int, assignment: Assignment, index_to_fingerprint: List[int], 
                fingerprints_to_indices: Dict[int, List[int]], fingerprint_data, round_num: int):
    """
    Assigns a fingerprint to a constraint norm or signal and updates the mappings.

    Parameters
    ----------
    is_norm : bool
        True if the item is a constraint norm; False if it is a signal.
    item : Constraint | int
        The constraint or signal to fingerprint.
    index : int
        Index of the item being fingerprinted.
    assignment : Assignment
        Assignment object managing the fingerprint IDs.
    index_to_fingerprint : List[Tuple[int, int]]
        Maps index to a (round, fingerprint ID) tuple.
    fingerprints_to_indices : Dict[Tuple[int, int], Set[int]]
        Reverse mapping from fingerprint to index set.
    fingerprint_data : List
        Supporting data for computing the fingerprint.
    round_num : int
        Current fingerprinting round.
    """

    if is_norm:
        fingerprint = item.fingerprint(*fingerprint_data)
    else:       
        fingerprint = circ.fingerprint_signal(item, *fingerprint_data)

    new_hash = assignment.get_assignment(fingerprint)

    index_to_fingerprint[index] = (round_num, new_hash)
    fingerprints_to_indices.setdefault((round_num, new_hash), set([])).add(index)

def switch(assignment: Assignment, fingerprints: Dict[str, List[int]], fingerprints_to_index: Dict[str, Dict[int, List[int]]], num_singular_fingerprints: int, 
           prev_fingerprints: Dict[str, List[int]], prev_fingerprints_to_index:  Dict[str, Dict[int, List[int]]], prev_fingerprints_to_index_count:  Dict[str, Dict[int, int]], to_update: Dict[str, Set[int]],
           get_to_update: Callable[[int, str], List[int]], other_fingerprints, other_num_singular, round_num: int, strict: bool):
    """
    Switches from one fingerprinting phase to another and prepares the next set of updates.

    Determines new singular classes based on latest fingerprint and rehashes so that these are indexed first. Determines which labels colours have actually changed (i.e. have different index subsets)
    to determine which indices actually need to be updated in the next round. Updates various tracking dicts do to with data in the previous round.

    Parameters
    ----------
    assignment : Assignment
        Current assignment of fingerprint IDs.
    fingerprints : Dict[str, List[Tuple[int, int]]]
        Mapping from item index to fingerprint tuple.
    fingerprints_to_index : Dict[str, Dict[Tuple[int, int], List[int]]]
        Reverse mapping of fingerprints to indices.
    num_singular_fingerprints : Dict[int, int]
        Count of singular fingerprints per round.
    prev_fingerprints : Dict[str, List[Tuple[int, int]]]
        Fingerprints from the previous round.
    prev_fingerprints_to_index : Dict[str, Dict[Tuple[int, int], List[int]]]
        Reverse mapping from fingerprint to indices for the previous round.
    prev_fingerprints_to_index_count : Dict[str, Dict[Tuple[int, int], int]]
        Count of items per previous fingerprint.
    to_update : Dict[str, Set[int]]
        Items to update in current round.
    get_to_update : Callable[[int, str], List[int]]
        Function to get related items that depend on a changed index.
    other_fingerprints : Dict[str, Dict[int, Tuple[int, int]]]
        Fingerprints from the other domain (signal or norm).
    other_num_singular : Dict[int, int]
        Number of singular fingerprints in the other domain.
    round_num : int
        Current round number.

    Returns
    -------
    Tuple
        Updated state of fingerprinting, mappings, and items to be updated in next round.
    """

    names = list(fingerprints_to_index.keys())
    next_to_update = {name: set([]) for name in names}

    add_to_update = lambda index, name : next_to_update[name].update(
        filter(lambda oind : other_fingerprints[name][oind][1] > other_num_singular[other_fingerprints[name][oind][0]], 
               get_to_update(index, name)))

    # isolate singular classes
    nonsingular_fingerprints = {name: [] for name in names}
    singular_renaming = Assignment(assignees=1, offset=num_singular_fingerprints[round_num-2])
    
    for name in names:
        for key in fingerprints_to_index[name].keys():
            if _key_is_unique(key, name, names, fingerprints_to_index, strict):
                index = next(iter(fingerprints_to_index[name][key]))
                fingerprints[name][index] = (round_num, singular_renaming.get_assignment(key))
                add_to_update(index, name)

                if round_num > 1 and prev_fingerprints[name][index][0] >= 0:
                    prev_fingerprints_to_index_count[name][prev_fingerprints[name][index]] -= 1
                    if prev_fingerprints_to_index_count[name][prev_fingerprints[name][index]] == 0: 
                        del prev_fingerprints_to_index[name][prev_fingerprints[name][index]]
                        del prev_fingerprints_to_index_count[name][prev_fingerprints[name][index]]

            else:
                nonsingular_fingerprints[name].append(key)

    num_singular_fingerprints[round_num] = num_singular_fingerprints[round_num - 2] + len(singular_renaming.inv_assignment) - 1

    ## needs to be new for if some key is singular in one but not the other
    new_assignment = Assignment(assignees=1, offset=num_singular_fingerprints[round_num])
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

    for name in names:

        # only add actually new classes
        for key in new_fingerprints_to_index[name].keys():

            new_class = new_fingerprints_to_index[name][key]
            prev_fingerprints_to_index[name][key] = new_class
            prev_fingerprints_to_index_count[name][key] = len(new_class)

            an_old_key = prev_fingerprints[name][next(iter(new_fingerprints_to_index[name][key]))]

            if round_num <= 1 or an_old_key[0] < 0:
                for index in new_fingerprints_to_index[name][key]: add_to_update(index, name)  
            else:
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
                    # maintain prev to index
                    del  prev_fingerprints_to_index[name][an_old_key]
                    del  prev_fingerprints_to_index_count[name][an_old_key]

    # return assignment fingerprints fingerprints_to_index other_prev_fingerprints prev_fingerprints_to_index, num_singular_fingerprints, to_update
    return new_assignment, fingerprints, {name: {} for name in names}, {name: {index: other_fingerprints[name][index] for index in next_to_update[name]} for name in names}, prev_fingerprints_to_index, prev_fingerprints_to_index_count, num_singular_fingerprints, next_to_update

def early_exit(fingerprint_to_size: Dict[str, Dict[int, int]]):
    """
    Sanity check for fingerprinting for equivalence fingerprinting.

    Parameters
    ----------
    fingerprint_to_size : Dict[str, Dict[int, int]]
        For each circuit name, mapping of fingerprint key to num indices with that key.

    Raises
    ------
    AssertionError
        If fingerprint sets or class sizes differ between any two circuits.
    """

    names = list(fingerprint_to_size.keys())

    if len(set(fingerprint_to_size[names[0]].keys()).symmetric_difference(fingerprint_to_size[names[1]].keys())) > 0:
        raise AssertionError(f"EE: different classes found, {set(fingerprint_to_size[names[0]].keys()).symmetric_difference(fingerprint_to_size[names[1]].keys())}")

    # enforce that the classes are the same
    for key in fingerprint_to_size[names[0]]:
        lsize, rsize = len(fingerprint_to_size[names[0]][key]), len(fingerprint_to_size[names[1]][key])
        assert lsize == rsize, f"EE: circuit {names[0]} had class {key} size {lsize} whereas circuit {names[1]} had size {rsize}"