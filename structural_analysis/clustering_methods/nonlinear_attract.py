from typing import Iterable, List, Tuple, Dict, Set
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
    coni_to_adjacent_coni = lambda coni : set(filter(lambda oconi: oconi != coni, itertools.chain(*map(sig_to_coni.__getitem__, getvars(circ.constraints[coni])))))

    def _is_nonlinear(con: Constraint) -> bool:
        return len(con.A) > 0 and len(con.B) > 0
    
    nonlinear_clusters = UnionFind()

    for coni in filter(lambda coni : _is_nonlinear(circ.constraints[coni]), range(circ.nConstraints)):
        nonlinear_clusters.union(coni, *filter(lambda oconi : _is_nonlinear(circ.constraints[oconi]), coni_to_adjacent_coni(coni)) )
    
    clusters = {}
    for coni in nonlinear_clusters.parent.keys():
        clusters.setdefault(nonlinear_clusters.find(coni), []).append(coni)
    
    adjacent_nonlinear = {}
    for key, cluster in clusters.items():
            adjacent_nonlinear[key] = set(
                itertools.chain(
                *map(
                    lambda coni : filter(lambda oconi : not _is_nonlinear(circ.constraints[oconi]) and 
                        nonlinear_clusters.find(oconi) == oconi, coni_to_adjacent_coni(coni)),
                    cluster
                )
            ))
    
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
            adjacent_nonlinear.setdefault(key, set([])).update(filter(lambda oconi : not _is_nonlinear(circ.constraints[oconi]) and nonlinear_clusters.find(oconi) == oconi, coni_to_adjacent_coni(coni)))

    return clusters, None, None

