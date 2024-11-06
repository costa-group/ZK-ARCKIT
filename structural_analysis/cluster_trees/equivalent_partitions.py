from typing import List, Dict
import itertools

from structural_analysis.cluster_trees.dag_from_clusters import DAGNode
from r1cs_scripts.circuit_representation import Circuit
from r1cs_scripts.constraint import Constraint
from utilities import getvars
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

    


def collective_equivalency_classes(circ: Circuit, nodes: List[Dict]) -> List[List[int]]:
    """
    does each step collectively hopefully reducing time
    """


    pass # TODO
