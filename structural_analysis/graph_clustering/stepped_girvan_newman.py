import networkx as nx
from typing import Callable, Iterable

def _get_next_edges(G: nx.graph, etol: float) -> Iterable["edge"]:

    data = nx.edge_betweenness_centrality(G, k = None)

    max_prop = max(data.values())

    return filter(lambda e : abs(data[e] - max_prop) <= etol, data.keys())


def stepped_girvan_newman(G: nx.Graph, cluster_limit: Callable[[nx.Graph],int] = None):
    if cluster_limit is None: cluster_limit = lambda g : g.number_of_nodes()**(0.5) 
    limit = cluster_limit(G)

    partitions = []

    G_ = G.copy()

    while len(partitions) < limit:
        # print(len(partitions), G.number_of_nodes()**(0.5))

        edges_with_max_prop = _get_next_edges(G_)

        G_.remove_edges_from(edges_with_max_prop)

        partitions = list(nx.connected_components(G_))
    
    return partitions
