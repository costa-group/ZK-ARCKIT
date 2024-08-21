if __name__ == '__main__':
    import networkx as nx
    import time
    from functools import reduce
    from itertools import product

    from utilities import count_ints
    from comparison_testing import get_circuits
    from r1cs_scripts.circuit_representation import Circuit
    from r1cs_scripts.read_r1cs import parse_r1cs
    from comparison.cluster_preprocessing import groups_from_clusters, circuit_clusters
    from structural_analysis.signal_graph import *
    from structural_analysis.connected_preprocessing import connected_preporcessing
    from structural_analysis.constraint_graph import *
    from structural_analysis.graph_clustering.HCS_clustering import HCS
    from structural_analysis.graph_clustering.nx_clustering_builtins import *
    from structural_analysis.graph_clustering.stepped_girvan_newman import stepped_girvan_newman
    from structural_analysis.graph_clustering.signal_equivalence_clustering import naive_removal_clustering
    from structural_analysis.graph_clustering.degree_clustering import twice_average_degree, ratio_of_signals
    from structural_analysis.graph_clustering.topological_flow_clustering import circuit_topological_clusters, constraint_topological_order, dag_clustering_from_order, dag_cluster_speed_priority, dag_cluster_and_merge, dag_strict_order_clustering
    from structural_analysis.graph_clustering.modularity_optimisation import undirected_adjacency, stable_directed_louvain, stable_undirected_louvain
    from structural_analysis.graph_clustering.spectral_clustering import spectral_undirected_clustering

    filename = "r1cs_files/RevealO1.r1cs"

    circ = Circuit()
    parse_r1cs(filename, circ)

    circ, circs, cmapp = get_circuits(filename, seed=463, return_mapping=False, return_cmapping=True)

    circ = connected_preporcessing(circ)
    circs = connected_preporcessing(circs)

    old_order = None

    in_pair = [("S1", circ), ("S2", circs)]
    clusters = circuit_clusters(in_pair, clustering_algorithm=twice_average_degree)
    groups = groups_from_clusters(in_pair, clusters)

    print(count_ints(map(len, groups["S1"].values())))


    # for c in [circ, circs]:
    #     start = time.time()

    #     clusters, adj, rem = twice_average_degree(c.constraints)

    #     # method = dag_cluster_speed_priority

    #     # clusters, adjacency, removed = circuit_topological_clusters(
    #     #     c,
    #     #     dag_cluster_and_merge,
    #     #     cluster_method = method
    #     # )

    #     # _, in_adj, out_adj = constraint_topological_order(c)
    #     # clusters = stable_directed_louvain(in_adj, out_adj, outer_loop_limit = 1, inner_loop_limit = 3, tolerance=10**(-8), resistance=60, debug=True)

    #     print(count_ints(map(len, clusters.values())), sum(map(len, clusters.values())))
    #     # print(count_ints(map(len, clusters2.values())), sum(map(len, clusters2.values())))
    #     print(time.time() - start)

    # data = constraint_topological_order(circ)
    # clusters = dag_clustering_as_written(*data)

    

    # circ = Circuit()
    
    # filename = "r1cs_files/SudokuO1.r1cs"
    # filename = "r1cs_files/PoseidonO1.r1cs"
    # filename = "r1cs_files/MultiAND.r1cs"
    # filename = "r1cs_files/RevealO1.r1cs"

    # modifiers = ["signal_twice"]

    # parse_r1cs(filename, circ)

    # g = shared_constraint_graph(circ.constraints)
    # print(list(map(len, list(nx.connected_components(g)))))

    # data = constraint_topological_order(circ)
    # clusters = dag_community_detection(circ, *data)
    
    
    # print(clusters)

    # clusters = twice_average_degree(circ.constraints)

    # g = shared_constraint_graph(list(map(
    #     lambda i : circ.constraints[i],
    #     reduce(
    #     lambda acc, x : acc + x,
    #     filter(lambda l : len(l) > 1, clusters),
    #     []
    # ))))

    # nx.nx_pydot.to_pydot(g).write_png(
    #     "structural_analysis" + filename[filename.index('/'):] + "_" * (len(modifiers) > 0) + "_".join(modifiers) +  ".png"
    # )  