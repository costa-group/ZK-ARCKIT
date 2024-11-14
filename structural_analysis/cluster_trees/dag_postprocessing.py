from typing import Dict, Callable, Iterable
import itertools
import collections

from r1cs_scripts.circuit_representation import Circuit
from structural_analysis.cluster_trees.dag_from_clusters import DAGNode
from utilities import DFS_reachability, getvars, _signal_data_from_cons_list, BFS_shortest_path

def merge_under_property(circ: Circuit, nodes: Dict[int, DAGNode], 
    property : Callable[[DAGNode], bool], 
    child_property: Callable[[DAGNode, DAGNode], int],
    parent_property: Callable[[DAGNode, DAGNode], int]) -> Dict[int, DAGNode]:

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
        passthrough_nodes = list(filter(lambda key : property(nodes[key]), nodes.keys()))

        for nkey in passthrough_nodes:

            # has already been merged
            if nkey not in nodes.keys(): continue

            # we want a successor that has all sig_in_both as input and none as output.
            #   otherwise, choose viable that maximises the number of sig_in_both dealt with (and deal with next on next iteration)

            # TODO: generalise to any ordered value here for successor.
            # TODO: maybe add option to merge with predecessors?
            # check outputs of successors

            index_to_nkeys = nodes[nkey].predecessors + nodes[nkey].successors
            adjacent_to_property = [
                parent_property(nodes[key], nodes[nkey]) for key in nodes[nkey].predecessors ] + [
                child_property(nodes[nkey], nodes[key]) for key in nodes[nkey].successors ]

            # check viability of successors
                # no path from succ to nkey
                # -- maybe cache this since it's the hardest information (can cache shortest path..)
            adjacent_is_viable = [
                adjacent_to_property[i] > 0 and check_viability(nkey, key)
                for i, key in enumerate(index_to_nkeys)
            ]

            # choose a viable successor
            #   if no viable successor do nothing (one may appear layer)
            to_merge = sorted(filter(adjacent_is_viable.__getitem__, range(len(index_to_nkeys))), 
                            key = adjacent_to_property.__getitem__, reverse = True)
            
            if len(to_merge) == 0: continue

            index = to_merge[0]
            is_predecessor = index < len(nodes[nkey].predecessors)
            okey = index_to_nkeys[index]

            merged_something = True

            merge_nodes(*((okey, nkey) if is_predecessor else (nkey, okey)), nodes, sig_to_coni, coni_to_node, adjacencies)

    return nodes

    # do we still only care about nonlinear constraints ?? presumably but I feel like this wouldn't hurt linear collapse

def merge_passthrough(circ: Circuit, nodes: Dict[int, DAGNode]) -> Dict[int, DAGNode]:

    has_passthrough_signals = lambda node : any(map(lambda sig : sig in node.output_signals, node.input_signals))
    num_passthrough_signals_caught_by_child = lambda parent, child : sum(
        map(lambda sig : sig in child.input_signals and sig not in child.output_signals,
        filter(lambda sig : sig in parent.output_signals, parent.input_signals)
    ))
    num_passthrough_signals_caught_by_parent = lambda parent, child : sum(
        map(lambda sig : sig in parent.output_signals and sig not in parent.input_signals,
        filter(lambda sig : sig in child.output_signals, child.input_signals)
    ))

    return merge_under_property(circ, nodes, has_passthrough_signals, num_passthrough_signals_caught_by_child, num_passthrough_signals_caught_by_parent)

def merge_only_nonlinear(circ: Circuit, nodes: Dict[int, DAGNode]) -> Dict[int, DAGNode]:
    
    constraint_is_nonlinear = lambda con : len(con.A) > 0 and len(con.B) > 0
    is_only_nonlinear = lambda node : all(map(constraint_is_nonlinear, map(circ.constraints.__getitem__, node.constraints)))
    child_isnt_nonlinear = lambda _, child : not is_only_nonlinear(child)
    parent_isnt_nonliner = lambda parent, _: not is_only_nonlinear(parent)

    # adjacent checks redundant for nonlinear_attract, not for louvain
    return merge_under_property(circ, nodes, is_only_nonlinear, child_isnt_nonlinear, parent_isnt_nonliner)

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