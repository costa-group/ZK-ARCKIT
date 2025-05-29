"""

get nonlinear cores -- UnionFind

-- prev: all pairs -- cant do that n^2 way too slow
    -- take one and go to each is much faster but can't take arbitrary cos they might not be equivalent
    -- custom convex bound? if any nonlinears in backset remove them from consideration and then try reach next set? -- how?

-- test how big the classes are and just encode into MAXSAT to see if its feasible without better fingerprinting?

minimum spanning tree - prim/kruskal O(m log n)

then go back and do all shortest paths for each edge.

seems bad --

enforce nonlinears -- 

"""

from typing import List, Dict, Tuple, Set
import itertools

from r1cs_scripts.circuit_representation import Circuit
from r1cs_scripts.constraint import Constraint
from utilities.utilities import _signal_data_from_cons_list, UnionFind, getvars

def _is_nonlinear(con: Constraint) -> bool:
        return len(con.A) > 0 and len(con.B) > 0

def get_nonlinar_cores(circ: Circuit, constraints: List[int], sig_to_coni: Dict[int, List[int]]) -> Dict[int, List[int]]:
    # Step 1: place adjacent nonlinears into a cluster
    coni_to_adjacent_coni = lambda coni : set(filter(lambda oconi: oconi != coni, itertools.chain(*map(sig_to_coni.__getitem__, getvars(circ.constraints[coni])))))
    
    nonlinear_clusters = UnionFind()

    # NOTE: we do not want only nonlinear clusters so we merge the first adjacency of linear clusters as well
    for coni in filter(lambda coni : _is_nonlinear(circ.constraints[coni]), constraints):
        nonlinear_clusters.union(coni, *filter(lambda oconi : _is_nonlinear(circ.constraints[oconi]), coni_to_adjacent_coni(coni)) )
            
    clusters = {}
    for coni in nonlinear_clusters.parent.keys():
        clusters.setdefault(nonlinear_clusters.find(coni), []).append(coni)
    
    return clusters

def all_shortest_paths(circ: Circuit, S: List[int], T: List[int], sig_to_coni:Dict[int, List[int]]) -> Tuple[int, List[int]]:
    
    coni_to_adjacent_coni = lambda coni : set(filter(lambda oconi: oconi != coni, itertools.chain(*map(sig_to_coni.__getitem__, getvars(circ.constraints[coni])))))
    
    backset = {}
    reached = {} # default False
    pushed = {} # default False

    for s in S: reached[s], pushed[s] = True, True

    dist = 0

    next_round = []
    current_round = [s for s in S]

    # find T
    while all(map(lambda coni: reached.setdefault(coni, False) == False, T)):
        dist += 1

        while len(current_round) > 0:
            curr = current_round.pop()

            adj_unreached = list(filter(lambda coni : reached.setdefault(coni, False) == False, coni_to_adjacent_coni(curr)))
            next_round.extend(filter(lambda coni : pushed.setdefault(coni, False) == False, adj_unreached))

            for adj in adj_unreached: 
                backset.setdefault(adj, []).append(curr)
                pushed[adj] = True

        for coni in next_round: reached[coni] = True
        next_round, current_round = [], next_round
    
    # get backset
    marked = {} # default False 
    for t in T: marked[t] = True
    backlist = list(T)

    next_round = []
    current_round = list(T)

    while all(map(lambda coni: marked.setdefault(coni, False) == False, S)):
        next_round = set(filter(lambda coni : marked.setdefault(coni, False) == False, itertools.chain(*map(backset.__getitem__, current_round))))
        backlist.extend(next_round)
        for coni in next_round: marked[coni] = True
        next_round, current_round = [], next_round
    
    backlist.extend(filter(lambda coni : marked.setdefault(coni, False) == False, S))
    return dist, backlist

def coreless_components(circ: Circuit, constraints: List[int], cores: Dict[int, List[int]], sig_to_coni: Dict[int, List[int]]) -> List[int]:
    coni_to_adjacent_coni = lambda coni : set(filter(lambda oconi: oconi != coni, itertools.chain(*map(sig_to_coni.__getitem__, getvars(circ.constraints[coni])))))

    def _is_linear(con: Constraint) -> bool:
        return not _is_nonlinear(con)
    
    linear_clusters = UnionFind()

    # NOTE: we do not want only nonlinear clusters so we merge the first adjacency of linear clusters as well
    for coni in filter(lambda coni : _is_linear(circ.constraints[coni]), constraints):
        linear_clusters.union(coni, *filter(lambda oconi : _is_linear(circ.constraints[oconi]), coni_to_adjacent_coni(coni)) )
            
    clusters = {}
    for coni in linear_clusters.parent.keys():
        clusters.setdefault(linear_clusters.find(coni), []).append(coni)

    nonlinear_to_core = {}
    for key, core in cores.items(): 
        for coni in core: nonlinear_to_core[coni] = key

    equiv_core = list(itertools.chain(*cores.values()))
    
    for key, cluster in clusters.items():
        adj_core = set(map(nonlinear_to_core.__getitem__, filter(lambda coni: _is_nonlinear(circ.constraints[coni]), itertools.chain(*map(coni_to_adjacent_coni, cluster)))))
        if len(adj_core) > 1: equiv_core.extend(cluster)
    
    return equiv_core


def shortest_minimum_span(circ: Circuit, constraints: List[int], signals: List[int]) -> List[int]:
    sig_to_coni = _signal_data_from_cons_list(map(circ.constraints.__getitem__, constraints), names=constraints)

    # get nonlinear cores
    cores = get_nonlinar_cores(circ, constraints, sig_to_coni = sig_to_coni)

    if len(cores) < 2:
        return constraints
    
    # TODO: think of a way to get around n^2
    # instead of all shortes
    equiv_core = coreless_components(circ, constraints, cores, sig_to_coni)
    return equiv_core
    # find minimum spanning tree

    # return union