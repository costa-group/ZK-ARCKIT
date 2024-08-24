from typing import List, Tuple, Dict, Set
from pysat.formula import CNF
import itertools

from utilities import _signal_data_from_cons_list, getvars
from bij_encodings.assignment import Assignment
from r1cs_scripts.circuit_representation import Circuit

def iterated_adjacency_reclassing(
        in_pair: List[Tuple[str, Circuit]],
        classes: Dict[str, List[int]],
        clusters: Dict[str, List[List[int]]] = None,
        mapp: Assignment = Assignment(),
        cmapp: Assignment = None,
        assumptions: Set[int] = set([]),
        formula: CNF = CNF(),
        signal_info: Dict[str, Dict[int, Set[int]]] = None,
        debug: bool = False
    ) -> Dict[str, List[int]]:

    # TODO: prove to self and formally that it halts
    signal_to_coni = {
        name : _signal_data_from_cons_list(circ.constraints)[1]
        for name, circ in in_pair
    }

    coni_to_key = {
        name: [None for _ in range(circ.nConstraints)]
        for name, circ in in_pair
    }

    def update_coni_to_key():

        for name, _ in in_pair:
            for key, class_ in classes[name].items():
                for coni in class_:
                    coni_to_key[name][coni] = key

    update_coni_to_key()

    while True:

        renaming = Assignment(assignees=2)
        new_classes = {name: {} for name, _ in in_pair}

        # TODO: make faster -- maps?
        for key in classes[in_pair[0][0]].keys():
            for name, circ in in_pair:
                if len(classes[name][key]) == 1:
                    new_classes[name][key] = classes[name][key]
                    continue

                for coni in classes[name][key]:
                    adj_coni = filter(lambda x : x != coni, 
                                    itertools.chain(*map(signal_to_coni[name].__getitem__, 
                                                        getvars(circ.constraints[coni]))))
                    hash_ = str(renaming.get_assignment(str(sorted(map(coni_to_key[name].__getitem__, adj_coni))), key))
                    new_classes[name].setdefault(hash_, []).append(coni)        
        
        if len(new_classes[in_pair[0][0]]) == len(classes[in_pair[0][0]]):
            break

        classes = new_classes
        update_coni_to_key()
    
    return classes, signal_info





