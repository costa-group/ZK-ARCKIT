"""
Preprocessing method using label passing to encode structural information into labels
"""

from typing import List, Tuple, Dict, Set
from pysat.formula import CNF
import itertools

from utilities.utilities import _signal_data_from_cons_list
from utilities.assignment import Assignment
from circuits_and_constraints.abstract_circuit import Circuit

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

    At each step we rehash every non-unique label to be the current label, and the unordered labels of all adjacent vertices. This 
    ensure, after finishing, that two vertices have the same label only if there is a bijection between all walks starting from each vertex
    that maintains initial labels, and vertex degree in all but the final vertex of the walk. For a fool proof relating to trees see
    the thesis.

    Parameters
    -----------
        names: List[str]
            Index names for various dictionaries representing the two graphs.
        vertices: Dict[str, List[int]]
            For each graph, the integers representing the vertex indices for that graph
        vertex_to_adjacent: Dict[str, Dict[int, List[int]]]
            For each graph, for each vertex, the adjacent vertices for that vertex
        initial_labels: Dict[str, Dict[any, List[int]]] | Dict[str, Dict[int, any]]
            Initial labels. For each graph, either mapping label_to_vertices or vertex_to_label respectively determined by input_inverse
        input_inverse: bool = False
            If True the initial_label is treated as label_to_vertex, otherwise it is treated as vertex_to_label
        return_inverse: bool = False
            If True returns label_to_vertices otherwise returns vertex_to_label
    
    Return
    ---------
    Dict[str, Dict[int, List[int]]] | Dict[str, Dict[int, int]]
        The final labels for the given vertices. If return_inverse is True returns label_to_vertices otherwise vertex_to_label
    """
    if input_inverse:
        vertex_to_label = {
            name: {v: -1 for v in vertices[name]}
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
    max_singular_label = 0

    # subordinate function to save unique labels and remove from iterative update process
    def remove_lone_classes(classes: Dict[str, Dict[any, List[int]]], max_singular_label) -> Dict[str, Dict[int, List[int]]]:

        singular_renaming = Assignment(assignees=1, offset = max_singular_label)
        non_singular_classes = []

        for key, name in itertools.chain(*[itertools.product(classes[name].keys(), [name]) for name in names]):
            
            if len(classes[name][key]) == 1:
                for coni in classes[name][key]: vertex_to_label[name][coni] = singular_renaming.get_assignment(key)
                singular_classes[name][singular_renaming.get_assignment(key)] = classes[name][key]
            else:
                non_singular_classes.append((key, name))

        max_singular_label = max_singular_label + len(singular_renaming.inv_assignment) - 1
        
        # TODO: more efficient way to remove conflicts with new_classes? 
        #       (could always add +len(classes) to right but that causes problems with int comparison)

        non_singular_renaming = Assignment(assignees=1, offset=max_singular_label)
        new_classes = {name: {} for name in names}
        
        for key, name in non_singular_classes:
            new_key = non_singular_renaming.get_assignment(key)

            for coni in classes[name][key]: vertex_to_label[name][coni] = new_key
            new_classes[name][new_key] = classes[name][key]
                
        return new_classes, max_singular_label
    
    label_to_vertex, max_singular_label = remove_lone_classes(initial_labels, max_singular_label)

    while True:

        renaming = Assignment(assignees=2, offset = max_singular_label)
        new_label_to_vertex = {name: {} for name in names}

        # TODO: make faster -- maps? -- parallelisation?
        #   not trivial due to get_assignment, need a lock on assignment...
        #   could assign each thread a modularity and always increase by that modularity...?

        for key, name in itertools.chain(*[itertools.product(label_to_vertex[name].keys(), [name]) for name in names]):
            for coni in label_to_vertex[name][key]:
                # need conversion to tuple for hashable
                hash_ = renaming.get_assignment(
                    key, 
                    tuple(sorted(map(vertex_to_label[name].__getitem__, vertex_to_adjacent[name][coni])))
                )
                new_label_to_vertex[name].setdefault(hash_, []).append(coni) 

        if all(map(lambda name : len(new_label_to_vertex[name]) == len(label_to_vertex[name]), names)): break

        label_to_vertex, max_singular_label = remove_lone_classes(new_label_to_vertex, max_singular_label)

    if return_inverse:
        for key, name in itertools.chain(*[itertools.product(label_to_vertex[name].keys(), [name]) for name in names]):
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
    """
    Wrapper for `iterated_label_propagation` as a constraint propagation function.
    
    All parameters not listed are dummy parameters used to fit the format.

    Parameters
    -----------
        in_pair: List[Tuple[str, Circuit]]
            Pair of circuit/name pairs for the input circuits
        classes: Dict[str, Dict[str, List[int]]]
            The constraint classes, for each circuitt name, and class hash the list of constraint indices that belong to that hash
        signal_info
            incoming knowledge about signal potential pairs
    """

    signal_to_coni = {
        name : _signal_data_from_cons_list(circ.constraints)
        for name, circ in in_pair
    }

    coni_to_adj_coni = {
        name: [
            set(filter(lambda x : x != coni, itertools.chain(*map(signal_to_coni[name].__getitem__, con.signals()))))
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





