"""
Handles the knowledge encoding for a given class
"""

from typing import Dict, Set, List, Tuple
from pysat.formula import CNF
import itertools

from r1cs_scripts.circuit_representation import Circuit
from bij_encodings.assignment import Assignment
from bij_encodings.single_cons_options import signal_options
from bij_encodings.internal_consistency import internal_consistency
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

    # TODO: have an "only 1 norm" function
    left_normed = list(map(lambda coni : r1cs_norm(in_pair[0][1].constraints[coni])[0],  class_[in_pair[0][0]]))

    right_normed = list(map(lambda coni: r1cs_norm(in_pair[1][1].constraints[coni]), class_[in_pair[1][0]]))

    class_posibilities = {
        name: {}
        for name, _ in in_pair
    }

    pipe = []
    def apply_intersection(i, name, signal, intersect_set):
        if signal_info[name].setdefault(signal, None) is None:

            if len(intersect_set) == 0:
                raise AssertionError(f"Attempted to apply empty set to {i, name, signal}")
            signal_info[name][signal] = intersect_set
        else:

            leftovers = signal_info[name][signal].symmetric_difference(intersect_set)

            pipe.extend(map(
                lambda ass : (1-i, mapp.get_inv_assignment(ass)[1-i]),
                leftovers)
            )

            assumptions.update(map(lambda x : -x, leftovers))

            og = set(signal_info[name][signal])
            signal_info[name][signal].intersection_update(intersect_set)

            if len(signal_info[name][signal]) == 0:
                raise AssertionError(f"In applying {i, name, signal, intersect_set} to {og} found no options")

    def extend_options(opset_possibilities, options):
        # take union of all options
        for name, _ in in_pair:
            for signal in options[name].keys():
                opset_possibilities[name].setdefault(signal, set([])).update(options[name][signal])
        
        return opset_possibilities
    
    # Union of options inside of class
    for i in range(size):

        def get_options(tup):
            j, k = tup
            return (j, k, signal_options([(in_pair[0][0], left_normed[i]), (in_pair[1][0], right_normed[j][k])], mapp, signal_info))

        options_by_jk = map(
            get_options,
            itertools.chain(*map(lambda j : itertools.product([j], range(len(right_normed[j]))), range(size)))
        )

        viable_options = list(filter(
            lambda tup: all(map(lambda opt: len(opt) != 0, 
                                itertools.chain(*map(lambda pair: tup[2][pair[0]].values(), in_pair)))),
            options_by_jk
        ))

        match len(viable_options):

                case 0:
                    raise AssertionError(f"Found constraint {class_[in_pair[0][0]][i]} in {in_pair[0][0]} that cannot be mapped to")
                
                case 1:
                    j, k, options = viable_options[0]
                    class_posibilities = extend_options(class_posibilities, options)

                    for i, (name, _) in enumerate(in_pair):
                        for signal in options[name].keys():
                            # force signal to be one of the options available
                            apply_intersection(i, name, signal, options[name][signal])

                case _:
                    # updating left hand side info, since info requires entire constraint options for logic to work
                    #   right hand side is not guaranteed to have checked every viable cons option for RHS so that is done after as before
                    
                    potential_jk = []

                    class_posibilities[in_pair[0][0]] = {}

                    for j, k, options in viable_options:

                        class_posibilities = extend_options(class_posibilities, options)
                
                        ijk = ckmapp.get_assignment(class_[in_pair[0][0]][i], class_[in_pair[1][0]][j], k)

                            # signal clauses
                        clauses = map(
                            lambda x : list(x) + [-ijk],
                            itertools.chain(*[options[name].values() for name, _ in in_pair])
                        )

                            # constraint clauses
                        potential_jk.append(ijk)
                        formula.extend(clauses)
                    
                    for signal in class_posibilities[in_pair[0][0]].keys(): 
                        apply_intersection(0, in_pair[0][0], signal, class_posibilities[in_pair[0][0]][signal])

                    formula.append(potential_jk)

    # intersection accross classes for other side
    for signal in class_posibilities[in_pair[1][0]].keys():
        apply_intersection(1, in_pair[1][0], signal, class_posibilities[in_pair[1][0]][signal])
    
    pipe.extend([(i, key) for i in range(2) for key in class_posibilities[in_pair[i][0]].keys()])

    internal_consistency(in_pair, mapp, assumptions, signal_info, list(set(pipe)))