import itertools
import networkx as nx

def HCS_recursion(G: nx.Graph) -> nx.Graph:
    cut = nx.algorithms.connectivity.minimum_edge_cut(G)

    if len(cut) == 0 or len(cut) > G.number_of_nodes() // 2:
        return G
    else:
        G_ = G.copy()
        G_.remove_edges_from(cut)

        # min-cut always returns 2 connected components
        subgraphs = [G_.subgraph(component) for component in nx.connected_components(G_)]
        subgraphs = [HCS_recursion(H) for H in subgraphs]

        return nx.compose(*subgraphs)

def HCS_norecursion(G: nx.Graph) -> nx.Graph:
    G_ = G.copy()

    stack = [G_.nodes()]

    while len(stack) > 0:

        nodes = stack.pop()
        H = G_.subgraph(nodes)

        cut = nx.algorithms.connectivity.minimum_edge_cut(H)

        if len(cut) > 0 and len(cut) <= H.number_of_nodes() // 2:

            G_.remove_edges_from(cut)
            H = G_.subgraph(nodes)

            stack += list(nx.connected_components(H))
    
    return G_

def HCS(G: nx.Graph, recursion: bool = False):
    return HCS_recursion(G) if recursion else HCS_norecursion(G)
