from typing import List, Dict
import itertools

from structural_analysis.cluster_trees.dag_from_clusters import DAGNode
from r1cs_scripts.circuit_representation import Circuit
from r1cs_scripts.constraint import Constraint
from utilities import getvars
from testing_harness import quick_compare

def naive_equivalency_analysis(nodes: List[DAGNode], time_limit: int = 0) -> List[List[int]]:
    """
    iterates over the list of partition, definition sub-circuits for each partition and comparing with each class representative
        worst-case time: O(len(partition)^2
    """

    classes: List[List[int]] = []
    class_representatives: List[Circuit] = []

    for node in nodes:

        # build sub-circuit
        sub_circ = node.get_subcircuit()

        equivalent = False
        for class_, repr_circ in zip(classes, class_representatives):

            equivalent = quick_compare(sub_circ, repr_circ, time_limit)

            if equivalent: 
                class_.append(node.id)
                break

        if not equivalent:
            classes.append([node.id])
            class_representatives.append(sub_circ)
    
    return classes

    


def collective_equivalency_classes(circ: Circuit, nodes: List[Dict]) -> List[List[int]]:
    """
    does each step collectively hopefully reducing time
    """


    pass # TODO
