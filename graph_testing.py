if __name__ == '__main__':
    import networkx as nx
    import time
    from functools import reduce
    from itertools import product

    from utilities import count_ints, getvars
    from comparison_testing import get_circuits
    from r1cs_scripts.circuit_representation import Circuit
    from r1cs_scripts.read_r1cs import parse_r1cs
    from comparison.cluster_preprocessing import groups_from_clusters, circuit_clusters
    from structural_analysis.connected_preprocessing import connected_preporcessing
    # from structural_analysis.signal_graph import shared_constraint_graph
    # from structural_analysis.connected_preprocessing import connected_preporcessing
    # from structural_analysis.constraint_graph import shared_signal_graph
    # from structural_analysis.graph_clustering.HCS_clustering import HCS
    # from structural_analysis.graph_clustering.nx_clustering_builtins import *
    # from structural_analysis.graph_clustering.stepped_girvan_newman import stepped_girvan_newman
    # from structural_analysis.graph_clustering.signal_equivalence_clustering import naive_removal_clustering
    # from structural_analysis.graph_clustering.degree_clustering import twice_average_degree, ratio_of_signals
    # from structural_analysis.graph_clustering.topological_flow_clustering import circuit_topological_clusters, constraint_topological_order, dag_clustering_from_order, dag_cluster_speed_priority, dag_cluster_and_merge, dag_strict_order_clustering
    # from structural_analysis.graph_clustering.modularity_optimisation import undirected_adjacency, stable_directed_louvain, stable_undirected_louvain
    # from structural_analysis.graph_clustering.spectral_clustering import spectral_undirected_clustering
    from structural_analysis.cluster_trees.tree_wrapper import O0_tree_clustering

    filename = "r1cs_files/RevealO0.r1cs"

    circ = Circuit()
    parse_r1cs(filename, circ)
    connected_preporcessing(circ)

    start = time.time()
    O0_tree_clustering(circ, outfile = "test.json")
    print(time.time() - start)


    
    