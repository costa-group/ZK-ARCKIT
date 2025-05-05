

## steps
    # 1. get fingerprints for norms using v2 stuff
    # 2. use this to classify the subcircuits
    # 3. keep fingerprint information to pass to comparison_v2

    # TODO: alter testing_harness without all the baggage from not using v2s
from typing import List, Dict, Tuple
import itertools
from collections import deque

from structural_analysis.cluster_trees.dag_from_clusters import DAGNode
from r1cs_scripts.circuit_representation import Circuit
from utilities.assignment import Assignment
from normalisation import r1cs_norm
from comparison_v2.fingerprinting_v2 import back_and_forth_fingerprinting
from utilities.utilities import _signal_data_from_cons_list, count_ints

from structural_analysis.cluster_trees.equivalent_partitions import naive_equivalency_analysis, class_iterated_label_passing

def subcircuit_fingerprinting_equivalency(nodes: Dict[int, DAGNode], time_limit: int = 0):
    
    subcircuit_groups, fingerprints_to_normi, fingerprints_to_signals = fingerprint_subcircuits(nodes)

    return list(itertools.chain(*map(lambda nodes_subset : naive_equivalency_analysis(nodes_subset, time_limit, fingerprints_to_normi = fingerprints_to_normi, fingerprints_to_signals = fingerprints_to_signals), 
                                 map(lambda keylist: {key: nodes[key] for key in keylist}, 
                                            subcircuit_groups.values())
        )))

def subcircuit_fingerprint_with_structural_augmentation_equivalency(nodes: Dict[int, DAGNode], time_limit: int = 0):
    
    subcircuit_groups, fingerprints_to_normi, fingerprints_to_signals = fingerprint_subcircuits(nodes)
    structural_labels = class_iterated_label_passing(nodes, subcircuit_groups)

    equivalent = []
    mappings = []

    deque(maxlen = 0,
          iterable = itertools.starmap(lambda equiv, mapp : [equivalent.extend(equiv), mappings.extend(mapp)],
                     map(lambda nodes_subset : naive_equivalency_analysis(nodes_subset, time_limit, fingerprints_to_normi = fingerprints_to_normi, fingerprints_to_signals = fingerprints_to_signals),
                     map(lambda keylist: {key: nodes[key] for key in keylist},
                     structural_labels.values()              
         )))
    )

    return equivalent, mappings

def fingerprint_subcircuits(nodes: Dict[int, DAGNode]) -> Dict[int, List[int]]:

    in_pair: List[Tuple[str, Circuit]] = [(node.id, node.get_subcircuit()) for node in nodes.values()]
    normalised_constraints = { node.id : list(itertools.chain(*map(r1cs_norm, node.get_subcircuit().constraints))) for node in nodes.values() }
    fingerprints_to_normi = { node.id: { 1 : list(range(len(normalised_constraints[node.id])))} for node in nodes.values() }
    fingerprints_to_signals = {name : {0 : [0], 
                                            1 : list(range(1,circ.nPubOut+1)), 
                                            2 : list(range(circ.nPubOut+1, circ.nPubOut + circ.nPrvIn + circ.nPubIn + 1)), 
                                            3 : list(range(circ.nPubOut + circ.nPrvIn + circ.nPubIn + 1, circ.nWires))} 
                                    for name, circ in in_pair}
    signal_to_normi = {name: _signal_data_from_cons_list(normalised_constraints[name]) for name in nodes.keys()}

    fingerprints_to_normi, fingerprints_to_signals = back_and_forth_fingerprinting(nodes.keys(), in_pair, normalised_constraints, signal_to_normi, fingerprints_to_normi, fingerprints_to_signals)

    ## COMBINE norm fingerprints into 
    subcircuit_assignment = Assignment(assignees=1)
    fingerprints_to_subcircuits = {}


    for node  in nodes.values():

        key = subcircuit_assignment.get_assignment( tuple(sorted(itertools.starmap( lambda key, val : (key, len(val)),  fingerprints_to_normi[node.id].items()))) )
        fingerprints_to_subcircuits.setdefault( key, [] ).append(node.id)

    return fingerprints_to_subcircuits, fingerprints_to_normi, fingerprints_to_signals


