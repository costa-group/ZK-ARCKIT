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

    signal_to_coni = {
        name : _signal_data_from_cons_list(circ.constraints)[1]
        for name, circ in in_pair
    }

    coni_to_key = {
        name: [None for _ in range(circ.nConstraints)]
        for name, circ in in_pair
    }
    
    def remove_lone_classes(classes: Dict[str, Dict[any, List[int]]]) -> Dict[str, Dict[int, List[int]]]:
        non_singular_classes = []

        for key in classes[in_pair[0][0]].keys():
            if len(classes[in_pair[0][0]][key]) == 1:
                ## remove from pool
                for name, _ in in_pair:

                    for coni in classes[name][key]: coni_to_key[name][coni] = len(lone_classes[name])
                    lone_classes[name][len(lone_classes[name])] = classes[name][key]
            else:          
                non_singular_classes.append(key)
        
        # TODO: more efficient way to remove conflicts with new_classes? 
        #       (could always add +len(classes) to right but that causes problems with int comparison)

        new_classes = {name: {} for name, _ in in_pair}
        
        for i, key in enumerate(non_singular_classes):
            for name, _ in in_pair:
                new_classes[name][i + len(lone_classes[in_pair[0][0]])] = classes[name][key]
                for coni in classes[name][key]: coni_to_key[name][coni] = i + len(lone_classes[in_pair[0][0]])

        return new_classes

    # remove lone classes from new_classes
    lone_classes = {name: {} for name, _ in in_pair}
    classes = remove_lone_classes(classes)

    while True:

        renaming = Assignment(assignees=2, offset = len(lone_classes[in_pair[0][0]]))
        new_classes = {name: {} for name, _ in in_pair}

        # TODO: make faster -- maps? -- parallelisation? the parallelisation is again trivial
        #   not trivial due to get_assignment, need a lock on assignment...
        #   could assign each thread a modularity and always increase by that modularity...?
        for key in classes[in_pair[0][0]].keys():
            for name, circ in in_pair:
                for coni in classes[name][key]:
                    adj_coni = filter(lambda x : x != coni, 
                                    itertools.chain(*map(signal_to_coni[name].__getitem__, 
                                                        getvars(circ.constraints[coni]))))
                    # need conversion to tuple for hashable
                    hash_ = str(renaming.get_assignment(key, tuple(sorted(map(coni_to_key[name].__getitem__, adj_coni)))))
                    new_classes[name].setdefault(hash_, []).append(coni) 

        if len(new_classes[in_pair[0][0]]) == len(classes[in_pair[0][0]]):
            break

        classes = remove_lone_classes(new_classes)

    for key in classes[in_pair[0][0]].keys():
        for name, _ in in_pair:
            lone_classes[name][key] = classes[name][key]

    return lone_classes, signal_info





