"""

We know that r1cs circuits have a sense of 'flow'. That is that from the inputs various constraints eventually 

    -- clustering in DAGs: https://www.emis.de/journals/AMEN/2021/AMEN-200819.pdf 
        -- the above is the same paper...

The above paper proposes a method for clustering a directed acyclic graph under a topological ordering (given by the graph).

It does this by calculting some best partitioning r_{k+1} for the set of ordered vertices x_{k+1}...x_n
    and then deiciding which of the [x_k, ..., x_k+i] + r_{k+i+1} partitions is best.

Some notes on the paper:

    the calculation at every step is really whether the delta Q is better if the 
    "next" went in it's own thing or went up to all the previous
    can we improve this?

    each include/exclude decision is purely made on a binary yes/no
        each include of a vertex u in the neighbourhood of i add 1/m
        each include of a vertex u adds [ out(i) * in(u) + in(i) * out(u) ] / m^2
            i.e. it's m > out(i) * in_sum(u) + in(i) * out_sum(u)
            otherwise its solo.

    so really we should be going forward with a memo array to vastly reduce calculation steps.
    
    However, after analysing the algorithm the clusters are order dependent:
        Consider a DAG rooted of two diamonds, the left of size 2, the right of size n. i.e
                           ------------   1 ----------------------
                         /           /               \ \ ... \ ... \
                        2           3                5 6 ... 5+i ... 5+n-1
                        \         /                   \ \    |      /
                            4                            5+n   5+n+1  

        With topological order 5+n+1 < 5+n < 4 < 3 < 5 < 6 < ... < 5+n-1 < 2 < 1
        note than when considered vertex 4 and 2 are in the same cluster then
        => m > out(4) * in_[sum u](u) + in(4) * out_[sum u](u) 
        => m > 2 * out_[sum u](u) 

        note that m = 3 * n + 4 and each 5,6...5+n-1 has out degree 2, and 3 has out degree 1

        => 3n + 4 > 2 * (2 * n + 1)
        => 3n + 4 > 4n + 2
        which is false for n >= 2, but for many other orderings (notably) 4, 3, 2 ... the 4 and 2 are in the same cluster.
        

This one deals with the order somewhat but at a skim read seems too slow 
    (essentially does the above and then loops over all clusters checking if merging improves value)

The paper itself is frustratingly vague about the specifics of the algorithm which is a shame because it seems to work relatively quickly

https://www.grad.hr/crocodays/proc_ccd2/antunovic_final.pdf

    TODO: implement above algorithm to test speed at larger instances to see if advanced version (order accounting ver) 
        is worth it to implement to test

    Running the algorithm is relatively quick 0.6s for revealO0

-----------------------------------------------------------------------------------------------------------------------------------

https://dial.uclouvain.be/memoire/ucl/en/object/thesis%3A8207/datastream/PDF_01/view

This thesis also provides a good overview of clustering techniques on directed graphs

"""
from typing import List, Set, Dict
from functools import reduce
from collections import deque
import itertools

from r1cs_scripts.circuit_representation import Circuit
from r1cs_scripts.constraint import Constraint

from comparison.static_distance_preprocessing import _distances_to_signal_set

from structural_analysis.graph_clustering.clustering_from_list import UnionFind
from structural_analysis.graph_clustering.degree_clustering import _signal_data_from_cons_list
from structural_analysis.graph_clustering.modularity_optimisation import directed_add_resistance, directed_calculate_mod_change, directed_get_adjacent_to, directed_inner_update_adjacency, directed_outer_update_adjacency

def getvars(con: Constraint) -> set:
    return set(con.A.keys()).union(con.B.keys()).union(con.C.keys()).difference(set([0]))
    

