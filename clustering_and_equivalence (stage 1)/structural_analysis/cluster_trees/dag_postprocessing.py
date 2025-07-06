"""
Functions for postprocessing the nodes
"""

from typing import Dict, Callable, Iterable, List
import itertools
import collections

from r1cs_scripts.circuit_representation import Circuit
from structural_analysis.cluster_trees.dag_from_clusters import DAGNode
from utilities.utilities import DFS_reachability, _signal_data_from_cons_list

def merge_under_property(circ: Circuit, nodes: Dict[int, DAGNode], 
    property : Callable[[DAGNode], bool], 
    child_property: Callable[[DAGNode, DAGNode], int],
    parent_property: Callable[[DAGNode, DAGNode], int]) -> Dict[int, DAGNode]:
    """
    Merges nodes that meet input properties
    
    Nodes that meet property 1 are listed as two merge, a successor or predecessor is chosen to be merged with
    based on suitability. An adjacent node is `suitable' only if it has adjacent_property > 0 and does not cause a cycle.
    
    Parameters
    ----------
        circ: Circuit 
            The circuit being worked on -- NOTE: could remove and take circ from nodes but don't for consistency
        nodes: Dict[int, DAGNode]
            The collection of nodes that cluster the circuit
        property: DAGNode -> Bool
            A function used to filter the nodes that require merging.
        child_property: (DAGNode, DAGNode) -> Ord
            A function used in determining suitability of successor nodes
        parent_property: (DAGNode, DAGNode) -> Ord
            A function used in determining suitability of predecessor nodes
        
    Returns
    ----------
    Dict[int, DAGNode] 
        Nodes list after merging.
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
    
    to_merge_queue = collections.deque(filter(lambda key : property(nodes[key]), nodes.keys()))
    first_unmerged = None

    while len(to_merge_queue) > 0:

        nkey = to_merge_queue.popleft()

        ## used to stop infinite looping when no viable merges available
        if nkey == first_unmerged: break

        ## successor node merged with parent might not exist anymore
        if nkey not in nodes.keys(): continue

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
        
        ## no viable to match
        if len(to_merge) == 0: 
            if first_unmerged is None: first_unmerged = nkey
            to_merge_queue.append(nkey)
            continue

        first_unmerged = None

        index = to_merge[0]
        is_predecessor = index < len(nodes[nkey].predecessors)
        okey = index_to_nkeys[index]

        parent_key, child_key = (okey, nkey) if is_predecessor else (nkey, okey)

        merge_nodes(parent_key, child_key, nodes, sig_to_coni, coni_to_node, adjacencies)

        if property(nodes[parent_key]): to_merge_queue.append(parent_key)

    return nodes

def merge_passthrough(circ: Circuit, nodes: Dict[int, DAGNode]) -> Dict[int, DAGNode]:
    """
    An instance of :py:func:`merge_under_property` merges nodes that have signals in the input and output.

    filter property : has at least 1 signals that is in the inputs and outputs of the node (i.e. passthrough signals)
    adj_property : number of passthrough signals that are `caught' by an adjacent node
        (i.e. for successors, number of passthrough signals in the input signals but not the output signals of the successor) 
    
    Parameters
    ----------
        circ: Circuit 
            The circuit being worked on -- NOTE: could remove and take circ from nodes but don't for consistency
        nodes: Dict(int, DAGNode)
            The collection of nodes that cluster the circuit
    
    Returns
    ----------
    Dict[int, DAGNode] 
        Nodes list after merging.
        Note that this function mutates the input nodes dictionary
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
    An instance of :py:func:`merge_under_property` merges nodes that have signals in the input and output.

    filter property : has only nonlinear constraints in the node
    adj_property : does not have only nonlinear constraints in the node

    Parameters
    ----------
        circ: Circuit 
            The circuit being worked on -- NOTE: could remove and take circ from nodes but don't for consistency
        nodes: Dict(int, DAGNode)
            The collection of nodes that cluster the circuit
    
    Returns
    ----------
    Dict[int, DAGNode] 
        Nodes list after merging.
        Note that this function mutates the input nodes dictionary
    """
    
    constraint_is_nonlinear = lambda con : con.is_nonlinear()
    is_only_nonlinear = lambda node : all(map(constraint_is_nonlinear, map(circ.constraints.__getitem__, node.constraints)))
    child_isnt_nonlinear = lambda _, child : not is_only_nonlinear(child)
    parent_isnt_nonliner = lambda parent, _: not is_only_nonlinear(parent)

    # adjacent checks redundant for nonlinear_attract, not for louvain
    return merge_under_property(circ, nodes, is_only_nonlinear, child_isnt_nonlinear, parent_isnt_nonliner)

def merge_single_linear(circ: Circuit, nodes: Dict[int, DAGNode], favour_down: bool = True) -> Dict[int, DAGNode]:
    """
    An instance of :py:func:`merge_under_property` merges nodes that have signals in the input and output.

    filter property : node is a single linear
    adj_property : number of shared signals

    Parameters
    ----------
        circ: Circuit 
            The circuit being worked on -- NOTE: could remove and take circ from nodes but don't for consistency
        nodes: Dict(int, DAGNode)
            The collection of nodes that cluster the circuit
    
    Returns
    ----------
    Dict[int, DAGNode] 
        Nodes list after merging.
        Note that this function mutates the input nodes dictionary
    """
    is_single_linear : Callable[[DAGNode], bool]= lambda node : len(node.constraints) == 1 and not circ.constraints[next(iter(node.constraints))].is_nonlinear()

    # note that this prioritises children over parents -- this is a heuristic given by Albert
    child_attraction : Callable[[DAGNode, DAGNode], int] = lambda node, child : (len(node.input_signals) if favour_down else 0) + len(node.output_signals.intersection(child.input_signals))
    parent_attraction : Callable[[DAGNode, DAGNode], int] = lambda parent, node : (0 if favour_down else len(node.output_signals)) + len(node.input_signals.intersection(parent.output_signals))

    return merge_under_property(circ, nodes, is_single_linear, child_attraction, parent_attraction)

def merge_unsafe_linear(circ: Circuit, nodes: Dict[int, DAGNode], favour_down: bool = True) -> Dict[int, DAGNode]:
    """
    An instance of :py:func:`merge_under_property` merges nodes that have signals in the input and output.

    filter property : has only nonlinear constraints in the node
    adj_property : does not have only nonlinear constraints in the node

    Parameters
    ----------
        circ: Circuit 
            The circuit being worked on -- NOTE: could remove and take circ from nodes but don't for consistency
        nodes: Dict(int, DAGNode)
            The collection of nodes that cluster the circuit
    
    Returns
    ----------
    Dict[int, DAGNode] 
        Nodes list after merging.
        Note that this function mutates the input nodes dictionary
    """
    is_single_unsafe_linear : Callable[[DAGNode], bool
        ] = lambda node : len(node.constraints) == 1 and not circ.constraints[next(iter(node.constraints))].is_nonlinear() and len(node.successors) > 1

    # note that this prioritises children over parents -- this is a heuristic given by Albert
    child_attraction : Callable[[DAGNode, DAGNode], int] = lambda node, child : (len(node.input_signals) if favour_down else 0) + len(node.output_signals.intersection(child.input_signals))
    parent_attraction : Callable[[DAGNode, DAGNode], int] = lambda parent, node : (0 if favour_down else len(node.output_signals)) + len(node.input_signals.intersection(parent.output_signals))

    return merge_under_property(circ, nodes, is_single_unsafe_linear, child_attraction, parent_attraction)

def merge_nodes(lkey: int, rkey: int, nodes: Dict[int, DAGNode], 
        sig_to_coni: Dict[int, List[int]], coni_to_node: List[int], adjacencies: Dict[int, List[int]]) -> None:
    """
    Helper function for merge_under_property

    Given two nodes, indexed `lkey' and `rkey' this creates a new node merging lkey and rkey 
        then mutates the various dictionaries lists to update them
    This function does not enforce any prerequitites on the nodes we assume
        that lkey is the parent of rkey, and that no cycle is created when these are merged.

    Parameters
    ----------
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
        
    Returns
    ----------
    None
        nodes, coni_to_node, adjacencies are all mutated to update with the new data
    """
    assert any(map(lambda sig : sig in nodes[rkey].input_signals, nodes[lkey].output_signals)), "lkey is not successor of rkey"

    # fixes the succesors/predecessors of all the other nodes -- also updates adjacencies
    # for each node_id in rkey.successor, finds rkey node_id.predecessor -- if lkey is a predecessor - delete rkey -- otherwise replace rkey with lkey (and add to lkey successors)
    #   does inverse too

    funcs = [lambda key : nodes[key].successors, lambda key : nodes[key].predecessors]
    for i in range(2):
        for key in funcs[1-i](rkey):
            rkey_index = funcs[i](key).index(rkey)
            if key == lkey or lkey in funcs[i](key): del funcs[i](key)[rkey_index]
            else: 
                funcs[i](key)[rkey_index] = lkey
                funcs[1-i](lkey).append(key)

    nodes[lkey].constraints.extend(nodes[rkey].constraints)

    # NOTE: if merges are taking way longer again it's probably because of input/output signal calculation which is not necessary here but for merge_passthrough
    #   it is possible to move this calculation to merge_passthrough alone -- I haven't done the refactoring but it is possible for equivalent work need to only
    #   call property on updated nodes but will require serious refactoring

    # lkey inputs are still inputs -- rkey inputs are not inputs only if the only node they connected to was lkey
    # rkey outputs are still outputs -- lkey outputs are not outputs only if the only node they connected to was rkey

    circ = next(iter(nodes.values())).circ

    nodes[lkey].input_signals.update(filter(
        lambda sig : circ.signal_is_input(sig) or any(map(lambda coni : coni_to_node[coni] in nodes[lkey].predecessors, sig_to_coni[sig])),
        nodes[rkey].input_signals
    ))
    nodes[lkey].output_signals = nodes[rkey].output_signals.union(filter(
        lambda sig : circ.signal_is_output(sig) or any(map(lambda coni : coni_to_node[coni] in nodes[lkey].successors, sig_to_coni[sig])),
        nodes[lkey].output_signals
    ))
    
    # fixes coni_to_node
    collections.deque(map(lambda coni : coni_to_node.__setitem__(coni, lkey) , nodes[rkey].constraints), maxlen=0)

    # removes entries for rkey dictionaries
    del adjacencies[rkey]
    del nodes[rkey]