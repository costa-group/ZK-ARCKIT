if __name__ == '__main__':
    import networkx as nx
    import numpy as np
    import time
    import json
    import os
    from functools import reduce
    from itertools import product

    from utilities import count_ints, getvars, UnionFind, _signal_data_from_cons_list
    from comparison_testing import get_circuits
    from r1cs_scripts.circuit_representation import Circuit
    from r1cs_scripts.read_r1cs import parse_r1cs
    from comparison.cluster_preprocessing import groups_from_clusters, circuit_clusters
    from structural_analysis.utilities.connected_preprocessing import connected_preprocessing, componentwise_preprocessing
    from structural_analysis.utilities.signal_graph import shared_constraint_graph
    from structural_analysis.utilities.graph_to_img import partition_graph_to_img
    # from structural_analysis.connected_preprocessing import connected_preporcessing
    from structural_analysis.utilities.constraint_graph import shared_signal_graph
    # from structural_analysis.graph_clustering.HCS_clustering import HCS
    # from structural_analysis.graph_clustering.nx_clustering_builtins import *
    # from structural_analysis.graph_clustering.stepped_girvan_newman import stepped_girvan_newman
    from structural_analysis.clustering_methods.naive.signal_equivalence_clustering import naive_removal_clustering, nonorm_relaxes_signal_equivalence_constraint
    # from structural_analysis.graph_clustering.degree_clustering import twice_average_degree, ratio_of_signals
    # from structural_analysis.graph_clustering.topological_flow_clustering import circuit_topological_clusters, constraint_topological_order, dag_clustering_from_order, dag_cluster_speed_priority, dag_cluster_and_merge, dag_strict_order_clustering
    # from structural_analysis.graph_clustering.modularity_optimisation import undirected_adjacency, stable_directed_louvain, stable_undirected_louvain
    # from structural_analysis.graph_clustering.spectral_clustering import spectral_undirected_clustering
    from structural_analysis.cluster_trees.tree_wrapper import O0_tree_clustering
    from structural_analysis.cluster_trees.r1cs_tree import r1cs_distance_tree
    from structural_analysis.clustering_methods.linear_coefficient import cluster_by_linear_coefficient
    from structural_analysis.cluster_trees.r1cs_O0_rooting import r1cs_O0_rooting
    from structural_analysis.cluster_trees.node_signals import node_signals
    from structural_analysis.clustering_methods.nonlinear_attract import nonlinear_attract_clustering

    def recursive_search(path):
        for opt in map(lambda opt : path + "/" + opt, os.listdir(path)):
            if ".r1cs" in opt: yield opt
            elif "." not in opt: 
                for f in recursive_search(opt): yield f

    parent = "clustering_tests/num2bitsandmore"
    # parent = "r1cs_files"
    clustering_method = lambda circ, **kwargs : naive_removal_clustering(circ, ignore_pattern=nonorm_relaxes_signal_equivalence_constraint, **kwargs)

    # TODO: none of the test examples given have any of the structured links we expect ... maybe a zokrates thing?
    #   results in graphs of length 1
    # TODO: improve linear clustering

    # for filename in recursive_search(parent):
    for filename in map(lambda f : "r1cs_files/" + f, ["binsub_test.r1cs", "PoseidonO0.r1cs"]):

        print(filename)

        circ = Circuit()
        try:
            parse_r1cs(filename, circ)
        except:
            continue

        start = time.time()

        # res = circ.nConstraints ** 0.5
        g = shared_signal_graph(circ.constraints)
        # comm = nx.algorithms.community.louvain_communities(g, resolution = res)

        clusters, _, _ = nonlinear_attract_clustering(circ)
        comm = clusters.values()
        
        print("clustering time: ", time.time() - start)

        testname = filename.split("/")[-1]
        file_suffix = "_nonlinear_attract" # f"_Louvain_res=sqrt({circ.nConstraints})"
        outfile = "structural_analysis/clustered_graphs/" + testname[:testname.index(".")] + file_suffix + ".png"

        partition_graph_to_img(circ, g, comm, outfile)

    # def cluster_by_nonlinear_constraints(circ: Circuit):
    #     nonlinear_constraints, removed = [], []
    #     for coni, con in enumerate(circ.constraints):
    #         (nonlinear_constraints if len(con.A) > 0 else removed).append(coni)
    #     nonlinear_uf = UnionFind()
    #     for coni in nonlinear_constraints: nonlinear_uf.find(coni)

    #     signal_to_coni = _signal_data_from_cons_list(circ.constraints)
    #     for complete_graph in signal_to_coni.values():
    #         nonlinear_uf.union(*filter(lambda coni : len(circ.constraints[coni].A) > 0, complete_graph))
        
    #     clusters = {}
    #     for coni in nonlinear_constraints:
    #         clusters.setdefault(nonlinear_uf.find(coni), []).append(coni)
        
    #     return clusters, None, removed
    



    
    