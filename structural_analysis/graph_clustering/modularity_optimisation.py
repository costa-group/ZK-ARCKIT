"""

The goal, broadly, is the to find and isolate the different templates within a circuit.
    These usually have higher-than-normal intra-community average degree then inter-community average degree
    Hence modularity should be an appropriate way of clustering them
"""

from typing import List, Set, Tuple
from itertools import product, chain, combinations_with_replacement

def louvain_community_detection(adjacency: List[Set[Tuple[int, int]]]) -> List[List[int]]:
    """
    Based on the louvain community detection algorithm - modified to be consistent
    https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.community.louvain.louvain_communities.html 

    To ensure that the clustering is equivalent accross the same circuit multiple times, we:
        1. check the modularity change for every possible different insertion of a singular vertex.
        2. do (all) the merges with maximum modularity change
        3. repeat until no merges increase modularity or no singular vertices left
        4. define new network with each community representing a vertex, and go to 1
        5. return
    
    """

    N = len(adjacency)
    m = sum(map(len, adjacency)) << 1

    # since every iteration reduces the number of labels by 1 max iterations is at most N
    clusters_to_originals = {
        v: [v]
        for v in range(len(adjacency))
    }

    clusters = {
        v: [v]
        for v in range(len(adjacency))
    }

    for outer_iteration in range(N):

        for iteration in range(N):
            best_mod_changes_val = 0
            best_mod_changes = []

            singular_clusters = filter(lambda key : len(clusters[key]) == 1, clusters.keys()) 

            # checkes singular-singular twice
            for lkey, rkey in product(singular_clusters, clusters.keys()):
                if lkey == rkey or ( len(clusters[rkey]) == 1 and lkey > rkey ):
                    continue 
                
                # modularity change calc 
                k_iC = sum([val for dest, val in adjacency[lkey] if dest in clusters[rkey]])
                k_i = sum(val for _, val in adjacency[lkey])
                Eps_tot = sum([val for mem in clusters[lkey] for _, val in adjacency[mem]])

                mod_change = k_iC * m - k_i * Eps_tot

                if mod_change > best_mod_changes_val:
                    best_mod_changes_val = mod_change
                    best_mod_changes = [(lkey, rkey)]
                elif mod_change == best_mod_changes_val:
                    best_mod_changes.append((lkey, rkey))

            if best_mod_changes == []:
                break

            for l, r in best_mod_changes:
                clusters[l].extend(clusters[r])
                del clusters[r]
        
        if iteration == 0:
            break
        
        # note what the key is actually referring to
        clusters_to_originals = {
            key: list(chain(*map(lambda key_ : clusters_to_originals[key_], cluster)))
            for key, cluster in clusters.items()
        }

        adjacency = {
            key: set(filter(
                lambda tup: tup[1] > 0,
                [(r, sum([
                    w for l_ in clusters[key] for r_, w in adjacency[l_] if r_ in clusters[rkey]
                ]))
                for rkey in clusters.keys()]
            ))            
            for key in clusters.keys()
        }

        clusters = {
            v: [v]
            for v in clusters.keys()
        }
    
    if outer_iteration > 0: return clusters_to_originals.values()
    else: return clusters.values()

    # TODO: bugfix



def eigen_modularity_optimisation():
    """

    Based on this paper:
    https://www.pnas.org/doi/epdf/10.1073/pnas.0601602103
    
    works similar to above but starts with all vertex in 1 community, and splits it down

    TODO: finish
    """
    
    pass