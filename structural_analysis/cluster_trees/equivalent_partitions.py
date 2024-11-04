from typing import List, Dict
import itertools

from r1cs_scripts.circuit_representation import Circuit
from r1cs_scripts.constraint import Constraint
from utilities import getvars
from testing_harness import quick_compare

def get_subcircuit(circ: Circuit, node: Dict) -> Circuit:
    """
    The subcircuit has new constraint instances (due to how the signal names are assumed)
    """

    sub_circ = Circuit()

    ordered_signals = list(itertools.chain(
        [0],
        node["output_signals"].difference(node["input_signals"]),
        node["input_signals"],
        set(itertools.chain(*map(getvars, map(circ.constraints.__getitem__, node["constraints"])))).difference(itertools.chain(node["output_signals"], node["input_signals"]))
    ))

    sig_mapping = dict(zip(
        ordered_signals,
        range(len(ordered_signals))
    ))

    sub_circ.constraints = list(map(lambda con : 
        Constraint(
            *[{sig_mapping[sig]: val for sig, val in dict_.items()} for dict_ in [con.A, con.B, con.C]],
            con.p
        ),
        map(circ.constraints.__getitem__, node["constraints"])))
    
    sub_circ.update_header(
        circ.field_size,
        circ.prime_number,
        len(sig_mapping),
        len(node["output_signals"].difference(node["input_signals"])),
        len(node["input_signals"]),
        0, # prv in doesn't matter
        None,
        len(node["constraints"])
    )

    return sub_circ


def naive_equivalency_analysis(circ: Circuit, nodes: List[Dict], time_limit: int = 0) -> List[List[int]]:
    """
    iterates over the list of partition, definition sub-circuits for each partition and comparing with each class representative
        worst-case time: O(len(partition)^2
    """

    classes: List[List[int]] = []
    class_representatives: List[Circuit] = []

    for node in nodes:

        # build sub-circuit
        sub_circ = get_subcircuit(circ, node)

        equivalent = False
        for class_, repr_circ in zip(classes, class_representatives):

            equivalent = quick_compare(sub_circ, repr_circ, time_limit)

            if equivalent: 
                class_.append(node["node_id"])
                break

        if not equivalent:
            classes.append([node["node_id"]])
            class_representatives.append(sub_circ)
    
    return classes

    


def collective_equivalency_classes(circ: Circuit, nodes: List[Dict]) -> List[List[int]]:
    """
    does each step collectively hopefully reducing time
    """


    pass # TODO
