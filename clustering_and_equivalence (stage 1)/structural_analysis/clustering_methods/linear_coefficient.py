from typing import Iterable, List, Tuple
import itertools

from utilities.utilities import getvars, _signal_data_from_cons_list, UnionFind

from r1cs_scripts.circuit_representation import Circuit
from r1cs_scripts.constraint import Constraint

from structural_analysis.clustering_methods.naive.clustering_from_list import cluster_by_ignore, IgnoreMethod

def cluster_by_linear_coefficient(circ: Circuit, coefs: Iterable[int] = [1, -1], **clustering_kwargs):
    """
    Clustering Method

    An attempt at a more general linear coefficient clustering method. Currently, the process is too eager to mark constraints as
    bridge constraints, additionally it has memory issues that cause problems for larger circuits.

    Process
    --------
        step 1: 
            split naively as before (w/ x = y constraints)

        step 2: 
            find candiate signal/constraint pairs
                must have coef in coefs in the C part of the constraint
                must not be previous

        step 3: 
            for each candidate pair, check if internal signal path is reachable through only noncandidates
                if yes, remove candidate - if no candidates for constraint make constraint noncandidate
                if no, continue
        
        step 4: 
            split on candidates too

    Parameters
    ---------
        circ: Circuit
            The input circuit to be clustered
        clusters: Iterable[int]
            The coefficients that define the pattern matching for what a candidate signal is
        clustering_kwargs
            kwargs passed to `cluster_by_ignore`
    
    Returns
    ---------
    (clusters, adjacency, removed)
        cluster: Dict[int, List[int]]
            Partition of the input graph given by connected components. Clusters are indexed by an arbitrary element of the cluster. 
            Dictionary used to later be able to remove and reindex elements without remapping indices.

        adjacency: Dict[int, List[int]]
            Maps cluster index to adjacent cluster indices. Empty if calculate_adjacency is False

        removed: List[int]
            List of removed constraints. Always equivalent to ignore_func
    """
    coefs = list(map(lambda x : x % circ.prime_number, coefs))

    # Step 1

    def _assumed_link_constraint(con: Constraint) -> bool:
        if not (len(con.A) == len(con.B) == 0): return False
        vars = getvars(con)
        if len(vars) != 2 or any(map(lambda sig : con.C[sig] not in coefs, vars)): return False
        return True
    
    removed, leftovers = [], []
    for coni, con in enumerate(circ.constraints): (removed if _assumed_link_constraint(con) else leftovers).append(coni)
    
    leftovers = set(range(circ.nConstraints)).difference(removed)
    noncandidates, candidates = [], []

    def _is_candidate_constraint(coni: int) -> bool:
        # any coni with a candidate signal is a candidate constraint
        for sig, value in filter(lambda tup: tup[0] != 0 and tup[1] in coefs, circ.constraints[coni].C.items()):
            return True
        return False 
    
    for coni in leftovers: (candidates if _is_candidate_constraint(coni) else noncandidates).append(coni)
    
    noncandidate_uf = UnionFind()
    for coni in noncandidates: noncandidate_uf.union(*getvars(circ.constraints[coni]))

    def _get_candidate_pairs(coni: int) -> List[Tuple[int, int]]:
        return list(itertools.product([coni],
            filter(lambda sig : sig != 0 and circ.constraints[coni].C[sig] in coefs, circ.constraints[coni].C.keys())))

    # if taking too long refactor so only loops once
    candidate_pair_not_in_queue = {}
    signal_to_candidate_coni = {}
    coni_to_num_candidates = {}
    pipe = []

    for coni, sig in itertools.chain(*map(_get_candidate_pairs, candidates)):
        signal_to_candidate_coni.setdefault(sig, set([])).add(coni) # slow..
        coni_to_num_candidates[coni] = coni_to_num_candidates.setdefault(coni, 0) + 1
        
        candidate_pair_not_in_queue[(coni, sig)] = False # TODO: to more A/B testing for speed here
        pipe.append((coni, sig))

    while len(pipe) > 0:
        coni, sig = pipe.pop()

        candidate_pair_not_in_queue[(coni, sig)] = True
        if coni_to_num_candidates[coni] == 0: continue

        # If there is any other signal in the bridge constraint that can reach the candidate signal via another means 
        #   (i.e. in same noncandidate cluster). Then that isn't a candidate signal and we can remove it from the options
        if any(map(lambda osig : sig != osig and noncandidate_uf.find(sig) == noncandidate_uf.find(osig), getvars(circ.constraints[coni]))):
            coni_to_num_candidates[coni] -= 1
            signal_to_candidate_coni[sig].remove(coni)

            # if the candidate has no more candidate signals it is no longer a candidate signal
            if len(signal_to_candidate_coni[sig]) == 0: del signal_to_candidate_coni[sig]

            if coni_to_num_candidates[coni] == 0:
                noncandidate_uf.union(*getvars(circ.constraints[coni]))

                candidates_to_add = list(filter(candidate_pair_not_in_queue.__getitem__, itertools.chain(
                    *map( lambda osig : itertools.product(signal_to_candidate_coni[osig], [osig]),
                    filter(lambda osig : noncandidate_uf.find(sig) == noncandidate_uf.find(osig), signal_to_candidate_coni.keys())
                    ))))

                # check any candidate pairs that have been merged
                for p in candidates_to_add: candidate_pair_not_in_queue[p] = False
                pipe.extend(candidates_to_add)

    links = list(filter(lambda coni : coni_to_num_candidates[coni] > 0, coni_to_num_candidates.keys()))
    return cluster_by_ignore(circ, IgnoreMethod.ignore_constraint_from_list, removed + links, **clustering_kwargs)
