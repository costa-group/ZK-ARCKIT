from typing import List, Tuple, Dict, Set
from pysat.formula import CNF
import itertools

from utilities import _signal_data_from_cons_list, getvars
from bij_encodings.assignment import Assignment
from r1cs_scripts.circuit_representation import Circuit

def iterated_label_propagation(
        names: List[str],
        vertices: Dict[str, List[int]],
        vertex_to_adjacent: Dict[str, Dict[int, List[int]]],
        initial_labels: Dict[str, Dict[any, List[int]]] | Dict[str, Dict[int, any]],
        input_inverse: bool = False,
        return_inverse: bool = False
    ) -> Dict[str, Dict[int, List[int]]] | Dict[str, Dict[int, int]]:
    """
    classical neighbourhood label propagation/updating but with added removal of singular labels due to stability
    """
    if input_inverse:
        vertex_to_label = {
            name: {v: None for v in vertices[name]}
            for name in names
        }
    
    else:
        vertex_to_label = initial_labels
        initial_labels = {name: {} for name in names}

        for name in names:
            for vertex in vertices[name]:
                initial_labels[name].setdefault(vertex_to_label[name][vertex], []).append(vertex)

    singular_classes = {
        name: {}
        for name in names
    }

    def remove_lone_classes(classes: Dict[str, Dict[any, List[int]]]) -> Dict[str, Dict[int, List[int]]]:
        non_singular_classes = []

        for key in classes[names[0]].keys():
            if len(classes[names[0]][key]) == 1:
                ## remove from pool
                for name in names:

                    for coni in classes[name][key]: vertex_to_label[name][coni] = len(singular_classes[name])
                    singular_classes[name][len(singular_classes[name])] = classes[name][key]
            else:          
                non_singular_classes.append(key)
        
        # TODO: more efficient way to remove conflicts with new_classes? 
        #       (could always add +len(classes) to right but that causes problems with int comparison)

        new_classes = {name: {} for name in names}
        
        for i, key in enumerate(non_singular_classes):
            for name in names:
                new_classes[name][i + len(singular_classes[name])] = classes[name][key]
                for coni in classes[name][key]: vertex_to_label[name][coni] = i + len(singular_classes[name])

        return new_classes
    
    label_to_vertex = remove_lone_classes(initial_labels)

    while True:
        renaming = Assignment(assignees=2, offset = len(singular_classes[names[0]]))
        new_label_to_vertex = {name: {} for name in names}

        # TODO: make faster -- maps? -- parallelisation? the parallelisation is again trivial
        #   not trivial due to get_assignment, need a lock on assignment...
        #   could assign each thread a modularity and always increase by that modularity...?
        for key in label_to_vertex[names[0]].keys():
            for name in names:
                for coni in label_to_vertex[name][key]:
                    # need conversion to tuple for hashable
                    hash_ = str(renaming.get_assignment(
                        key, 
                        tuple(sorted(map(vertex_to_label[name].__getitem__, vertex_to_adjacent[name][coni])))
                    ))
                    new_label_to_vertex[name].setdefault(hash_, []).append(coni) 

        if len(new_label_to_vertex[names[0]]) == len(label_to_vertex[names[0]]):
            break

        label_to_vertex = remove_lone_classes(new_label_to_vertex)

    if return_inverse:

        for key in label_to_vertex[names[0]].keys():
            for name in names:
                singular_classes[name][key] = label_to_vertex[name][key]

        return singular_classes

    else: 
        return vertex_to_label

def iterated_adjacency_reclassing(
        in_pair: List[Tuple[str, Circuit]],
        classes: Dict[str, Dict[any, List[int]]],
        clusters: Dict[str, List[List[int]]] = None,
        mapp: Assignment = Assignment(),
        cmapp: Assignment = None,
        assumptions: Set[int] = set([]),
        formula: CNF = CNF(),
        signal_info: Dict[str, Dict[int, Set[int]]] = None,
        debug: bool = False
    ) -> Dict[str, List[int]]:

    signal_to_coni = {
        name : _signal_data_from_cons_list(circ.constraints)
        for name, circ in in_pair
    }

    coni_to_adj_coni = {
        name: [
            set(filter(lambda x : x != coni, itertools.chain(*map(signal_to_coni[name].__getitem__, getvars(con)))))
            for coni, con in enumerate(circ.constraints)
        ]
        for name, circ in in_pair
    }

    new_classes = iterated_label_propagation(
        [name for name, _ in in_pair],
        {name: range(circ.nConstraints) for name, circ in in_pair},
        coni_to_adj_coni,
        classes,
        input_inverse=True,
        return_inverse=True
    )

    return new_classes, signal_info





