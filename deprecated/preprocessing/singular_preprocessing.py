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
from bij_encodings.assignment import Assignment
from bij_encodings.single_cons_options import signal_options
from bij_encodings.reduced_encoding.red_class_encoder import reduced_encoding_class

def singular_class_preprocessing(
        in_pair: List[Tuple[str, Circuit]],
        classes: Dict[str, Dict[str, int]],
        clusters: Dict[str, List[List[int]]] = None,
        mapp: Assignment = Assignment(),
        cmapp: Assignment = None,
        assumptions: Set[int] = set([]),
        formula: CNF = CNF(),
        known_signal_mapping: Dict[str, Dict[int, Set[int]]] = None,
        debug: bool = False,
        debug_value: int = None
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

    if debug: class_count = 1
    if debug and debug_value is None: debug_value = 1
    for sclass_key in singular_classes:
        if debug:
            print(f"Encoding class of size {class_count}                ", end='\r')
            class_count += 1

        reduced_encoding_class(
            {name: classes[name][sclass_key] for name, _ in in_pair},
            in_pair,
            mapp, cmapp,
            formula, assumptions, 
            known_signal_mapping
        )

        # i, j = classes[in_pair[0][0]][sclass_key][0], classes[in_pair[1][0]][sclass_key][0]

        # singular_class_propagator(
        #     in_pair,
        #     i, j,
        #     mapp, cmapp,
        #     known_signal_mapping,
        #     assumptions,
        #     formula
        # )
    
    # internal consistency now down inside reduced_encoding_class
    # internal_consistency(in_pair, mapp, formula, assumptions, known_signal_mapping)
    nonsingular_class_keys = filter(lambda key: len( classes[in_pair[0][0]][key] ) > 1, classes[in_pair[0][0]].keys())
    
    if debug: print(f"Reclustering, this is batch {debug_value}                            ", end='\r')

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
        
        new_classes = recluster(in_pair, classes_to_update, clusters, mapp, known_signal_mapping)

    if any(len(class_) == 1 for class_ in new_classes[in_pair[0][0]].values()):
        return singular_class_preprocessing(
            in_pair, new_classes, clusters,
            mapp, cmapp, assumptions, formula,
            known_signal_mapping, debug=debug, debug_value=debug_value+1
        )
    else:
        return new_classes, known_signal_mapping