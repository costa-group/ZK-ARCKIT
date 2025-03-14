"""
Handles the knowledge encoding for a given class
"""

from typing import Dict, Set, List, Tuple
from pysat.formula import CNF
import itertools

from r1cs_scripts.circuit_representation import Circuit
from r1cs_scripts.constraint import Constraint
from bij_encodings.assignment import Assignment
from bij_encodings.single_cons_options import signal_options
from bij_encodings.internal_consistency import internal_consistency

def reduced_encoding_class(
        class_: Dict[str, List[int]], 
        norms : Dict[str, List[List[Constraint]]],
        in_pair: List[Tuple[str, Circuit]],
        mapp: Assignment,
        ckmapp: Assignment,
        formula: CNF,
        assumptions: Set[int],
        signal_info: Dict[str, Dict[int, Set[int]]],
        has_unordered_AB: bool
) -> None:
    r"""
    Encodes a single constraint class into a CNF formula

    As in the paper. We can exclude the necessity for having a full bijection for constraints if we have one for signals (handles
    elsewhere). The intutive encoding here is:

    - Each constraint in left circuit must be mapped to at least 1 normalised constraint from the right circuit
    
    - For every potential mapping (left, right), assuming equivalence, signals must be constrained given the coefficients of the two normalised constraints
    
    This translates to a formal encoding:
    .. math::

        \bigwedge_{l \in Left}( \bigvee_{rn \in RightNorms}(l, rn) \land \bigwedge_{rn \in RightNorms, cons \in Constraints(l, rn)}( \neg (l, rn) \lor cons) )
    
    Parameters
    -----------
        class_: Dict[str, List[int]]
            For each circuitname a list of constraint indices in the class
        norms  Dict[str, List[List[Constraint]]]
            For each circtuiname and each constraint index (indexed in class_) the norms of that constraint
        in_pair: List[Tuple[str, Circuit]]
            Input pair of circuitname/circuit tuple 
        mapp: Assignment
                incoming signal_mapping Assignment object
        ckmapp: Assignment
            incoming constraint_mapping Assignment object
        formula: CNF
            If applicable a preexisting formula to append onto
        assumptions: Set[int]
            incoming fixed pairs
        signal_info
            incoming knowledge about signal potential pairs
        has_unordered_AB: Bool
            Determines if the normalised constraints have unordered AB. Could be calculated for each case but to save time done just once.

    Returns
    -----------
    None
        Mutates the mapp, ckmapp, formula, assumptions, singal_info to include the information from the encoded class
    """
    # NOTE: passes information directly to formula/signal_info

    size = len(class_[in_pair[0][0]])
    class_posibilities = {
        name: {}
        for name, _ in in_pair
    }

    pipe = []
    # for a given name, signal applies the intersection of the intersect_set to the current information for that signal
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

            # This means we now know that this signal has no valid pairing and thus the circuits aren't equivalent
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
            return (j, k, 
                signal_options(
                    [(in_pair[0][0], norms[in_pair[0][0]][i][0]), (in_pair[1][0], norms[in_pair[1][0]][j][k])], 
                    mapp, has_unordered_AB, signal_info))

        options_by_jk = map(
            get_options,
            itertools.chain(*map(lambda j : itertools.product([j], range(len(norms[in_pair[1][0]][j]))), range(size)))
        )

        # a viable option is one where all signals have at least 1 option (inconsistencies are made impossible in encoding)
        viable_options = list(filter(
            lambda tup: all(map(lambda opt: len(opt) != 0, 
                                itertools.chain(*map(lambda pair: tup[2][pair[0]].values(), in_pair)))),
            options_by_jk
        ))

        match len(viable_options):

                case 0:
                    raise AssertionError(f"Found constraint {class_[in_pair[0][0]][i]} in {in_pair[0][0]} that cannot be mapped to")
                
                case 1:
                    # the constraint pair is forced so we can directly apply the lhs info intersection
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
                    
                    # class_posibilites is the union of the information among the entire class
                    # i.e. the lhs is constrainted to the union of options in the class
                    for signal in class_posibilities[in_pair[0][0]].keys(): 
                        apply_intersection(0, in_pair[0][0], signal, class_posibilities[in_pair[0][0]][signal])

                    formula.append(potential_jk)

    # intersection accross classes for other side
    for signal in class_posibilities[in_pair[1][0]].keys():
        apply_intersection(1, in_pair[1][0], signal, class_posibilities[in_pair[1][0]][signal])
    
    # maintain internal consistency
    pipe.extend([(i, key) for i in range(2) for key in class_posibilities[in_pair[i][0]].keys()])
    internal_consistency(in_pair, mapp, assumptions, signal_info, list(set(pipe)))