from typing import List, Dict
import itertools
from collections import deque

from utilities.assignment import Assignment
from structural_analysis.cluster_trees.dag_from_clusters import DAGNode
from maximal_equivalence.iterated_fingerprints_with_pausing import coefficient_only_fingerprinting
from comparison_v2.fingerprinting_v2 import back_and_forth_fingerprinting
from normalisation import r1cs_norm
from utilities.utilities import _is_nonlinear, _signal_data_from_cons_list

def get_subclasses_by_nonlinears(nodes: Dict[int, DAGNode]) -> List[Dict[int, DAGNode]]:
    # TODO: make it so that it accounts for intralinear passes

    names = nodes.keys()
    circ = next(iter(nodes.values())).circ
    
    fingerprints = coefficient_only_fingerprinting(
        names,
        { node.id : list(filter(_is_nonlinear, map(circ.constraints.__getitem__, node.constraints))) for node in nodes.values() }
    )

    class_fingerprints = Assignment(assignees=1)
    fingerprints = { node_id : class_fingerprints.get_assignment(tuple(sorted(itertools.starmap(lambda fp, conis : (fp, len(conis)), fingerprints[node_id].items())))) for node_id in names }
    
    fingerprint_to_DAGNode = {}
    
    deque(
        maxlen = 0,
        iterable = map(lambda node : fingerprint_to_DAGNode.setdefault(fingerprints[node.id], {}).__setitem__(node.id, node), nodes.values())
    )

    return fingerprint_to_DAGNode.values()

def get_subclasses_by_nonlinear_relation(nodes: Dict[int, DAGNode]) -> List[Dict[int, DAGNode]]:

    names = nodes.keys()

    circ = next(iter(nodes.values())).circ

    normalised_constraints = { name : list(filter(_is_nonlinear, map(node.circ.constraints.__getitem__, node.constraints))) for name, node in nodes.items() }
    fingerprints_to_normi = coefficient_only_fingerprinting(names, normalised_constraints)

    signal_to_normi = {name: _signal_data_from_cons_list(normalised_constraints[name]) for name in names}
    signal_sets = {name: signal_to_normi[name].keys() for name in names}
    fingerprints_to_signals = {name: { 0: [0], 1 : list(signal_sets[name])} for name in names}
    fingerprints_to_normi, _ = back_and_forth_fingerprinting(names, itertools.product(names, [circ]), normalised_constraints, signal_to_normi, fingerprints_to_normi, fingerprints_to_signals, signal_sets = signal_sets, initial_mode=False)


    node_hashing = Assignment(assignees=1)
    node_fingerprints = {node_id : node_hashing.get_assignment(tuple(sorted(itertools.starmap(lambda fp, normis : (fp, len(normis)), fingerprints_to_normi[node_id].items())))) for node_id in names}
        
    fingerprint_to_DAGNode = {}
    
    deque(
        maxlen = 0,
        iterable = map(lambda node : fingerprint_to_DAGNode.setdefault(node_fingerprints[node.id], {}).__setitem__(node.id, node), nodes.values())
    )

    return fingerprint_to_DAGNode.values()
