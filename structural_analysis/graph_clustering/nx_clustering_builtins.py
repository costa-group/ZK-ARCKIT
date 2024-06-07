import networkx as nx
from typing import List


def induce_on_partitions(G: nx.Graph, partitions: List["Node"]):
    G_ = nx.Graph()

    for partition in partitions:
        G_.add_edges_from( G.subgraph(partition).edges() )

    return G_


def Louvain(G: nx.Graph, graph: bool = False, seed=None):
    partitions = nx.community.louvain_communities(G, seed=seed)
    if graph: return induce_on_partitions(G, partitions)
    else: return partitions

def Label_propagation(G: nx.Graph, graph: bool = False, seed=None):
    partitions = nx.community.asyn_lpa_communities(G, seed=seed)
    if graph: return induce_on_partitions(G, partitions)
    else: return partitions