import networkx as nx
from typing import List


def induce_on_partitions(G: nx.Graph, partitions: List["Node"]):
    G_ = nx.Graph()

    for partition in partitions:
        G_.add_edges_from( G.subgraph(partition).edges() )

    return G_


def Louvain(G: nx.Graph):

    return induce_on_partitions(G, nx.community.louvain_communities(G))

def Label_propagation(G: nx.Graph, seed=None):

    return induce_on_partitions(G, nx.community.asyn_lpa_communities(G, seed=seed))