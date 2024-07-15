"""
Preprocesses classes where there is only 1 constraint and propagates logic
"""

from typing import List, Tuple, Dict, Set, Iterable
from collections import defaultdict
from pysat.formula import CNF
from pysat.card import CardEnc, EncType

from r1cs_scripts.circuit_representation import Circuit
from r1cs_scripts.constraint import Constraint
from normalisation import r1cs_norm
from comparison.constraint_preprocessing import hash_constraint, known_split
from comparison.cluster_preprocessing import groups_from_clusters
from bij_encodings.assignment import Assignment
from bij_encodings.single_cons_options import signal_options
from bij_encodings.batched_info_passing import recluster

def singular_class_propagator(
        in_pair: List[Tuple[str, Circuit]], 
        l_cons_index: int, r_cons_index: int,
        mapp: Assignment, cmapp: Assignment,
        signal_bijection: Dict[str, Dict[int, Set[int]]],
        assumptions: Set[int],
        formula: CNF
):
    """
    Modifies mapp, cmapp, assumptions, formula to propagate information about l_cons_index, r_cons_index
    """

    def assume_signal_bijection(ij: int) -> None:
    
        assumptions.add(ij)

        l, r = mapp.get_inv_assignment(ij)

        for k, name in [(l, "S1"), (r, "S2")]:

            if ij in signal_bijection[name].setdefault(k, set([])) or signal_bijection[name][k] == set([]):
                signal_bijection[name][k] = set([ij])
            else:
                raise AssertionError("Contradicting Assumptions")


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
        
        options = signal_options(lcon, rcon, mapp, assumptions, signal_bijection)

        if any([len(options[name][key]) == 0 for name, _ in in_pair for key in options[name].keys()]):
            # logic inconsistent -- i.e. signal without consistent matching pair
            continue

        possible_k.append(cmapp.get_assignment(l_cons_index, r_cons_index, k))
        logic = []
        for name, _ in in_pair:
            logic.extend(map(lambda tup: (name, tup[0], tup[1]),options[name].items()))

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

        # each op is a different signal's options
        for name, k, op in filter(lambda tup : len(tup[2]) == 1, k_logic[0]): 
            assume_signal_bijection(list(op)[0])

        for name, k, op in filter(lambda tup : len(tup[2]) > 1, k_logic[0]):

            signal_bijection[name][k] = set(op)

            formula.extend(
                CardEnc.equals(
                    lits = signal_bijection[name][k],
                    bound = 1,
                    encoding = EncType.pairwise
                )
            )
            

    if len(possible_k) > 1:
            raise NotImplementedError
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
        clusters: Dict[str, List[List[int]]] = None,
        mapp: Assignment = Assignment(),
        cmapp: Assignment = None,
        assumptions: Set[int] = set([]),
        formula: CNF = CNF(),
        known_signal_mapping: Dict[str, Dict[int, Set[int]]] = None
    ) -> Tuple[ Dict[str, Dict[str, int]], Dict[str, Dict[int, Set[int]]] ]:
    
    if cmapp is None:
        cmapp = Assignment(assignees=3, link = mapp)
    if known_signal_mapping is None:

        known_signal_mapping = {
            name: {}
            for name, _ in in_pair
        }

        for bij in filter( lambda x : 0 < x < len(mapp.assignment), assumptions ):
            l, r = mapp.get_inv_assignment(bij)
            known_signal_mapping[in_pair[0][0]].setdefault(l, set([])).add(bij)
            known_signal_mapping[in_pair[1][0]].setdefault(r, set([])).add(bij)

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
    
    nonsingular_class_keys = filter(lambda key: len( classes[in_pair[0][0]][key] ) > 1, classes[in_pair[0][0]].keys())

    if clusters is None:
        new_classes = {
            name: {} for
            name, _  in in_pair
        }

        hash_mapp = Assignment(assignees=1)

        for ind, key in enumerate(nonsingular_class_keys):
            for name, circ in in_pair:
                for consi in classes[name][key]:
                    new_classes[name].setdefault(f"{ind}:{hash_mapp.get_assignment(known_split(r1cs_norm(circ.constraints[consi]), name, mapp, known_signal_mapping))}", []).append(consi)
    else:
        classes_to_update = map(lambda key: {name: classes[name][key] for name, _ in in_pair}, nonsingular_class_keys)

        new_classes = recluster(in_pair, classes, classes_to_update, mapp, known_signal_mapping)

    if any(len(class_) == 1 for class_ in new_classes[in_pair[0][0]].values()):
        return singular_class_preprocessing(
            in_pair, new_classes, clusters,
            mapp, cmapp, assumptions, formula,
            known_signal_mapping
        )
    else:
        return new_classes, known_signal_mapping