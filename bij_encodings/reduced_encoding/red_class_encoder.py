"""
Handles the knowledge encoding for a given class
"""

from typing import Dict, Set, List, Tuple
from pysat.formula import CNF
import itertools

from r1cs_scripts.circuit_representation import Circuit
from bij_encodings.assignment import Assignment
from bij_encodings.single_cons_options import signal_options
from normalisation import r1cs_norm

def reduced_encoding_class(
        class_: Dict[str, List[int]], 
        in_pair: List[Tuple[str, Circuit]],
        mapp: Assignment,
        ckmapp: Assignment,
        formula: CNF,
        assumptions: Set[int],
        signal_info: Dict[str, Dict[int, Set[int]]]
) -> None:
    # NOTE: passes information directly to formula/signal_info

    size = len(class_[in_pair[0][0]])

    left_normed = list(map(lambda coni : r1cs_norm(in_pair[0][1].constraints[coni])[0],  class_[in_pair[0][0]]))

    right_normed = list(map(lambda coni: r1cs_norm(in_pair[1][1].constraints[coni]), class_[in_pair[1][0]]))

    class_posibilities = {
        name: {}
        for name, _ in in_pair
    }

    pipe = []
    def apply_intersection(i, name, signal, intersect_set):
        if signal_info[name].setdefault(signal, None) is None:
            signal_info[name][signal] = intersect_set
        else:
            leftovers = signal_info[name][signal].symmetric_difference(intersect_set)

            pipe.extend(map(
                lambda ass : (1-i, mapp.get_inv_assignment(ass)[1-i]),
                leftovers)
            )

            assumptions.update(map(lambda x : -x, leftovers))
            signal_info[name][signal].intersection_update(intersect_set)
    


    def extend_options(opset_possibilities, options):
        # take union of all options
        for name, _ in in_pair:
            for signal in options[name].keys():
                opset_possibilities[name][signal] = opset_possibilities[name].setdefault(signal, set([])
                                                                            ).union(options[name][signal])
        
        return opset_possibilities
    
    # Union of options inside of class
    for i in range(size):
        potential_pairings = []
        for j in range(size):
            for k in range(len(right_normed[j])):

                options = signal_options(left_normed[i], right_normed[j][k], mapp, assumptions, signal_info) 

                # is pairing non-viable
                if any(map(
                        lambda x : len(x) == 0,
                        itertools.chain(*[options[name].values() for name, _ in in_pair])
                    )):
                    continue

                # if pairing is viable, add clauses to formula and update signal info
                class_posibilities = extend_options(class_posibilities, options)    
                
                ijk = ckmapp.get_assignment(class_[in_pair[0][0]][i], class_[in_pair[1][0]][j], k)

                    # signal clauses
                clauses = map(
                    lambda x : list(x) + [-ijk],
                    itertools.chain(*[options[name].values() for name, _ in in_pair])
                )

                    # constraint clauses
                potential_pairings.append(ijk)
                formula.extend(clauses)

                    # used to force signal values if it's the only option
                if len(potential_pairings) == 1: last_options = options
                else: last_options = None
        
        if len(potential_pairings) == 0:
            ## TODO: pass nonviable through encoding
            raise AssertionError(f"Found constraint {class_[in_pair[0][0]][i]} that cannot be mapped to") 
        
        elif len(potential_pairings) == 1:
            ## NOTE: this means that left has only 1 potential right pair, meaning it is that pair (if True)
            for i, (name, _) in enumerate(in_pair):
                for signal in last_options[name].keys():
                    # force signal to be one of the options available
                    apply_intersection(i, name, signal, last_options[name][signal])
        formula.append(potential_pairings)
    
    # intersection accross classes
    for i, (name, _) in enumerate(in_pair):
        for signal in class_posibilities[name].keys():
            apply_intersection(i, name, signal, class_posibilities[name][signal])
    
    pipe.extend([(i, key) for i in range(2) for key in class_posibilities[in_pair[i][0]].keys()])

    while len(pipe) > 0:

        i, value = pipe.pop()

        # name, signal type value
        name, oname = in_pair[i][0], in_pair[1-i][0]

        # if the other signal doesn't have the value then it isn't a valid assignment
        inconsistent_assignments = [
            ass for ass in signal_info[name][value]
            if ass not in signal_info[oname][mapp.get_inv_assignment(ass)[1-i]]
        ]
        assumptions.update(map(lambda x : -x, inconsistent_assignments))

        signal_info[name][value].difference_update(inconsistent_assignments)

        if len(signal_info[name][value]) == 0:
            raise AssertionError(f"Found signal {name, value} with no mapping after removing {inconsistent_assignments}")
        elif len(signal_info[name][value]) == 1:
            # if there is only 1 value, then that is a 'correct' assignment

            ass = next(iter(signal_info[name][value]))
            osignal = mapp.get_inv_assignment(ass)[1-i]

            pipe.extend(
                map(lambda x : (i, mapp.get_inv_assignment(x)[i]), 
                filter(lambda x : x != ass, signal_info[oname][osignal]))
            )
            signal_info[oname][osignal] = set([ass])