from typing import Dict
import itertools
import collections

from r1cs_scripts.circuit_representation import Circuit
from structural_analysis.cluster_trees.dag_from_clusters import DAGNode
from utilities import DFS_reachability, getvars, _signal_data_from_cons_list, BFS_shortest_path

def merge_passthrough(circ: Circuit, nodes: Dict[int, DAGNode]) -> Dict[int, DAGNode]:

    # when a node has a signal as an input and output... we check successors for a viable merge where the signal is not an output
    #   TODO: add predecessor to nodes to allow for back-checking too.
    
    sig_to_coni = _signal_data_from_cons_list(circ.constraints)
    coni_to_node = [None for _ in range(circ.nConstraints)]

    # populates coni_to_node
    collections.deque(
        itertools.starmap(lambda coni, nodeid : coni_to_node.__setitem__(coni, nodeid),
        itertools.chain(*map(lambda node : itertools.product(node.constraints, [node.id]),
        nodes.values()))), maxlen=0
    )

    adjacencies = {key: node.successors for key, node in nodes.items()}

    extra_key = max(adjacencies.keys())+1
    adjacencies[extra_key] = None

    def check_viability(lkey: int, rkey: int) -> bool:
        adjacencies[extra_key] = set(itertools.chain(*map(lambda key : nodes[key].successors, [lkey, rkey]))).difference([lkey, rkey])
        return not DFS_reachability(extra_key, [lkey, rkey], adjacencies)

    merged_something = True
    while merged_something:

        merged_something = False

        # need list now because keys might be deleted. -- could fix other way if memory becomes a problem
        passthrough_nodes = list(filter(lambda key : any(map(lambda sig : sig in nodes[key].output_signals, nodes[key].input_signals)), nodes.keys()))

        for nkey in passthrough_nodes:

            # has already been merged
            if nkey not in nodes.keys(): continue

            node = nodes[nkey]
            sig_in_both = list(filter(lambda sig : sig in node.output_signals, node.input_signals))

            # we want a successor that has all sig_in_both as input and none as output.
            #   otherwise, choose viable that maximises the number of sig_in_both dealt with (and deal with next on next iteration)

            # TODO: generalise to any ordered value here for successor.
            # TODO: maybe add option to merge with predecessors?
            # check outputs of successors
            successor_index_to_num_sig_dealt_with = [
                sum(map(lambda sig : sig in nodes[key].input_signals and sig not in nodes[key].output_signals, sig_in_both)) 
                for key in node.successors
            ]

            # check viability of successors
                # no path from succ to nkey
                # -- maybe cache this since it's the hardest information (can cache shortest path..)
            successor_is_viable = [
                False if successor_index_to_num_sig_dealt_with[i] == 0 else check_viability(nkey, key)
                for i, key in enumerate(node.successors)
            ]

            # choose a viable successor
            #   if no viable successor do nothing (one may appear layer)
            to_merge = sorted(filter(successor_is_viable.__getitem__, range(len(node.successors))), 
                            key = successor_index_to_num_sig_dealt_with.__getitem__, reverse = True)
            
            if len(to_merge) == 0: continue
            merged_something = True

            merge_nodes(nkey, node.successors[to_merge[0]], nodes, sig_to_coni, coni_to_node, adjacencies)

    return nodes

    # do we still only care about nonlinear constraints ?? presumably but I feel like this wouldn't hurt linear collapse

def merge_only_nonlinear():
    pass 

def merge_nodes(lkey: int, rkey: int, nodes: Dict[int, DAGNode], sig_to_coni, coni_to_node, adjacencies) -> None:
    """
    mutates the nodes list to merge lkey and rkey
    lkey is assumed to be the parent of rkey, and they are assumed to be viable (i.e. not introduce any cycle)
    """

    assert any(map(lambda sig : sig in nodes[rkey].input_signals, nodes[lkey].output_signals)), "lkey is not successor of rkey"

    newnode = DAGNode(
        nodes[lkey].circ,
        lkey,
        nodes[lkey].constraints + nodes[rkey].constraints,
        set([]), set([])
    )

    newnode.successors   = list(set(itertools.chain(*map(lambda key : nodes[key].successors,   [lkey, rkey]))).difference([lkey, rkey]))
    newnode.predecessors = list(set(itertools.chain(*map(lambda key : nodes[key].predecessors, [lkey, rkey]))).difference([lkey, rkey]))

    # input signals, any signals that form an edge to any constraint in a predecessor
    #   likewise for outputs but with successors
    node_signals = set(itertools.chain(*map(lambda coni : getvars(newnode.circ.constraints[coni]), newnode.constraints)))
    signals_is_incident_with_node_set = lambda sig, node_set: any(map(lambda coni : coni_to_node[coni] in node_set, sig_to_coni[sig]))
    newnode.input_signals = set(filter(lambda sig : signals_is_incident_with_node_set(sig, newnode.predecessors), node_signals))
    newnode.output_signals = set(filter(lambda sig : signals_is_incident_with_node_set(sig, newnode.successors), node_signals))

    nodes[lkey] = newnode
    adjacencies[lkey] = newnode.successors

    # fixes the succesors/predecessors of all the other nodes -- also updates adjacencies
    funcs = [lambda key : nodes[key].successors, lambda key : nodes[key].predecessors]
    for i in range(2):
        for key in funcs[1-i](rkey):
            if rkey in funcs[i](key):
                if lkey in funcs[i](key): del funcs[i](key)[funcs[i](key).index(rkey)]
                else: funcs[i](key)[funcs[i](key).index(rkey)] = lkey
    
    # fixes coni_to_node
    collections.deque(map(lambda coni : coni_to_node.__setitem__(coni, lkey) , nodes[rkey].constraints), maxlen=0)

    # removes entries for rkey dictionaries
    del adjacencies[rkey]
    del nodes[rkey]