"""
Functions for converting clusters into Directed Acyclic Graphs (DAG)
"""

from typing import List, Dict, Set, Tuple, Iterable
import itertools
import json
import warnings

from utilities.utilities import UnionFind, _signal_data_from_cons_list, dist_to_source_set, _distances_to_signal_set
from circuits_and_constraints.abstract_circuit import Circuit
from circuits_and_constraints.abstract_constraint import Constraint

def partition_from_partial_clustering(
        circ: Circuit, clusters: List[List[int]], 
        remaining: List[int] | None = None,
        group_unclustered: bool = False) -> List[List[int]]:
    """
    Given a partial clustering for a given circuit, this returns a full partition.

    Parameters
    ----------
        circ: Circuit
            The circuit upon which we are providing a partition
        clusters: List[List[int]]
            A list of clusters, each cluster is a list of constraint indices.
                - each cluster is assumed to be a connected component
                - each cluster is pairwise disjoint, i.e. every constraint index is in at most 1 cluster
        remaining: List[int] | None
            A list of the constraint indices not appearing in any cluster. If None is provided this is calculated.    
        group_unclustered: Bool
            Defines the clustering_method used for the remaining value. If False each remaining constraint is given its own cluster.
            If True, the remaining constraints are clustered in connected components.
    
    Returns
    ----------
    List[List[int]]
        A partition of the circuit, that is, a cluster whever every constraint index appears in exactly 1 cluster.
    """
    
    not_in_cluster = [True for _ in range(circ.nConstraints)]

    for coni in itertools.chain(*clusters): not_in_cluster[coni] = False

    if remaining is None:
        remaining = list(filter(not_in_cluster.__getitem__, range(circ.nConstraints)))
    
    if not group_unclustered: return list(itertools.chain(clusters, map(lambda x : [x], remaining)))

    sig_to_coni = _signal_data_from_cons_list(circ.constraints)
    unclustered_uf = UnionFind()
    
    for coni in remaining:
        unclustered_uf.find(coni)
        adj_unclustered_coni = set(filter(not_in_cluster.__getitem__, itertools.chain(*map(sig_to_coni.__getitem__, circ.constraints[coni].signals()))))
        # adj_unclustered will contain coni
        unclustered_uf.union(*adj_unclustered_coni)
    
    remaining_clusters = {}
    for coni in remaining:
        remaining_clusters.setdefault(unclustered_uf.find(coni), []).append(coni)
    
    return list(itertools.chain(clusters, remaining_clusters.values())) 


