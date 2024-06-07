import itertools
import networkx as nx


def HCS(G: nx.Graph) -> nx.Graph:

    cut = nx.algorithms.connectivity.minimum_edge_cut(G)

    if len(cut) > G.number_of_nodes() // 2:
        return G
    else:
        G_ = G.copy()
        G_.remove_edges_from(cut)

        # min-cut always returns 2 connected components
        subgraphs = [G_.subgraph(component) for component in nx.connected_components(G_)]
        subgraphs = [HCS(H) for H in subgraphs]

        return nx.compose(*subgraphs)
