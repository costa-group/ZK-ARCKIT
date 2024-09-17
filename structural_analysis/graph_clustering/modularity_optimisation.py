"""

The goal, broadly, is the to find and isolate the different templates within a circuit.
    These usually have higher-than-normal intra-community average degree then inter-community average degree
    Hence modularity should be an appropriate way of clustering them

Resolution limits I think will also play a key part meaning modularity may not be the best..
"""

from typing import List, Tuple, Dict, Callable
from itertools import product, chain, combinations

from utilities import count_ints
from r1cs_scripts.circuit_representation import Circuit
from structural_analysis.graph_clustering.clustering_from_list import UnionFind
from utilities import _signal_data_from_cons_list

def undirected_adjacency(circ: Circuit, unweighted: bool = False) -> List[List[int]]:
    signal_to_coni = _signal_data_from_cons_list(circ.constraints)

    adjacency = [{} for _ in range(circ.nConstraints)]

    for signal in signal_to_coni.keys():
        for l, r in combinations(signal_to_coni[signal], 2):
            adjacency[l][r] = adjacency[l].setdefault(r, 0) + 1
            adjacency[r][l] = adjacency[r].setdefault(l, 0) + 1

    if unweighted:
        adjacency = [ list(adjacency[v].keys()) for v in range(len(adjacency)) ]

    # last conversion probably unnescary, don't think order is mattering
    return adjacency
    # return list(map(list, adjacency))

def abs_stable_louvain(
        N: int,
        adjacency_args: List,
        get_adjacent_to: Callable,
        calculate_mod_change: Callable,
        inner_update_adjacency: Callable,
        outer_update_adjacency: Callable,
        tolerance: float = 0,
        inner_loop_limit: int = float("inf"),
        outer_loop_limit: int = float("inf"),
        return_unionfind: bool = False,
        debug: bool = False
    ) -> List[List[int]]:
    """
    A pseudo-abstract stable louvain method that holds the skeleton to be used by the undirected and directed versions

    ## TODO: modularize the function so that we can have iteration limits.. we know 1 iteration will take ~20s
        # possible algorithm version is a version where we have a relatively high tolerance.. say 50%
        # and only run ~4-5 iterations of the inner.. How would this scale, better than twice average degree? It's stable.
        #   current reveal times are ~30s total... would need to show great improvement in resultant encoding for this to work
        #   given low estimates of ~2-3min..
    """

    clusters = UnionFind(representative_tracking=True)
    list(map(clusters.find, range(N)))

    singular = [True for _ in range(N)]

    # since each iteration reduces the total number of clusters each is capped by N
    for outer_iteration in range(min(outer_loop_limit, N)):
        for iteration in range(min(inner_loop_limit, N)):

            best_mod_changes_val = 0
            best_mod_changes = []

            singular_clusters = filter(lambda key : singular[key], clusters.get_representatives()) 

            # checkes singular-singular twice
            for lkey, rkey in chain(*
                    map(
                        lambda sig:  product([sig], map(clusters.find, get_adjacent_to(sig, *adjacency_args))), 
                        singular_clusters
                    )
                ): 
                if debug: print(lkey, rkey, "                                 ", end='\r')

                if lkey == rkey or ( singular[rkey] and lkey > rkey ):
                    continue 
                
                # modularity change calc 
                mod_change = calculate_mod_change(lkey, rkey, clusters, *adjacency_args)

                if mod_change > best_mod_changes_val:
                    best_mod_changes_val = mod_change
                    
                    if tolerance == 0:
                        best_mod_changes = [(lkey, rkey, mod_change)]
                    if tolerance > 0: 
                        best_mod_changes = list(filter(lambda tup : tup[2] >= mod_change * (1-tolerance), best_mod_changes))
                        best_mod_changes.append((lkey, rkey, mod_change))
                        
                elif mod_change >= best_mod_changes_val * (1 - tolerance):
                    best_mod_changes.append((lkey, rkey, mod_change))

            if best_mod_changes == []:
                break

            if debug: print(outer_iteration, iteration, best_mod_changes_val, len(best_mod_changes))

            for l, r, _ in best_mod_changes:
                l_, r_ = clusters.find(l), clusters.find(r)
                
                if l_ == r_:
                    continue

                clusters.union(l, r)
                
                # if r_ == clusters.find(r) then l -> r, otherwise r -> l -- so after this l -> r
                if r_ != clusters.find(r): l_, r_ = r_, l_
                # assert r_ == clusters.find(r) == clusters.find(l), "Theory Error"
                singular[r_] = False

                # update adjacency so that representative has all the links: since l -> r sum all (old) l links to r
                inner_update_adjacency(l_, r_, clusters, *adjacency_args)

        if iteration == 0:
            break
        
        if debug: print(f"################### {outer_iteration, len(clusters.get_representatives())} #################")

        for sig in clusters.get_representatives():
            # make 'singular' again
            singular[sig] = True

            # some keys in adjacency may have been made no longer representative so:
            outer_update_adjacency(sig, clusters, *adjacency_args)

    if return_unionfind: return clusters

    cluster_lists = {}

    for i in range(N):
        cluster_lists.setdefault(clusters.find(i), []).append(i)

    return cluster_lists

def undirected_inner_update_adjacency(l_: int, r_: int, clusters: UnionFind, adjacency: List[Dict[int, int]], totals: List[int]):

        for sig, val in adjacency[l_].items():
            adjacency[r_][clusters.find(sig)] = adjacency[r_].setdefault(clusters.find(sig), 0) + val
            totals[r_] += val