def dag_from_partition(circ: Circuit, partition: List[List[int]]) -> "directed_acyclic_graph":
    """
    Given a circuit and partition, it returns a new partition and arcs that define a directed acyclic graph.

    Each partition is given a key (distance_to_input, distance_to_outputs) used in a partial ordering.
        The distances are counting number of parts, not number of constraints.
        If two parts are adjacent and have the same key these are merged thus we achieve a strict partial ordering

    The strict partial ordering is defined as follows:
        if parti closer to inputs than partj. parti < partj
        if parti, partj same distance from inputs but partj closer to outputs parti < partj.

    Parameters
    ----------
        circ: Circuit
            The circuit upon which we are providing a partition
        partition: List[List[int]]
            A partition of the circuit, that is, a list of clusters whever every constraint index appears in exactly 1 cluster.

    Returns
    ------- 
    (partition, arcs)
        partition; List[List[int]]
            
            A new partition with some clusters in the input version merged -- does not mutate the original partition

        arcs; List[Tuple[int, int]]
            
            A list of arcs (parti, partj).
    """

    # TODO: do we want to have distance to inputs being early -- we can isolate solo parts and adjust these accordingly.
    #   specifically, this method ensures solo parts are outgoing but arms might not be...
    #   TODO: think of a better partial ordering.
    #       what is the rule that we want, every path from an input to an output should be directed...
    #       can we efficiently calculate this?

    # TODO: make subordinate function to handle all this prep
    # TODO: optimise this it's very messy
    # copying to avoid mutating

    partition: Dict[int, List[int]] = {i : part for i, part in enumerate(partition)}

    part_to_sigs = lambda part : itertools.chain.from_iterable(map(lambda coni : circ.constraints[coni].signals(), part))
    input_parts = set(filter(lambda i : any(map(circ.signal_is_input, part_to_sigs(partition[i]))),partition.keys()))
    output_parts = set(filter(lambda i : any(map(circ.signal_is_output, part_to_sigs(partition[i]))),partition.keys()))

    coni_to_part = [None for _ in range(circ.nConstraints)]
    for i, part in partition.items():
        for coni in part: 
            if coni_to_part[coni] is not None: warnings.warn(f"NOT PARTITION: coni {coni} is in {i} and {coni_to_part[coni]}")
            coni_to_part[coni] = i

    sig_to_coni = _signal_data_from_cons_list(circ.constraints)

    adj_parts = lambda part_id, part : set(
        filter(lambda opair_id : opair_id != part_id, 
        map(coni_to_part.__getitem__, 
        itertools.chain.from_iterable(map(sig_to_coni.__getitem__, 
        part_to_sigs(part))))))

    adjacencies = {i: adj_parts(i, part) for i, part in partition.items() }

    merged = True
    while merged:
        merged = False

        dist_to_inputs = dist_to_source_set(input_parts, adjacencies)
        dist_to_outputs = dist_to_source_set(output_parts, adjacencies)

        ## make the preorder
        part_to_preorder = { i: (dist_to_inputs.get(i, float("inf")), dist_to_outputs.get(i, float("inf"))) for i in partition.keys()}
        
        to_merge = UnionFind()

        ## detect equivalent adjacent pairs and merge them
        for parti in partition.keys():
            for partj in adjacencies[parti]:
                if part_to_preorder[parti] == part_to_preorder[partj]:
                    merged = True
                    to_merge.union(parti, partj)
        
        parti_to_merge = {}
        for parti in to_merge.parent.keys():
            parti_to_merge.setdefault(to_merge.find(parti), []).append(parti)
        
        ## handle new adjacencies / distances 
            ## think of shortcuts
        merge_parts(parti_to_merge.values(), input_parts, output_parts, partition, adjacencies)

    ## then make DAG from partial order

    def le(parti, partj):
        # At this point we know that parti and partj differ in at least 1 place
        # if parti closer to inputs, then parti < partj
        #   if parti and partj equivalent dist to inputs and partj closer to outputs, then parti < partj

        return part_to_preorder[parti][0] < part_to_preorder[partj][0] or (
            part_to_preorder[parti][0] == part_to_preorder[partj][0] and part_to_preorder[parti][1] > part_to_preorder[partj][1])

    # define arc direction and return.
    mapping = {key: i for i, key in enumerate(partition.keys())}
    arcs = [(mapping[parti], mapping[partj]) for parti in adjacencies.keys() for partj in adjacencies[parti] if le(parti, partj)]
    
    return list(partition.values()), arcs

def merge_parts(to_merge: List[List[int]], input_parts: Set[int], output_parts: Set[int], partition: Dict[int, int], adjacencies: Dict[int, Set[int]]):
    """
    subordinate function of dag_from_partition
    
    iterating over the input list, merges a list of parts and updates the various adjacencies.
    """
    
    # mutates the above

    for merge_list in to_merge:
        root, to_elim = merge_list[0], merge_list[1:]

        partition[root] = list(itertools.chain(*map(partition.__getitem__, merge_list)))
        adjacencies[root] = set(itertools.chain(*map(adjacencies.__getitem__, merge_list))).difference(merge_list)

        for parti in to_elim: 
            del partition[parti]
            for partj in filter(lambda x : x not in merge_list, adjacencies[parti]):
                adjacencies[partj].remove(parti)
                adjacencies[partj].add(root)
            del adjacencies[parti]
    
        for source in [input_parts, output_parts]:
            source_in_merge_list = source.intersection(merge_list)
            if len(source_in_merge_list) > 0:
                source.difference_update(source_in_merge_list)
                source.add(root)

