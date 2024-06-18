"""
Preprocesses classes where there is only 1 constraint and propagates logic
"""

from typing import List, Tuple, Dict, Set
from collections import defaultdict
from pysat.formula import CNF
from pysat.card import CardEnc, EncType

from r1cs_scripts.circuit_representation import Circuit
from r1cs_scripts.constraint import Constraint
from normalisation import r1cs_norm
from comparison.constraint_preprocessing import hash_constraint
from bij_encodings.assignment import Assignment
from bij_encodings.single_cons_options import signal_options

# TODO: update signal_bijection to map to a set of potential values
# TODO: update signal_bijection to be ints of mapp values rather than true mapping

def singular_class_propagator(
        in_pair: List[Tuple[str, Circuit]], 
        l_cons_index: int, r_cons_index: int,
        mapp: Assignment, cmapp: Assignment,
        signal_bijection: Dict[str, Dict[int, int]],
        assumptions: Set[int],
        formula: CNF
):
    """
    Modifies mapp, cmapp, assumptions, formula to propagate information about l_cons_index, r_cons_index
    """

    def assume_signal_bijection(ij: int) -> None:
    
        assumptions.add(ij)

        l, r = mapp.get_inv_assignment(ij)

        if signal_bijection["S1"].setdefault(l, r) != r: raise AssertionError("Contradicting Assumptions")
        if signal_bijection["S2"].setdefault(r, l) != l: raise AssertionError("Contradicting Assumptions")


    # get 1st norm of l, norms of r.
    lcon  = r1cs_norm(in_pair[0][1].constraints[l_cons_index])[0]
    rcons = r1cs_norm(in_pair[1][1].constraints[r_cons_index])

    possible_k = []
    k_logic = []

    forced_signals = {
        name: {}
        for name, _ in in_pair
    }

    # check signal_bijection to see any forced decisions about 
    # IU-II to get info about signals
    for k, rcon in enumerate(rcons):
        
        options = signal_options(lcon, rcon, mapp, signal_bijection)

        if any([len(options[name][key]) == 0 for name, _ in in_pair for key in options[name].keys()]):
            # logic inconsistent -- i.e. signal without consistent matching pair
            continue

        possible_k.append(cmapp.get_assignment(l_cons_index, r_cons_index, k))
        logic = []
        for name, _ in in_pair:
            logic.extend(options[name].values())

            for key in options[name].keys():
                forced_signals[name][key] = forced_signals[name].setdefault(key, set([])).union(options[name][key])
        k_logic.append(logic)

    for name, _ in in_pair:
        for key in filter(lambda k : len(forced_signals[name][k]) == 1, forced_signals[name].keys()):
            ij = iter(forced_signals[name][key]).__next__()
            assume_signal_bijection(ij)
            
    if len(possible_k) == 0: raise AssertionError("No Valid Mapping means Non-Equivalent Circuits")
    if len(possible_k) == 1: 
        
        # logic is now forced
        assumptions.update(possible_k)

        # each op is an different signal's options
        for op in filter(lambda x : len(x) == 1, k_logic[0]): 
            assume_signal_bijection(list(op)[0])

        for op in filter(lambda x : len(x) > 1, k_logic[0]):

            # constraint bijection logic
            formula.extend(
                CardEnc.equals(
                    lits = possible_k,
                    bound = 1,
                    encoding = EncType.pairwise
                )
            )

    if len(possible_k) > 1:
            # NOTE: untested

            # adds formula for 
            formula.extend(
                CardEnc.equals(
                    lits = possible_k,
                    bound = 1,
                    encoding=EncType.pairwise
                )
            )

            # TODO: check to see any forced signals add to assumption

            # logic for each individual constraint
            for i, logic in enumerate(k_logic):
                formula.extend(map( lambda x : list(x) + [-possible_k[i]], logic))

            # TODO: add assumptions for generic clauses
            # at most 1 bij for signals
            for name, _ in in_pair:
                for key in forced_signals[name].keys():
                    formula.extend(
                        CardEnc.atmost(
                            lits = forced_signals[name][key],
                            bound = 1,
                            encoding = EncType.pairwise
                        )
                    )

def singular_class_preprocessing(
        in_pair: List[Tuple[str, Circuit]], 
        classes: Dict[str, Dict[str, int]],
        mapp: Assignment,
        cmapp: Assignment,
        assumptions: Set[int],
        formula: CNF,
        known_signal_mapping: Dict[str, Dict[int, int]] = None
    ) -> Tuple[ Dict[str, Dict[int, int]], Dict[str, Dict[str, int]] ]:
    
    
    if known_signal_mapping is None:

        known_signal_mapping = {
            name: {}
            for name, _ in in_pair
        }

        for bij in filter( lambda x : 0 < x < len(mapp.assignment), assumptions ):
            l, r = mapp.get_inv_assignment(bij)
            known_signal_mapping[in_pair[0][0]][l] = r
            known_signal_mapping[in_pair[1][0]][r] = l

    singular_classes = filter(lambda key: len( classes[in_pair[0][0]][key] ) == 1, classes[in_pair[0][0]].keys())

    for sclass_key in singular_classes:
        i, j = classes[in_pair[0][0]][sclass_key][0], classes[in_pair[1][0]][sclass_key][0]

        singular_class_propagator(
            in_pair,
            i, j,
            mapp, cmapp,
            known_signal_mapping,
            assumptions,
            formula
        )

    nonsingular_classes = filter(lambda key: len( classes[in_pair[0][0]][key] ) > 1, classes[in_pair[0][0]].keys())

    new_classes = {
        name: defaultdict(lambda : [])
        for name, _ in in_pair
    }

    # Redo the classes with known_signal informations
    for class_key in nonsingular_classes:
        
        # hashing with new info
        for name, circ in in_pair:
            
            for i in classes[name][class_key]:

                hash_ = hash_constraint(circ.constraints[i], known_signal_mapping, mapp, name)

                new_classes[name][hash_].append(i)

    if any(len(class_) == 1 for class_ in new_classes[in_pair[0][0]].values()):
        return singular_class_preprocessing(
            in_pair, new_classes,
            mapp, cmapp, assumptions, formula,
            known_signal_mapping
        )
    else:
        return known_signal_mapping, new_classes
