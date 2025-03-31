import networkx as nx
import itertools
import math
import numpy as np

def louvain_ex_comm(G, resolution, n_communities):
    pass



def iterated_louvain(G: nx.Graph, max_iterations: int = 100, init_resolution: int = 1, res_tolerance: float = 1.0, seed : int | None = None):

    RNG = np.random.RandomState(seed)

    res = init_resolution
    for niter in range(max_iterations):

        partition = nx.algorithms.community.louvain_communities(G, resolution=res, seed=RNG.randint(25565))

        # edges in is doubled but doubled in equation so unfixed
        edges_in = 0
        twice_edges = G.number_of_edges() * 2
        degree_sq_sum = 0
        
        for part in partition:

            in_pair = {v : True for v in part}
            degree_sq_sum += sum(map(len, map(G.adj.__getitem__, part)))**2

            edges_in += sum(1 for _ in filter(lambda ov : in_pair.setdefault(ov, False), itertools.chain(*map(lambda v : G.adj[v].keys() , part))))

        omega_in = edges_in * (twice_edges / degree_sq_sum)
        omega_out = (twice_edges - edges_in) / (twice_edges - degree_sq_sum / twice_edges)
    
        newres = (omega_in - omega_out) / (math.log(omega_in) - math.log(omega_out))

        if abs(res - newres) < res_tolerance: break
        res = newres

    return partition, res