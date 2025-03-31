"""

Functions that call networkx community finding algorithms. Each either returns the partitions or the subgraph.

"""

import networkx as nx
from typing import List


def induce_on_partitions(G: nx.Graph, partitions: List["Node"]):
    "Given an input graph returns the composition of the induced subgraphs for each part"
    G_ = nx.Graph()

    for partition in partitions:
        G_.add_edges_from( G.subgraph(partition).edges() )

    return G_

def Louvain(G: nx.Graph, graph: bool = False, seed=None):
    """see nx.community.louvain_communities
    
    https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.community.louvain.louvain_communities.html"""
    partitions = nx.community.louvain_communities(G, seed=seed)
    if graph: return induce_on_partitions(G, partitions)
    else: return partitions

def Label_propagation(G: nx.Graph, graph: bool = False, seed=None):
    """see nx.community.asyn_lpa_communities
    
    https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.community.label_propagation.asyn_lpa_communities.html"""
    partitions = nx.community.asyn_lpa_communities(G, seed=seed)
    if graph: return induce_on_partitions(G, partitions)
    else: return partitions