def constraint_topological_order(circ: Circuit, unweighted: bool = False):
    """
    given a circuit, returns a topological order and in and out neighbourhoods for each vertex

    NOTE: 
        in and out neighbours will be the same for equivalent circuits
        topological order will be a valid topological order for the DAG defined by the previous but is not consistent
    
    TODO:
        maybe add weights to flow into modularity stuff easier -- or at least option for weights
    """

    _, signal_to_coni = _signal_data_from_cons_list(circ.constraints)

    # outputs = range(1, circ.nPubOut+1)
    # distances_to_output = _distances_to_signal_set(circ.constraints, outputs, signal_to_coni)

    inputs = range(circ.nPubOut+1, circ.nPubOut + circ.nPrvIn + circ.nPubIn + 1)
    distances_to_input = _distances_to_signal_set(circ.constraints, inputs, signal_to_coni)

    # get distances, to give each constraint a tuple (x_1, x_2..., x_n) where each x_i is the distance of signal i in coni. this is sorted

    # NOTE: interestingly, this more comprehensive order makes the speed_priority version way slower on reveal... why?
        # more unique distances means more edges ~ 20K more which makes it take longer
    coni_to_distances = list(map(
            lambda coni : sorted(map(lambda sig : distances_to_input[sig], getvars(circ.constraints[coni]))), 
            range(circ.nConstraints)
        ))

    ## With a strict layering order we keep any edges between constraints of different layers
    in_neighbours = [{} for _ in range(circ.nConstraints)]
    out_neighbours = [{} for _ in range(circ.nConstraints)]

    # NOTE: reversed order provided consistently better results
    topological_order = sorted(range(circ.nConstraints),key = lambda coni: coni_to_distances[coni])

    for coni in topological_order:

        adjacent_coni = reduce(
            lambda acc, x: acc.union(signal_to_coni[x]),
            getvars(circ.constraints[coni]),
            set([])
        )

        is_strictly_higher = lambda oconi : coni_to_distances[oconi] > coni_to_distances[coni]
        is_strictly_lower = lambda oconi : coni_to_distances[oconi] < coni_to_distances[coni]

        for func, dict_ in [(is_strictly_higher, in_neighbours), (is_strictly_lower, out_neighbours)]:
            for oconi in filter(func, adjacent_coni):
                dict_[coni][oconi] = dict_[coni].setdefault(oconi, 0) + 1
    
    if unweighted:
        in_neighbours = [list(in_neighbours[v].keys()) for v in range(circ.nConstraints)]
        out_neighbours = [list(out_neighbours[v].keys()) for v in range(circ.nConstraints)]

    return topological_order, in_neighbours, out_neighbours

def order_to_clusters(clusters: List[int], order: List[int]):
    actual_clusters = []

    for i in range(1, len(clusters)):

        start, end = clusters[i-1], clusters[i]

        actual_clusters.append([order[pos] for pos in range(start,end)])
    
    return actual_clusters

def dag_clustering_from_order(topological_order: List[int], in_neighbours: List[Set[int]], out_neighbours: List[Set[int]], resolution: int = 1):
    """
    Algorithm takes O(n^2 * max_degree) time.

    DAG clustering as actually works in the examples provided

    TODO: doesn't line up with the example.
        Clusters the example directed graph [1, 2, 3, 4], [5, 6] instead of [1,2,3], [4,5,6]
        Since example does not list \Delta Q_d and no other examples are provided (results networks not given)
        I have no way to confirm if the authors have made an error or I've misinterpreted something about the process...
    
    Testing shows this being relatively slow but stable on tested circuits, though this is not always true (see above)
    """

    # num_edges
    m = sum(map(len, in_neighbours))

    # coni_to_label[k][coni] = label of coni for optimal k
    coni_to_order = [None for _ in range(len(topological_order))]
    for i in range(len(topological_order)): coni_to_order[topological_order[i]] = i

    # final element always in own cluster
    pos_to_curr_modularity = [None for _ in range(len(topological_order) - 1)] + [0]
    pos_to_best_modularity = [None for _ in range(len(topological_order) - 1)] + [0, 0]
    pos_to_best_clusters = [None for _ in range(len(topological_order) - 1)] + [len(topological_order)-1]

    # TODO: we can get upper bounds on Delta, then we can keep r_k + pos_to_curr sorted and abort the search once its no longer possible?
    #       working_cluster_curr_modularity still can't be calculated then?
    #       maybe ignore working_cluster_curr_modularity and the paper example behviour
    for pos in range(len(topological_order)-2, -1, -1):

        coni = topological_order[pos]

        in_coni = len(in_neighbours[coni])
        out_coni = len(in_neighbours[coni])

        neighbourhood = in_neighbours[coni].union(out_neighbours[coni])

        # base choice is entirely new cluster: modularity is previous modularity

        best_modularity = pos_to_best_modularity[pos + 1]
        best_stopping = pos

        current_modularity_change = 0

        for opos in range(pos+1, len(topological_order)):
            
            optimal_modularity_for_rest = pos_to_best_modularity[opos+1]
            working_cluster_curr_modularity = pos_to_curr_modularity[opos]

            # modularity change for cluster of pos
            current_modularity_change -= resolution * (in_coni * len(out_neighbours[topological_order[opos]]) + out_coni * len(in_neighbours[topological_order[opos]]))
            
            # TODO: improve this check
            if topological_order[opos] in neighbourhood:
                current_modularity_change += m

            pos_to_curr_modularity[opos] = working_cluster_curr_modularity + current_modularity_change
            opos_modularity = optimal_modularity_for_rest + working_cluster_curr_modularity + current_modularity_change

            if opos_modularity > best_modularity:
                best_modularity = opos_modularity
                best_stopping = opos

        pos_to_curr_modularity[pos] = 0
        pos_to_best_modularity[pos] = best_modularity
        pos_to_best_clusters[pos]   = best_stopping

    # build clusters from info
    clusters = [0]
    while clusters[-1] < len(topological_order):
        clusters.append(pos_to_best_clusters[clusters[-1]]+1)

    return order_to_clusters(clusters, topological_order)

