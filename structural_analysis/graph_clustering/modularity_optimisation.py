"""

The goal, broadly, is the to find and isolate the different templates within a circuit.
    These usually have higher-than-normal intra-community average degree then inter-community average degree
    Hence modularity should be an appropriate way of clustering them
"""

from typing import List, Tuple, Dict
from itertools import product, chain, combinations_with_replacement

from utilities import count_ints
from r1cs_scripts.circuit_representation import Circuit
from structural_analysis.graph_clustering.clustering_from_list import UnionFind
from structural_analysis.graph_clustering.degree_clustering import _signal_data_from_cons_list

def unweighted_adjacency(circ: Circuit) -> List[List[int]]:
    _, signal_to_coni = _signal_data_from_cons_list(circ.constraints)

    adjacency = [set([]) for _ in range(circ.nConstraints)]

    for signal in signal_to_coni.keys():
        for coni in signal_to_coni[signal]:
            adjacency[coni].update(filter(lambda oconi : oconi != coni, signal_to_coni[signal]))
    
    # last conversion probably unnescary, don't think order is mattering
    return adjacency
    # return list(map(list, adjacency))

def stable_louvain(adjacency: List[List[int]]) -> List[List[int]]:
    """
    Based on the louvain community detection algorithm - modified to be consistent
    https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.community.louvain.louvain_communities.html 

    To ensure that the clustering is equivalent accross the same circuit multiple times, we:
        1. check the modularity change for every possible different insertion of a singular vertex.
        2. do (all) the merges with maximum modularity change
        3. repeat until no merges increase modularity or no singular vertices left
        4. define new network with each community representing a vertex, and go to 1
        5. return
    
    -----------------------------------------------------------------------------------------------------------------------------------
    Takes way too long, on first iteration makes nConstraints^2 comparisons...

    Poseidon ~2s
    
    """

    N = len(adjacency)
    m = sum(map(len, adjacency)) << 1

    # change to weighted version
    adjacency = [
        {u: 1 for u in adjacency[v]}
        for v in range(N) 
    ]

    clusters = UnionFind()
    list(map(clusters.find, range(N)))

    # TODO: maybe think/test different singular method
    singular = [True for _ in range(N)]

    for _ in range(N):

        for iteration in range(N):
            best_mod_changes_val = 0
            best_mod_changes = []

            singular_clusters = filter(lambda key : singular[key], clusters.get_representatives()) 

            # checkes singular-singular twice
            for lkey, rkey in product(singular_clusters, clusters.get_representatives()): 

                if lkey == rkey or ( singular[rkey] and lkey > rkey ):
                    continue 
                
                # modularity change calc 
                k_iC = sum([val for dest, val in adjacency[lkey].items() if clusters.find(dest) == rkey])
                k_i = sum(val for val in adjacency[lkey].values())
                Eps_tot = sum([val for val in adjacency[rkey].values()]) # we continuously update so that repr has all edges/weights

                mod_change = k_iC * m - k_i * Eps_tot

                if mod_change > best_mod_changes_val:
                    best_mod_changes_val = mod_change
                    best_mod_changes = [(lkey, rkey)]
                elif mod_change == best_mod_changes_val:
                    best_mod_changes.append((lkey, rkey))

            if best_mod_changes == []:
                break

            for l, r in best_mod_changes:
                l_, r_ = clusters.find(l), clusters.find(r)
                
                if l_ == r_:
                    continue

                clusters.union(l, r)
                
                # if r_ == clusters.find(r) then l -> r, otherwise r -> l -- so after this l -> r
                if r_ != clusters.find(r): l , r, l_, r_ = r , l, r_, l_
                # assert r_ == clusters.find(r) == clusters.find(l), "Theory Error"
                singular[r_] = False

                # update adjacency so that representative has all the links: since l -> r sum all (old) l links to r
                for sig in list(adjacency[l_].keys()):

                    adjacency[clusters.find(r)][
                              clusters.find(sig)] = adjacency[clusters.find(r)].setdefault(
                                                              clusters.find(sig), 0) + adjacency[l_][sig]
        
        if iteration == 0:
            break

        for sig in clusters.get_representatives():
            # make 'singular' again
            singular[sig] = True

            # some keys in adjacency may have been made no longer representative so:
            for osig in list(adjacency[sig].keys()):
                
                if clusters.find(osig) != osig:
                    adjacency[sig][clusters.find(osig)] = adjacency[sig].setdefault(clusters.find(osig), 0) + adjacency[sig][osig]
                    del adjacency[sig][osig]
    
    cluster_lists = {}

    for i in clusters.parent.keys():
        cluster_lists.setdefault(clusters.find(i), []).append(i)

    return cluster_lists.values()



def eigen_modularity_optimisation():
    """

    Based on this paper:
    https://www.pnas.org/doi/epdf/10.1073/pnas.0601602103
    
    works similar to above but starts with all vertex in 1 community, and splits it down

    TODO: finish
    """
    
    pass