import networkx as nx
import numpy as np
from typing import Callable, Iterable, List

def _get_next_edges(G: nx.graph, etol: float, seed = None) -> Iterable["edge"]:
    # floating point errors in python mean we need some error tolerance

    #TODO: think about doing some randomised testing to cut down on time (with error tolerance probably won't change anything -- needs testing)
    #   - preliminary testing didn't look promising
    data = nx.edge_betweenness_centrality(G, k = None , seed = seed)

    max_prop = max(data.values())

    return filter(lambda e : abs(data[e] - max_prop) <= etol, data.keys())

def stepped_girvan_newman(G: nx.Graph, cluster_limit: Callable[[nx.Graph],int] = None, seed = None) -> List[List[int]]:
    if cluster_limit is None: cluster_limit = lambda g : g.number_of_nodes()**(0.5) 
    limit = cluster_limit(G)

    partitions = []

    RNG = np.random.RandomState(seed = seed)

    G_ = G.copy()

    while len(partitions) < limit:

        edges_with_max_prop = _get_next_edges(G_, etol=10**(-6), seed = RNG) # etol chosen heuristically -- empirical data shows differences of ~10**-8

        G_.remove_edges_from(edges_with_max_prop)

        partitions = list(nx.connected_components(G_))
    
    return partitions
