

## steps
    # 1. get fingerprints for norms using v2 stuff
    # 2. use this to classify the subcircuits
    # 3. keep fingerprint information to pass to comparison_v2

    # TODO: alter testing_harness without all the baggage from not using v2s
from typing import List, Dict, Tuple
import itertools

from structural_analysis.cluster_trees.dag_from_clusters import DAGNode
from r1cs_scripts.circuit_representation import Circuit
from bij_encodings.assignment import Assignment
from normalisation import r1cs_norm
from comparison_v2.fingerprinting_v2 import back_and_forth_fingerprinting
from utilities import _signal_data_from_cons_list, count_ints

def subcircuit_fingerprinting_equivalency():
    pass

def subcircuit_fingerprint_with_structural_augmentation_equivalency():
    pass


def fingerprint_subcircuits(nodes: Dict[int, DAGNode]) -> List[int]:

    in_pair: List[Tuple[str, Circuit]] = [(node.id, node.get_subcircuit()) for node in nodes.values()]
    normalised_constraints = { node.id : itertools.chain(*map(r1cs_norm, node.get_subcircuit().constraints)) for node in nodes.values() }
    fingerprints_to_normi = { node.id: { 1 : list(range(len(normalised_constraints[node.id])))} for node in nodes.values() }
    fingerprints_to_signals = {name : {0 : [0], 
                                            1 : list(range(1,circ.nPubOut+1)), 
                                            2 : list(range(circ.nPubOut+1, circ.nPubOut + circ.nPrvIn + circ.nPubIn + 1)), 
                                            3 : list(range(circ.nPubOut + circ.nPrvIn + circ.nPubIn + 1, circ.nWires))} 
                                    for name, circ in in_pair}
    signal_to_normi = {name: _signal_data_from_cons_list(normalised_constraints[name]) for name in nodes.keys()}

    fingerprints_to_normi, fingerprints_to_signals = back_and_forth_fingerprinting(nodes.keys(), in_pair, normalised_constraints, signal_to_normi, fingerprints_to_normi, fingerprints_to_signals)

    ## COMBINE norm fingerprints into 