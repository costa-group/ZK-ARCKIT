from typing import List, Dict, Set
import itertools

from utilities import UnionFind, _signal_data_from_cons_list, getvars, dist_to_source_set
from comparison.static_distance_preprocessing import _distances_to_signal_set
from r1cs_scripts.circuit_representation import Circuit

def partition_from_partial_clustering(circ: Circuit, clusters: List[List[int]], remaining: List[int] | None = None) -> List[List[int]]:
    
    not_in_cluster = [True for _ in range(circ.nConstraints)]

    for coni in itertools.chain(*clusters): not_in_cluster[coni] = False

    if remaining is None:
        remaining = list(filter(not_in_cluster.__getitem__, range(circ.nConstraints)))
    
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
        part_to_preorder = [(dist_to_outputs[i], dist_to_inputs[i]) for i in partition.keys()]
        
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
    arcs = [(parti, partj) for parti in adjacencies.keys() for partj in adjacencies[parti] if le(parti, partj)]
    
    return list(partition.values()), arcs

def merge_parts(to_merge: List[List[int]], input_parts: Set[int], output_parts: Set[int], partition: Dict[int, int], adjacencies: Dict[int, Set[int]]):
    # mutates the above

    for merge_list in to_merge:
        root, to_elim = merge_list[0], merge_list[1:]

        partition[root] = list(itertools.chain(*map(partition.__getitem__, merge_list)))
        adjacencies[root] = set(itertools.chain(*map(adjacencies.__getitem__, merge_list))).difference(merge_list)

        for parti in to_elim: 
            del merge_list[parti]
            for partj in filter(lambda x : x not in merge_list, adjacencies[parti]):
                adjacencies[partj].remove(parti)
                adjacencies[partj].add(root)
            del adjacencies[parti]
    
        for source in [input_parts, output_parts]:
            source_in_merge_list = source.intersection(merge_list)
            if len(source_in_merge_list) > 0:
                source.difference_update(source_in_merge_list)
                source.add(root)
    
