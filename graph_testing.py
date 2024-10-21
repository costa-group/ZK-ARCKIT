if __name__ == '__main__':
    import networkx as nx
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
    from structural_analysis.connected_preprocessing import connected_preprocessing, componentwise_preprocessing
    from structural_analysis.signal_graph import shared_constraint_graph
    # from structural_analysis.connected_preprocessing import connected_preporcessing
    from structural_analysis.constraint_graph import shared_signal_graph
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

    def recursive_search(path):
        for opt in map(lambda opt : path + "/" + opt, os.listdir(path)):
            if ".r1cs" in opt: yield opt
            elif "." not in opt: 
                for f in recursive_search(opt): yield f

    parent = "clustering_tests"
    # parent = "r1cs_files"
    clustering_method = lambda circ, **kwargs : naive_removal_clustering(circ, ignore_pattern=nonorm_relaxes_signal_equivalence_constraint, **kwargs)
    file_suffix = ""

    # TODO: none of the test examples given have any of the structured links we expect ... maybe a zokrates thing?
    #   results in graphs of length 1
    # TODO: improve linear clustering

    # for filename in recursive_search(parent):

    #     print(filename)

    #     circ = Circuit()
    #     try:
    #         parse_r1cs(filename, circ)
    #     except:
    #         continue

    #     print("outputs", circ.nPubOut)

    #     circs, sigmapp, conmapp = componentwise_preprocessing(circ)

    #     if len(circs) == 0: print("No input nodes")
    #     elif len(circs) == 1:

    #         start = time.time()

    #         circ = circs[0]
    #         T = r1cs_distance_tree(circ, clustering_method)

    #         print(len(T[0]))
    #         N = r1cs_O0_rooting(circ, *T)
    #         node_signals(circ, N)

    #         print(time.time() - start)

    #         f = open(filename[:filename.index(".")] + file_suffix + ".json", 'w')
    #         json.dump(N.to_json(), f, indent = 4)
    #         f.close()
    #     else:
            
    #         dir = filename[:filename.index(".")]
    #         total_time = 0

    #         try: os.mkdir(dir) 
    #         except FileExistsError: pass
    #         f = open(dir + "/mapping.txt", 'w')
    #         json.dump({"sigmapp": sigmapp, "conmapp" : conmapp}, f)
    #         f.close()
    #         for i, circ in enumerate(circs):

    #             start = time.time()

    #             T = r1cs_distance_tree(circ, clustering_method)
    #             N = r1cs_O0_rooting(circ, *T)
    #             node_signals(circ, N)

    #             total_time += time.time() - start

    #             f = open(dir + f"/circuit{i}" + file_suffix + ".json", 'w')
    #             json.dump(N.to_json(), f, indent = 4)
    #             f.close()
    #         print(total_time)

    filename = "r1cs_files/binsub_test.r1cs"
    circ = Circuit()
    parse_r1cs(filename, circ)
    connected_preprocessing(circ)

    g = shared_signal_graph(circ.constraints)

    comm = nx.algorithms.community.louvain_communities(g)

    print(comm)

    # start = time.time()

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

    # T = r1cs_distance_tree(circ, clustering_method = cluster_by_linear_coefficient)
    # print("finished tree in", time.time() - start)
    # try:
    #     N = r1cs_O0_rooting(circ, *T)
    # except AssertionError:
    #     print("No input nodes")

    # print(time.time() - start)

    # f = open("test.json", 'w')
    # json.dump(N.to_json(), f, indent = 4)
    # f.close()

    # list(map(lambda con : con.print_constraint_terminal(), map(circ.constraints.__getitem__, [20, 5, 18])))

    # outputs = range(1, circ.nPubOut+1)
    # inputs = range(circ.nPubOut+1, circ.nPubOut+1+circ.nPrvIn+circ.nPubIn)

    # for coni, con in enumerate(circ.constraints):
    #     if any(map(lambda sig : sig in inputs, getvars(con))):
    #         print(coni, "in")

    #     if any(map(lambda sig : sig in outputs, getvars(con))):
    #         print(coni, "out")

    #     if len(con.A) != 0 and len(con.B) != 0:
    #         print(coni)

    # nx.nx_pydot.to_pydot(shared_signal_graph(circ.constraints)).write_png("test.png")

    



    
    