def undirected_outer_update_adjacency(sig: int, clusters: UnionFind, adjacency: List[Dict[int, int]], totals: List[int]):

    for osig in list(adjacency[sig].keys()):
        if clusters.find(osig) != osig:
            adjacency[sig][clusters.find(osig)] = adjacency[sig].setdefault(clusters.find(osig), 0) + adjacency[sig][osig]
            del adjacency[sig][osig]

def stable_undirected_louvain(
        adjacency: List[Dict[int, int]],
        resolution: int = 1,
        resistance: int = 0,
        **kwargs
    ) -> List[List[int]]:

    N = len(adjacency)

    # add resistances if required
    if resistance > 0:
        for v in range(N): adjacency[v][v] = resistance

    totals = [sum(adjacency[v].values()) for v in range(N)]
    m = sum(totals) << 1

    adjacency_args = [adjacency, totals]

    def get_adjacent_to(sig: int, adjacency: List[Dict[int, int]], totals: List[int]):
        return adjacency[sig].keys()

    def calculate_mod_change(lkey: int, rkey: int, clusters: UnionFind, adjacency: List[Dict[int, int]], totals: List[int]):

        k_iC = sum([val for dest, val in adjacency[lkey].items() if clusters.find(dest) == rkey])
        k_i = totals[lkey]
        Eps_tot = totals[rkey] # we continuously update so that repr has all edges/weights

        mod_change = k_iC * m - resolution * k_i * Eps_tot

        return mod_change
    
    return abs_stable_louvain(
        N,
        adjacency_args,
        get_adjacent_to,
        calculate_mod_change,
        undirected_inner_update_adjacency,
        undirected_outer_update_adjacency,
        **kwargs
    )

def directed_add_resistance(resistance: int, in_adjacency: List[Dict[int, int]], out_adjacency: List[Dict[int, int]]):
    for v in range(len(in_adjacency)):
        in_adjacency[v][v] = in_adjacency[v].setdefault(v, 0) + resistance
        out_adjacency[v][v] = out_adjacency[v].setdefault(v, 0) + resistance

def directed_get_adjacent_to(sig: int, in_adjacency: List[Dict[int, int]], out_adjacency: List[Dict[int, int]], totals_in: List[int], totals_out: List[int], resolution: int, m: int):
        return set(chain(in_adjacency[sig].keys(), out_adjacency[sig].keys()))
    
def directed_calculate_mod_change(lkey: int, rkey: int, clusters: UnionFind, in_adjacency: List[Dict[int, int]], out_adjacency: List[Dict[int, int]], totals_in: List[int], totals_out: List[int], resolution: int, m: int):
    k_i_in = sum([val for adjacency in [in_adjacency, out_adjacency] for dest, val in adjacency[lkey].items() if clusters.find(dest) == rkey])
    k_out_i = totals_out[lkey]
    k_in_i = totals_in[lkey]
    eps_in = totals_in[rkey]
    eps_out = totals_out[rkey]

    mod_change = k_i_in * m - resolution * (k_out_i * eps_in + k_in_i * eps_out)

    return mod_change 

def directed_inner_update_adjacency(l_: int, r_: int, clusters: UnionFind, in_adjacency: List[Dict[int, int]], out_adjacency: List[Dict[int, int]], totals_in: List[int], totals_out: List[int], resolution: int, m: int):

    for adjacency, totals in [(in_adjacency, totals_in), (out_adjacency, totals_out)]:
        undirected_inner_update_adjacency(l_, r_, clusters, adjacency, totals)

def directed_outer_update_adjacency(sig: int, clusters: UnionFind, in_adjacency: List[Dict[int, int]], out_adjacency: List[Dict[int, int]], totals_in: List[int], totals_out: List[int], resolution: int, m: int):

    for adjacency, totals in [(in_adjacency, totals_in), (out_adjacency, totals_out)]:
        undirected_outer_update_adjacency(sig, clusters, adjacency, totals)

def stable_directed_louvain(
        in_adjacency: List[Dict[int, int]], 
        out_adjacency: List[Dict[int, int]],
        resolution: int = 1,
        resistance: int = 0,
        **kwargs
    ) -> List[List[int]]:
    
    """
    Works as stable_louvain but for a directed graph
    Will be too slow for Reveal on its own but will be used (hopefully) for stabilising the dag_clustering_from_formula
    """
    
    N = len(in_adjacency)

    if resistance > 0: directed_add_resistance(resistance, in_adjacency, out_adjacency)

    totals_in  = [sum(in_adjacency[v].values()) for v in range(N)] 
    totals_out = [sum(out_adjacency[v].values()) for v in range(N)] 

    m = sum(totals_in)

    adjacency_args = [in_adjacency, out_adjacency, totals_in, totals_out, resolution, m]

    return abs_stable_louvain(
        N, adjacency_args,
        directed_get_adjacent_to,
        directed_calculate_mod_change,
        directed_inner_update_adjacency,
        directed_outer_update_adjacency,
        **kwargs
    )

def eigen_modularity_optimisation():
    """

    Based on this paper:
    https://www.pnas.org/doi/epdf/10.1073/pnas.0601602103
    
    works similar to above but starts with all vertex in 1 community, and splits it down

    TODO: implement this
    """
    
    pass