from typing import Dict, List
from collections import deque
import itertools

from bij_encodings.assignment import Assignment
from structural_analysis.cluster_trees.dag_from_clusters import DAGNode
from utilities import dijkstras_shortest_weight, getvars, _is_nonlinear

def get_subclasses_by_nonlinear_shortest_path(nodes: Dict[int, DAGNode]) -> List[Dict[int, DAGNode]]:
    ## weighted shortest path where weight is number of nonlinears in target vertex.
    # doesn't seem super necessary rn

    circ = next(iter(nodes.values())).circ
    _is_input_signal = lambda sig : circ.nPubOut < sig <= circ.nPubOut + circ.nPubIn + circ.nPrvIn
    _is_output_signal = lambda sig : 0 < sig <= circ.nPubOut

    input_parts = list(filter(lambda node_id : any(map(_is_input_signal, nodes[node_id].input_signals)), nodes.keys()))
    output_parts = list(filter(lambda node_id : any(map(_is_output_signal, nodes[node_id].output_signals)), nodes.keys()))

    nodeid_to_signal = {nodeid : set(itertools.chain(*map(getvars, map(circ.constraints.__getitem__, nodes[nodeid].constraints)))) for nodeid in nodes.keys()}
    nodeid_to_num_nonlinear = {nodeid : sum(1 for _ in filter(_is_nonlinear, map(circ.constraints.__getitem__, nodes[nodeid].constraints))) for nodeid in nodes.keys()}

    signal_to_nodeid = {}
    deque(maxlen=0, 
          iterable = itertools.starmap(lambda nodeid, sig : signal_to_nodeid.setdefault(sig, []).append(nodeid),
                     itertools.chain(*map(lambda nodeid : itertools.product([nodeid], nodeid_to_signal[nodeid]), 
                     nodes.keys()
                    )))
    )

    adjacencies = {}
    deque(maxlen=0,
          iterable = itertools.starmap(lambda id, id2 : adjacencies.setdefault(id2, {}).__setitem__(id, nodeid_to_num_nonlinear[id]), 
                     itertools.chain(*map(lambda nodeid : itertools.product(
                        [nodeid], 
                        set(filter(lambda oid : oid != nodeid, itertools.chain(*map(lambda sig : signal_to_nodeid[sig], nodeid_to_signal[nodeid])))), 
                        ), 
                    nodes.keys()
                    ))
            )
    )

    shortest_weight_to_input = { node_id : dijkstras_shortest_weight(node_id, input_parts, adjacencies) for node_id in nodes.keys() }
    shortest_weight_to_output = { node_id : dijkstras_shortest_weight(node_id, output_parts, adjacencies) for node_id in nodes.keys() }

    node_hashing = Assignment(assignees=2)
    node_fingerprints = {node_id : node_hashing.get_assignment(shortest_weight_to_input[node_id], shortest_weight_to_output[node_id]) for node_id in nodes.keys()}
        
    fingerprint_to_DAGNode = {}
    
    deque(
        maxlen = 0,
        iterable = map(lambda node : fingerprint_to_DAGNode.setdefault(node_fingerprints[node.id], {}).__setitem__(node.id, node), nodes.values())
    )

    return fingerprint_to_DAGNode.values()