from typing import Iterable, List, Tuple, Dict, Set
import itertools

from utilities.utilities import UnionFind, _signal_data_from_cons_list
from circuits_and_constraints.abstract_circuit import Circuit
from circuits_and_constraints.abstract_constraint import Constraint

def nonlinear_attract_clustering(circ: Circuit, pre_merge: bool = False):
    """
    Clustering Method

    Process
    --------
        step 1:
            place adjacent nonlinears into a cluster
        step 2: 
            iteratively check adjacent constraints
            if cons adjacent to only cluster then attract
            otherwise leave alone
    
    To Improve
    --------
        non-adjacent nonlinear can never be in the same class
        leads to very small clusters typically
        need to think of some point at which we can merge clusters
        TODO: for large circuits like test_ecdsa, nonlinear attract seems to have lower quality clusters (one very big cluster)

    Parameters
    ----------
        circ: Circuit
            the input circuit to cluster
    
    Returns
    ----------
    (Dict[int, List[int]], None, None)
        The clusters in dictionary form and 2 None object to keep the same number of returns as previous Clustering Methods
    """

    # Step 1: place adjacent nonlinears into a cluster
    sig_to_coni = _signal_data_from_cons_list(circ.constraints)
    coni_to_adjacent_coni = lambda coni : set(filter(lambda oconi: oconi != coni, itertools.chain(*map(sig_to_coni.__getitem__, circ.constraints[coni].signals()))))
    
    nonlinear_clusters = UnionFind()

    # NOTE: we do not want only nonlinear clusters so we merge the first adjacency of linear clusters as well
    for coni in filter(lambda coni : circ.constraints[coni].is_nonlinear(), range(circ.nConstraints)):
        if pre_merge:
            nonlinear_clusters.parent[coni] = -2 # hack to ensure no linear cluster indexes
            nonlinear_clusters.union(coni, *coni_to_adjacent_coni(coni))
        else:
            nonlinear_clusters.union(coni, *filter(lambda oconi : circ.constraints[oconi].is_nonlinear(), coni_to_adjacent_coni(coni)) )
            
    clusters = {}
    for coni in nonlinear_clusters.parent.keys():
        clusters.setdefault(nonlinear_clusters.find(coni), []).append(coni)
    
    # Step 1.5: calculate nonlinear cluster adjacency
    adjacent_nonlinear = {}
    for key, cluster in clusters.items():
            adjacent_nonlinear[key] = set(
                itertools.chain(
                *map(
                    lambda coni : filter(lambda oconi : ( not circ.constraints[oconi].is_nonlinear() ) and 
                        nonlinear_clusters.find(oconi) == oconi, coni_to_adjacent_coni(coni)),
                    cluster
                )
            ))

    # Step 2: repeatedly check if any adjacent vertices are only adjacent to 1 cluster. If so, attract them to that cluster and 
    #   adjust the adjacency values as required.
    updated = True
    while updated:

        adjacent_to = {}

        for key, adjacencies in adjacent_nonlinear.items():
            for coni in adjacencies:
                adjacent_to.setdefault(coni, []).append(key)

        to_attract = list(filter(lambda key : len(adjacent_to[key]) == 1, adjacent_to.keys()))
        updated = len(to_attract) > 0

        adjacent_nonlinear = {}

        # need to do this first for consistency
        for coni in to_attract:
            nonlinear_clusters.parent[coni] = adjacent_to[coni][0]

        for coni in to_attract:
            key = adjacent_to[coni][0]
            clusters[key].append(coni)
            adjacent_nonlinear.setdefault(key, set([])).update(filter(lambda oconi : ( not circ.constraints[oconi].is_nonlinear() ) and nonlinear_clusters.find(oconi) == oconi, coni_to_adjacent_coni(coni)))

    return clusters, None, None

