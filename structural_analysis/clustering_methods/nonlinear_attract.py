from typing import Iterable, List, Tuple
import itertools

from utilities import UnionFind, _signal_data_from_cons_list, getvars
from r1cs_scripts.circuit_representation import Circuit
from r1cs_scripts.constraint import Constraint

def nonlinear_attract_clustering(circ: Circuit):
    """
    
    step 1 : place adjacent nonlinears into a cluster
    step 2 : iteratively check adjacent constraints
        - if cons adjacent to only cluster then attract
        - otherwise leave alone
    
    ?? 
    """

    sig_to_coni = _signal_data_from_cons_list(circ.constraints)
    coni_to_adjacent_coni = lambda coni : set(itertools.chain(*map(sig_to_coni.__getitem__, getvars(circ.constraints[coni])))).difference([coni])

    def _is_nonlinear(con: Constraint) -> bool:
        return len(con.A) > 0 and len(con.B) > 0
    
    nonlinear_clusters = UnionFind()

    for coni, _ in filter(lambda tup : _is_nonlinear(tup[1]), enumerate(circ.constraints)):
        nonlinear_clusters.union(coni, *filter(lambda oconi : _is_nonlinear(circ.constraints[oconi]), coni_to_adjacent_coni(coni)) )
    
    clusters = {}
    for coni in nonlinear_clusters.parent.keys():
        clusters.setdefault(nonlinear_clusters.find(coni), []).append(coni)
    
    adj_coni = {}
    for key, cluster in clusters.items():
        adj_coni[key] = set(itertools.chain(
            *map(
                lambda coni : filter(lambda oconi : nonlinear_clusters.find(oconi) == oconi, coni_to_adjacent_coni(coni)),
                cluster
            )
        ))
    
    updated = True
    while updated:

        adjacent_to = {}

        for key, adjacencies in adj_coni.items():
            for coni in adjacencies:
                adjacent_to.setdefault(coni, []).append(key)
        
        adj_coni = {}

        for key in adj_coni.keys():
            adj_coni[key].difference_update(adjacent_to.keys())

        to_attract = list(filter(lambda key : len(adjacent_to[key]) == 1, adjacent_to.keys()))
        updated = len(to_attract) > 0

        # need to do this first for consistency
        for coni in to_attract:
            nonlinear_clusters.union(coni, adjacent_to[coni][0])
        
        for coni in to_attract:
            clusters[adjacent_to[coni][0]].append(coni)
            adj_coni[adjacent_to[coni][0]] = set(filter(lambda oconi : nonlinear_clusters.find(oconi) == oconi, coni_to_adjacent_coni(coni)))
    
    return clusters, None, None