class DAGNode():
    """
    Cluster for Node in a DAG

    Attributes
    ----------
        circ: Circuit
            the Circuit upon which the node is represented
        id: Int
            the index of the node
        constraints: List[int]
            the constraints that make up the part of the node
        input_signals: Set[int]
            external signals in the node stemming from incoming arcs in the DAG
        output_signals: Set[int]
            external signals in the node stemming from outgoing arcs in the DAG
        successors: List[int]
            node indexes of successor nodes in the DAG
        predecessors: List[int]
            node indexes of predecessor nodes in the DAG
        subcircuit: Circuit | None
            If the subcircuit represented by the node has been calculated it is stored here otherwise it is None
    """

    def __init__(self, 
        circ: Circuit, node_id: int, constraints: List[int], input_signals: Set[int], output_signals: Set[int] 
    ):
        """
        Constructor for DAGNode

        Parameters
        ----------
            circ: Circuit
                the Circuit upon which the node is represented
            id: Int
                the index of the node
            constraints: List[int]
                the constraints that make up the part of the node
            input_signals: Set[int]
                external signals in the node stemming from incoming arcs in the DAG
            output_signals: Set[int]
                external signals in the node stemming from outgoing arcs in the DAG
        """
        self.circ, self.id, self.constraints, self.input_signals, self.output_signals, self.successors, self.predecessors, self.subcircuit = (
            circ, node_id, constraints, input_signals, output_signals, [], [], None
        )
    
    def add_successors(self, successor_ids: Iterable[int]) -> None:
        "Adds successors to the list of successors"
        # NOTE: I think this is never actually used... we could do a full getter/setter but I'm not that bothered
        self.successors.extend(successor_ids)

    def get_subcircuit(self) -> Circuit:
        """
        Returns the subcircuit represented by the node and caches it for later reuse

        The subcircuit is the circuit containing only the constraints in the node,
        the circuit is completely new with a signal and constraint bijection to the subcircuit in self.circ
        this is because Circuits are assumed to always have signals 0..nSignals not a set of named signals
        """

        if self.subcircuit is None: self.subcircuit = self.circ.take_subcircuit(self.constraints, self.input_signals, self.output_signals)
        return self.subcircuit
    
    def to_dict(self, inverse_mapping : Tuple[dict] | None = None) -> Dict[str, int | List[int]]:
        """
        Returns a dictionary that contains the information required for outputting to JSON
        """

        def inverse_coni(index):
            if inverse_mapping is None: return index
            return inverse_mapping[0][index]
    
        def inverse_signal(index):
            if inverse_mapping is None: return index
            return inverse_mapping[1][index]

        return {
            key: val for key, val in [
                ("node_id", self.id), ("constraints", list(map(inverse_coni, self.constraints))), ("signals", list(map(inverse_signal, set(itertools.chain.from_iterable(map(lambda con : con.signals(), map(self.circ.constraints.__getitem__, self.constraints))))))),
                # need to convert to hashable type list
                ("input_signals", list(map(inverse_signal, self.input_signals))), ("output_signals", list(map(inverse_signal, self.output_signals))),
                ("successors", self.successors)
            ]
        }

def dag_to_nodes(circ: Circuit, partition: List[List[int]], arcs: List[Tuple[int, int]], index_offset: int = 0) -> Dict[int, DAGNode]:
    """
    Given a circ and DAG, returns a dictionary of nodes populated with data, indexes by the node_id.

    We use a dictionary here rather than a list due to postprocessing merging nodes and putting gaps in the index set.
    using a dictionary avoids remapping the indices at every step.

    Process
    ----------
        loop over partitions to define initial information, that is, constraints, id, and any signals that are input/output in the circ,
        then loop over arcs, these define predecessor/successors and expand input/output signals
    """

    # TODO: slower then just iterating once, could use a consume on a subordinate function

    part_to_signals = list(map(lambda part : set(itertools.chain.from_iterable(map(lambda coni : circ.constraints[coni].signals(), part))), partition))

    nodes: List[DAGNode] = {
        i + index_offset : DAGNode(
            circ, i + index_offset, part,
            set(filter(circ.signal_is_input, part_to_signals[i])),
            set(filter(circ.signal_is_output, part_to_signals[i]))
        )
        for i, part in enumerate(partition)
    }

    for arc in arcs:

        l, r = arc
        nodes[l].successors.append(r)
        nodes[r].predecessors.append(l)

        # need to identify signals shared between these arcs, then mark these signals as input/output as appropriate
        shared_signals = part_to_signals[l].intersection(part_to_signals[r])

        nodes[l].output_signals.update(shared_signals)
        nodes[r].input_signals.update(shared_signals)
    
    return nodes


def nodes_to_json(nodes: Iterable[DAGNode], outfile: str = "test.json") -> None:
    "Named function to write the json from the nodes to a .json file"

    f = open(outfile, 'w')
    json.dump(list(map(lambda n : n.to_dict(), nodes)), f, indent=4)
    f.close()


    
