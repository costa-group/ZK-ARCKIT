from typing import Callable, Tuple, List, Dict
import itertools

from utilities import getvars, is_not_none, UnionFind
from r1cs_scripts.circuit_representation import Circuit
from structural_analysis.clustering_methods.naive.signal_equivalence_clustering import naive_removal_clustering

def r1cs_distance_tree(
        circ: Circuit,
        clustering_method: Callable[[Circuit], Tuple[Dict[int,List[int]], any, List[int]]] = naive_removal_clustering,
    ) -> Tuple[Dict[int, List[int]], List[Tuple[int, int]]]:
    """
    Given an r1cs as input it first attempts to identify and removed all 'link' constraints, those that separate between components, 
    clustering the remaning constraint according to shared signals.
        Then it defines new clusters from the removed constraints based on adjacencies to existing constraints, recursively doing so
    until all constraints are in cluster. It additionally returns the tree adjacencies of this structure.
    """

    clusters, _, removed = naive_removal_clustering(circ, calculate_adjacency = False)

    signal_to_repr = [None for _ in range(circ.nWires)] # worse memory up front but better memory over runtime
    adjacencies = []
    repr_to_conis = {}

    counter = 0 # global new name for signals

    for repr, cluster in clusters.items():  
        repr_to_conis[counter] = cluster

        for sig in itertools.chain(*map(lambda coni : getvars(circ.constraints[coni]), cluster)):
            signal_to_repr[sig] = counter
        counter += 1

    while len(removed) > 0:

        not_adjacent_to_any = []
        adjacency_uf = UnionFind()
        repr_to_adjacent_removed = {}

        # calculate which constraints are adjacent to existing clusters
        for coni in removed:
            adj_repr_set = set(filter(is_not_none, map(signal_to_repr.__getitem__, getvars(circ.constraints[coni]))))

            if len(adj_repr_set) == 0: not_adjacent_to_any.append(coni)
            for repr in adj_repr_set: repr_to_adjacent_removed.setdefault(repr, []).append(coni)
            adjacency_uf.union(*adj_repr_set)

         # merge prepr by internal adjacencies -- maybe better idea - I think the clustering removed is just the same
        sig_to_new_repr = {}
        for repr, adjacent in repr_to_adjacent_removed.items():
            for sig in set(itertools.chain(*map(getvars, map(circ.constraints.__getitem__, adjacent)))):
                sig_to_new_repr.setdefault(sig, []).append(repr)
        
        # In O0 if two constraint share a signal, either direct call or in same component
        #   if two constraints share a signal, and are both direct calling the same component
        #   then as long as they are not using equivalence rewriting they are in the same component
        #   if we want to maintain a tree structure we must assume this is true, otherwise we much change to a DAG structure
        for incident_repr in sig_to_new_repr.values():
            adjacency_uf.union(*incident_repr)
        
        # collate repr into a single parent repr
        prepr_to_adjacent_removed = {}
        for repr in adjacency_uf.parent.keys():
            prepr_to_adjacent_removed.setdefault(adjacency_uf.find(repr), set([])).update(repr_to_adjacent_removed[repr])

        # write new cluster 'counter' for each prepr and update signal/adjacency values
        for adjacent in prepr_to_adjacent_removed.values():
            repr_to_conis[counter] = list(adjacent)
            counter_adjacencies = set([])

            for sig in set(itertools.chain(*map(getvars, map(circ.constraints.__getitem__, adjacent)))):
                if signal_to_repr[sig] is None:
                    signal_to_repr[sig] = counter
                else:
                    counter_adjacencies.add((counter, signal_to_repr[sig]))
            
            adjacencies.extend(counter_adjacencies)
            counter += 1
        
        removed = not_adjacent_to_any
    
    # TODO: adjacency calculation?
    return repr_to_conis, adjacencies


        

           
           

