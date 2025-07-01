

## steps
    # 1. get fingerprints for norms using v2 stuff
    # 2. use this to classify the subcircuits
    # 3. keep fingerprint information to pass to comparison_v2

    # TODO: alter testing_harness without all the baggage from not using v2s
from typing import List, Dict, Tuple
import itertools
from collections import deque

from structural_analysis.cluster_trees.dag_from_clusters import DAGNode
from circuits_and_constraints.abstract_circuit import Circuit
from utilities.assignment import Assignment
from comparison_v2.fingerprinting_v2 import back_and_forth_fingerprinting
from utilities.utilities import _signal_data_from_cons_list

from structural_analysis.cluster_trees.equivalent_partitions import naive_equivalency_analysis, class_iterated_label_passing

def subcircuit_fingerprinting_equivalency(nodes: Dict[int, DAGNode], time_limit: int = 0):
    
    subcircuit_groups, fingerprints_to_normi, fingerprints_to_signals = fingerprint_subcircuits(nodes)

    equivalent = []
    mappings = []

    deque(maxlen = 0,
          iterable = itertools.starmap(lambda equiv, mapp : [equivalent.extend(equiv), mappings.extend(mapp)],
                     map(lambda nodes_subset : naive_equivalency_analysis(nodes_subset, time_limit, fingerprints_to_normi = fingerprints_to_normi, fingerprints_to_signals = fingerprints_to_signals),
                     map(lambda keylist: {key: nodes[key] for key in keylist},
                     subcircuit_groups.values()              
         )))
    )

    return equivalent, mappings

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

    equivalent, mappings = propagate_subcirctuit_labels(nodes, equivalent, mappings)

    return equivalent, mappings

def subcircuit_fingerprinting_equivalency_and_structural_augmentation_equivalency(nodes: Dict[int, DAGNode], time_limit: int = 0):

    local_equivalent, local_mappings = subcircuit_fingerprinting_equivalency(nodes, time_limit)
    full_equivalent, full_mappings = propagate_subcirctuit_labels(nodes, local_equivalent, local_mappings)
    
    return local_equivalent, local_mappings, full_equivalent, full_mappings

def fingerprint_subcircuits(nodes: Dict[int, DAGNode]) -> Dict[int, List[int]]:

    in_pair: List[Tuple[str, Circuit]] = [(node.id, node.get_subcircuit()) for node in nodes.values()]
    deque(maxlen = 0,
          iterable = (circ.normalise_constraints() for name, circ in in_pair)
    )

    fingerprints_to_normi = { id: { 1 : list(range(len(circ.normalised_constraints)))} for id, circ in in_pair }
    fingerprints_to_signals = {name : {
                                        1 : list(circ.get_output_signals()), 
                                        2 : list(circ.get_input_signals()), 
                                        3 : list(filter(lambda sig : not circ.signal_is_input(sig) and not circ.signal_is_output(sig), circ.get_signals()))} 
                                    for name, circ in in_pair}
    signal_to_normi = {name: _signal_data_from_cons_list(circ.normalised_constraints) for name, circ in in_pair}

    fingerprints_to_normi, fingerprints_to_signals = back_and_forth_fingerprinting(list(nodes.keys()), in_pair, signal_to_normi, fingerprints_to_normi, fingerprints_to_signals)

    ## COMBINE norm fingerprints into 
    subcircuit_assignment = Assignment(assignees=1)
    fingerprints_to_subcircuits = {}


    for node  in nodes.values():

        key = subcircuit_assignment.get_assignment( tuple(sorted(itertools.starmap( lambda key, val : (key, len(val)),  fingerprints_to_normi[node.id].items()))) )
        fingerprints_to_subcircuits.setdefault( key, [] ).append(node.id)

    return fingerprints_to_subcircuits, fingerprints_to_normi, fingerprints_to_signals

def propagate_subcirctuit_labels(nodes: Dict[int, DAGNode], equivalent: List[List[int]], mappings = List[List[List[int]]]):
    
    ## pass to propagator
    label_to_index = class_iterated_label_passing(nodes, { i : class_ for i, class_ in enumerate(equivalent)})

    ## detect and fix mappings
    index_to_label = {}
    deque(
        iterable = itertools.starmap(lambda label, index : index_to_label.__setitem__(index, label), 
                   itertools.chain(*itertools.starmap(lambda label, indices: itertools.product([label], indices), label_to_index.items()))),
        maxlen=0
    )

    ## Could optimise assuming stability - but seems dangerous
    new_mappings = {}

    for label, nodis in enumerate(equivalent):

        reference_node = nodis[0]
        newlabels = set(map(index_to_label.__getitem__, nodis))
        
        nodi_to_index = {}
        deque(
            iterable = itertools.starmap(lambda i, nodi : nodi_to_index.__setitem__(nodi, i), enumerate(nodis)),
            maxlen=0
        )


        for newlabel in newlabels:
            
            nl_nodis = label_to_index[newlabel]

            if reference_node in nl_nodis:
                
                ## make reference the first vertex to
                new_ref_index = nl_nodis.index(reference_node)
                nl_nodis[0], nl_nodis[new_ref_index] = nl_nodis[new_ref_index], nl_nodis[0]

                new_mappings[newlabel] = [
                    mappings[label][nodi_to_index[onodi]-1]
                    for onodi in nl_nodis[1:]
                ]

            else:
                ## decide first is new ref index
                new_ref_map = mappings[label][nodi_to_index[nl_nodis[0]]-1]

                new_mappings[newlabel] = [
                    list(map(lambda p : p[1], sorted(zip(new_ref_map, mappings[label][nodi_to_index[onodi] - 1]))))
                    for onodi in nl_nodis[1:]
                ]

    return list(label_to_index.values()), [new_mappings[key] for key in label_to_index.keys()]
