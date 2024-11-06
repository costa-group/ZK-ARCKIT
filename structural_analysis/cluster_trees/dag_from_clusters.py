from typing import List, Dict, Set, Tuple, Iterable
import itertools
import json

from utilities import UnionFind, _signal_data_from_cons_list, getvars, dist_to_source_set
from comparison.static_distance_preprocessing import _distances_to_signal_set
from r1cs_scripts.circuit_representation import Circuit
from r1cs_scripts.constraint import Constraint

def partition_from_partial_clustering(
        circ: Circuit, clusters: List[List[int]], 
        remaining: List[int] | None = None,
        group_unclustered: bool = False) -> List[List[int]]:
    
    not_in_cluster = [True for _ in range(circ.nConstraints)]

    for coni in itertools.chain(*clusters): not_in_cluster[coni] = False

    if remaining is None:
        remaining = list(filter(not_in_cluster.__getitem__, range(circ.nConstraints)))
    
    if not group_unclustered: return list(itertools.chain(clusters, map(lambda x : [x], remaining)))

    sig_to_coni = _signal_data_from_cons_list(circ.constraints)
    unclustered_uf = UnionFind()
    
    for coni in remaining:
        unclustered_uf.find(coni)
        adj_unclustered_coni = set(filter(not_in_cluster.__getitem__, itertools.chain(*map(sig_to_coni.__getitem__, getvars(circ.constraints[coni])))))
        # adj_unclustered will contain coni
        unclustered_uf.union(*adj_unclustered_coni)
    
    remaining_clusters = {}
    for coni in remaining:
        remaining_clusters.setdefault(unclustered_uf.find(coni), []).append(coni)
    
    return list(itertools.chain(clusters, remaining_clusters.values())) 


def dag_from_partition(circ: Circuit, partition: List[List[int]]) -> "directed_acyclic_graph":

    # TODO: make subordinate function to handle all this prep
    # TODO: optimise this it's very messy
    # copying to avoid mutating

    partition = {i : part for i, part in enumerate(partition)}

    is_input_sig = lambda sig : circ.nPubOut < sig <= circ.nPubOut + circ.nPubIn + circ.nPrvIn
    is_output_sig = lambda sig : 0 < sig <= circ.nPubOut

    part_to_sigs = lambda part : itertools.chain(*map(lambda coni : getvars(circ.constraints[coni]), part))
    input_parts = set(filter(lambda i : any(map(is_input_sig, part_to_sigs(partition[i]))),partition.keys()))
    output_parts = set(filter(lambda i : any(map(is_output_sig, part_to_sigs(partition[i]))),partition.keys()))

    coni_to_part = [None for _ in range(circ.nConstraints)]
    for i, part in partition.items():
        for coni in part: coni_to_part[coni] = i

    sig_to_coni = _signal_data_from_cons_list(circ.constraints)

    adj_parts = lambda part_id, part : set(
        filter(lambda opair_id : opair_id != part_id, 
        map(coni_to_part.__getitem__, 
        itertools.chain(*map(sig_to_coni.__getitem__, 
        part_to_sigs(part))))))

    adjacencies = {i: adj_parts(i, part) for i, part in partition.items() }

    merged = True
    while merged:
        merged = False

        dist_to_inputs = dist_to_source_set(input_parts, adjacencies)
        dist_to_outputs = dist_to_source_set(output_parts, adjacencies)

        ## make the preorder
        part_to_preorder = { i: (dist_to_outputs[i], dist_to_inputs[i]) for i in partition.keys()}
        
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
        return part_to_preorder[parti][0] >= part_to_preorder[partj][0] or (part_to_preorder[parti][0] == part_to_preorder[partj][0] and part_to_preorder[parti][1] <= part_to_preorder[partj][1])

    # define arc direction and return.
    mapping = {key: i for i, key in enumerate(partition.keys())}
    arcs = [(mapping[parti], mapping[partj]) for parti in adjacencies.keys() for partj in adjacencies[parti] if le(parti, partj)]
    
    return list(partition.values()), arcs

def merge_parts(to_merge: List[List[int]], input_parts: Set[int], output_parts: Set[int], partition: Dict[int, int], adjacencies: Dict[int, Set[int]]):
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

    def __init__(self, 
        circ: Circuit, node_id: int, constraints: List[int], input_signals: Set[int], output_signals: Set[int] 
    ):
        self.circ, self.id, self.constraints, self.input_signals, self.output_signals, self.successors, self.subcircuit = (
            circ, node_id, constraints, input_signals, output_signals, [], None
        )
    
    def add_successors(self, successor_ids: Iterable[int]) -> None:
        self.successors.extend(successor_ids)

    def get_subcircuit(self) -> Circuit:

        if self.subcircuit is None:

            self.subcircuit = Circuit()

            ordered_signals = list(itertools.chain(
                [0],
                self.output_signals.difference(self.input_signals), # TODO: how to handle signal being in input AND output?
                self.input_signals,
                set(itertools.chain(*map(getvars, map(self.circ.constraints.__getitem__, self.constraints)))).difference(itertools.chain(self.output_signals, self.input_signals))
            ))

            sig_mapping = dict(zip(
                ordered_signals,
                range(len(ordered_signals))
            ))

            self.subcircuit.constraints = list(map(lambda con : 
                Constraint(
                    *[{sig_mapping[sig]: val for sig, val in dict_.items()} for dict_ in [con.A, con.B, con.C]],
                    con.p
                ),
                map(self.circ.constraints.__getitem__, self.constraints)))
            
            self.subcircuit.update_header(
                self.circ.field_size,
                self.circ.prime_number,
                len(sig_mapping),
                len(self.output_signals.difference(self.input_signals)),
                len(self.input_signals),
                0, # prv in doesn't matter
                None,
                len(self.constraints)
            )

        return self.subcircuit
    
    def to_dict(self) -> Dict[str, int | List[int]]:
        return {
            key: val for key, val in [
                ("node_id", self.id), ("constraints", self.constraints),
                ("input_signals", list(self.input_signals)), ("output_signals", list(self.output_signals)),
                ("successors", self.successors)
            ]
        }

def dag_to_nodes(circ: Circuit, partition: List[List[int]], arcs: List[Tuple[int, int]]) -> Dict[int, DAGNode]:

    # TODO: slower then just iterating once, could use a consume on a subordinate function

    part_to_signals = list(map(lambda part : set(itertools.chain(*map(lambda coni : getvars(circ.constraints[coni]), part))), partition))

    nodes: List[DAGNode] = {
        i : DAGNode(
            circ, i, part,
            set(filter(lambda sig : circ.nPubOut < sig <= circ.nPubOut + circ.nPrvIn + circ.nPrvIn, part_to_signals[i])),
            set(filter(lambda sig : 0 < sig <= circ.nPubOut, part_to_signals[i]))
        )
        for i, part in enumerate(partition)
    }

    for arc in arcs:

        l, r = arc
        nodes[l].successors.append(r)

        # need to identify signals shared between these arcs, then mark these signals as input/output as appropriate
        shared_signals = part_to_signals[l].intersection(part_to_signals[r])
        nodes[l].output_signals.update(shared_signals)
        nodes[r].input_signals.update(shared_signals)
    
    return nodes


def nodes_to_json(nodes: Iterable[DAGNode], outfile: str = "test.json") -> None:
    # TODO: separate the node generation from this to not call it twice..

    f = open(outfile, 'w')
    json.dump(list(map(lambda n : n.to_dict(), nodes)), f, indent=4)
    f.close()


    
