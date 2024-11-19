from typing import Dict, Callable, Iterable, List
import itertools
import collections

from r1cs_scripts.circuit_representation import Circuit
from structural_analysis.cluster_trees.dag_from_clusters import DAGNode
from utilities import DFS_reachability, getvars, _signal_data_from_cons_list, BFS_shortest_path

def merge_under_property(circ: Circuit, nodes: Dict[int, DAGNode], 
    property : Callable[[DAGNode], bool], 
    child_property: Callable[[DAGNode, DAGNode], int],
    parent_property: Callable[[DAGNode, DAGNode], int]) -> Dict[int, DAGNode]:
    """
    Merges nodes that meet input properties
    
    Nodes that meet property 1 are listed as two merge, a successor or predecessor is chosen to be merged with
        based on suitability.
    An adjacent node is `suitable' only if it has adjacent_property > 0 and does not cause a 
    
    parameters:
        circ: Circuit 
            The circuit being worked on -- NOTE: could remove and take circ from nodes but don't for consistency
        nodes: Dict(int, DAGNode)
            The collection of nodes that cluster the circuit
        property: DAGNode -> Bool
            A function used to filter the nodes that require merging.
        child_property: (DAGNode, DAGNode) -> Ord
            A function used in determining suitability of successor nodes
        parent_property: (DAGNode, DAGNode) -> Ord
            A function used in determining suitability of predecessor nodes
        
    return_value:
        A Dict(int, DAGNode) of the nodes after merging.
        Note that this function mutates the input nodes dictionary
    """

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

            # check outputs of adjacent nodes

            index_to_nkeys = nodes[nkey].predecessors + nodes[nkey].successors
            adjacent_to_property = [
                parent_property(nodes[key], nodes[nkey]) for key in nodes[nkey].predecessors ] + [
                child_property(nodes[nkey], nodes[key]) for key in nodes[nkey].successors ]

            # check viability of adjacent nodes
                # no path from key (adj) to nkey
                # -- TODO: maybe cache this since it's the hardest information (can cache shortest path..?)
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
    """
    An instance of merge_under_property mergins nodes that have signals in the input and output.

    filter property : has at least 1 signals that is in the inputs and outputs of the node (i.e. passthrough signals)
    adj_property : number of passthrough signals that are `caught' by an adjacent node
        (i.e. for successors, number of passthrough signals in the input signals but not the output signals of the successor) 
    
    parameters:
        circ: Circuit 
            The circuit being worked on -- NOTE: could remove and take circ from nodes but don't for consistency
        nodes: Dict(int, DAGNode)
            The collection of nodes that cluster the circuit
    """

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
    """
    An instance of merge_under_property mergins nodes that have signals in the input and output.

    filter property : has only nonlinear constraints in the node
    adj_property : does not have only nonlinear constraints in the node

    parameters:
        circ: Circuit 
            The circuit being worked on -- NOTE: could remove and take circ from nodes but don't for consistency
        nodes: Dict(int, DAGNode)
            The collection of nodes that cluster the circuit
    """
    
    constraint_is_nonlinear = lambda con : len(con.A) > 0 and len(con.B) > 0
    is_only_nonlinear = lambda node : all(map(constraint_is_nonlinear, map(circ.constraints.__getitem__, node.constraints)))
    child_isnt_nonlinear = lambda _, child : not is_only_nonlinear(child)
    parent_isnt_nonliner = lambda parent, _: not is_only_nonlinear(parent)

    # adjacent checks redundant for nonlinear_attract, not for louvain
    return merge_under_property(circ, nodes, is_only_nonlinear, child_isnt_nonlinear, parent_isnt_nonliner)

def merge_nodes(lkey: int, rkey: int, nodes: Dict[int, DAGNode], 
        sig_to_coni: Dict[int, List[int]], coni_to_node: List[int], adjacencies: Dict[int, List[int]]) -> None:
    """
    Helper function for merge_under_property

    Given two nodes, indexed `lkey' and `rkey' this creates a new node merging lkey and rkey 
        then mutates the various dictionaries lists to update them
    This function does not enforce any prerequitites on the nodes we assume
        that lkey is the parent of rkey, and that no cycle is created when these are merged.

    parameters:
        lkey: Int
            index of the parent node in nodes
        rkey: Int
            index of the child node in nodes
        nodes: Dict(int, DAGNode)
            The collection of nodes that cluster the circuit
        sig_to_coni: Dict(int, List[int])
            Maps each signal in the circuit to the index of the constraints it appears in
        coni_to_node: List[int]
            Maps each constraint index in the circuit to the index of the node it appears in
        adjacencies: Dict(int, List[int])
            Maps each node index to the successor nodes -- used in cycle detection in parent function
        
    returns:
        None
        nodes, coni_to_node, adjacencies are all mutated to update with the new data
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