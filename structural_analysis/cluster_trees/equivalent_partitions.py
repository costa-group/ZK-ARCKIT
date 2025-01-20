from typing import List, Dict
import itertools
import collections

from structural_analysis.cluster_trees.dag_from_clusters import DAGNode
from bij_encodings.preprocessing.iterated_adj_reclassing import iterated_label_propagation
from r1cs_scripts.circuit_representation import Circuit
from r1cs_scripts.constraint import Constraint
from utilities import getvars
from bij_encodings.assignment import Assignment
from testing_harness import quick_compare

def naive_equivalency_analysis(nodes: Dict[int, DAGNode], time_limit: int = 0) -> List[List[int]]:
    """
    iterates over the list of partition, definition sub-circuits for each partition and comparing with each class representative
        worst-case time: O(len(partition)^2
    """

    classes: List[List[int]] = []

    for node_id, node in nodes.items():

        # build sub-circuit
        sub_circ = node.get_subcircuit()

        equivalent = False
        for class_ in classes:

            # subcircuit only calculated once then stored in the class so this isn't wasting time
            repr_circ = nodes[class_[0]].get_subcircuit()
            equivalent = quick_compare(sub_circ, repr_circ, time_limit)

            if equivalent: 
                class_.append(node_id)
                break

        if not equivalent:
            classes.append([node_id])
    
    return classes

def easy_fingerprint_then_equivalence(nodes: Dict[int, DAGNode], time_limit: int = 0) -> List[List[int]]:
    """
    fingerprints ensuring all groups have the same number of constraints, signals, inputs/outputs
    """
    NKGroups = class_fingerprints(nodes)

    # then, for each class put it through naive_equivalency_analysis
    return list(itertools.chain(*map(lambda nodes_subset : naive_equivalency_analysis(nodes_subset, time_limit), 
                                 map(lambda keylist: {key: nodes[key] for key in keylist}, 
                                            NKGroups.values())
        )))

def structural_augmentation_equivalence(nodes: Dict[int, DAGNode], time_limit: int = 0) -> List[List[int]]:
    """
    Does iniital fingerprtinting based on internal information then augments this with structural information as requested then calling equivalence
    """

    initial_labels = class_fingerprints(nodes)
    structural_labels = class_iterated_label_passing(nodes, initial_labels)

    return list(itertools.chain(*map(lambda nodes_subset : naive_equivalency_analysis(nodes_subset, time_limit), 
                                 map(lambda keylist: {key: nodes[key] for key in keylist}, 
                                            structural_labels.values())
        )))

def class_fingerprints(nodes: Dict[int, DAGNode]) -> Dict[int, List[int]]:
    """
    Gives each node a fingerprints based on the number of constraints, signals, inputs/outputs
    """
    
    NKAssignment = Assignment(assignees=1)
    NKGroups = {}

    # pairs each node with the subcircuit hash data - then group the subcircuits by equivalent hash
    for node, key in zip(nodes.values(), 
        map(lambda circ: (circ.nConstraints, circ.nWires, circ.nPrvIn + circ.nPubIn, circ.nPubOut), 
        map(lambda node : node.get_subcircuit(), nodes.values()))):

        hash_ = NKAssignment.get_assignment(key)
        NKGroups.setdefault(hash_, []).append(node.id)

    return NKGroups

def class_iterated_label_passing(nodes: Dict[int, DAGNode], initial_labels: Dict[int, List[int]]) -> Dict[int, List[int]]:
    """
    augments the initial labels with structural information based on locality within the circuit
    """

    names = ["succ", "pred"]
    vertex_to_label = iterated_label_propagation(
        names = names,
        vertices = {name: nodes.keys() for name in names},
        vertex_to_adjacent = {
            "succ": {key  : nodes[key].successors for key in nodes.keys()},
            "pred": {key  : nodes[key].predecessors for key in nodes.keys()}
        },
        initial_labels = {
            name: {label : initial_labels[label] for label in initial_labels.keys()} for name in names
        },
        input_inverse = True,
        return_inverse = False
    )

    merge_labels = Assignment(assignees=2)

    final_labels = {}
    for key in nodes.keys():
        final_labels.setdefault(merge_labels.get_assignment(vertex_to_label['succ'][key], vertex_to_label['pred'][key]), []).append(key)

    return final_labels

def collective_equivalency_classes(circ: Circuit, nodes: List[DAGNode]) -> List[List[int]]:
    """
    does each step collectively hopefully reducing time

    can fingerprint all constraints, then create n-tuples for each fingerprint -- no guarantee of nonemptiness now
        - by transitivity of enclosure, we test equivalence only to first circuit, 
            -- doing that is still n^2 (* compare) in the worst case right?
        - we can do an all-to-all comparison for each class but that seems extremely expensive...
    
    Extending this is actually a lot of effort, since none of the information passing stuff works here 
        (in addition to refactoring all the various part of the comparison algorithm)

    If we assume that naive equivalency is n^2 in a group we can first fingerprint them to save some time.
    If we want to eventually call naive equivalency then we are gonna want to the fingerprint to be easy
    If we do constraint level fingerprinting we really ought to design an entirely new algorithm
    """
    pass #TODO
