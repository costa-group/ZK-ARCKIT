if __name__ == '__main__':
    import networkx as nx
    import numpy as np
    import time
    import json
    import os
    from functools import reduce
    import itertools
    from typing import List, Dict

    from bij_encodings.assignment import SharedInt
    from utilities import count_ints, getvars, UnionFind, _signal_data_from_cons_list, dist_to_source_set
    from comparison_testing import get_circuits
    from r1cs_scripts.circuit_representation import Circuit
    from r1cs_scripts.read_r1cs import parse_r1cs
    from deprecated.cluster_preprocessing import groups_from_clusters, circuit_clusters
    from structural_analysis.utilities.connected_preprocessing import connected_preprocessing, componentwise_preprocessing
    from structural_analysis.utilities.signal_graph import shared_constraint_graph
    from structural_analysis.utilities.graph_to_img import partition_graph_to_img, dag_graph_to_img, circuit_graph_to_img
    # from structural_analysis.connected_preprocessing import connected_preporcessing
    from structural_analysis.utilities.constraint_graph import shared_signal_graph
    # from structural_analysis.graph_clustering.HCS_clustering import HCS
    # from structural_analysis.graph_clustering.nx_clustering_builtins import *
    # from structural_analysis.graph_clustering.stepped_girvan_newman import stepped_girvan_newman
    from structural_analysis.clustering_methods.naive.signal_equivalence_clustering import naive_removal_clustering, nonorm_relaxes_signal_equivalence_constraint
    from structural_analysis.clustering_methods.naive.degree_clustering import twice_average_degree, ratio_of_signals
    # from structural_analysis.graph_clustering.topological_flow_clustering import circuit_topological_clusters, constraint_topological_order, dag_clustering_from_order, dag_cluster_speed_priority, dag_cluster_and_merge, dag_strict_order_clustering
    # from structural_analysis.graph_clustering.modularity_optimisation import undirected_adjacency, stable_directed_louvain, stable_undirected_louvain
    # from structural_analysis.graph_clustering.spectral_clustering import spectral_undirected_clustering
    from deprecated.cluster_trees.tree_wrapper import O0_tree_clustering
    from deprecated.cluster_trees.r1cs_tree import r1cs_distance_tree
    from structural_analysis.clustering_methods.linear_coefficient import cluster_by_linear_coefficient
    from deprecated.cluster_trees.r1cs_O0_rooting import r1cs_O0_rooting
    from deprecated.cluster_trees.node_signals import node_signals
    from structural_analysis.clustering_methods.nonlinear_attract import nonlinear_attract_clustering
    from structural_analysis.cluster_trees.dag_from_clusters import dag_from_partition, partition_from_partial_clustering, dag_to_nodes, DAGNode
    from structural_analysis.cluster_trees.equivalent_partitions import naive_equivalency_analysis, easy_fingerprint_then_equivalence
    from structural_analysis.cluster_trees.dag_postprocessing import merge_passthrough, merge_only_nonlinear
    from structural_analysis.utilities.node_to_img import nodelist_to_img

    def recursive_search(path):
        for opt in map(lambda opt : path + "/" + opt, os.listdir(path)):
            if ".r1cs" in opt: yield opt
            elif "." not in opt: 
                for f in recursive_search(opt): yield f
    
    def json_to_dagnode(lst : List[dict], custom: bool = True) -> List[DAGNode]:
        # TODO: if necessary put in circ stuff

        def premade_to_dagnode(dct: dict) -> DAGNode:
            n = DAGNode(
                None, dct["node_id"], list(range(dct["initial_constraint"], dct["initial_constraint"] + dct["no_constraints"])), None, None
            )
            n.successors = list(map(lambda x : x["node_id"], dct["subcomponents"]))
            return n

        def custom_to_dagnode(dct : dict) -> DAGNode:
            n = DAGNode(
                None, dct["node_id"], dct["constraints"], dct["input_signals"], dct["output_signals"]
            )
            n.successors = dct["successors"]
            return n


        return list(map(custom_to_dagnode if custom else premade_to_dagnode, lst))

    target_directory = "comparison_trees/PoseidonO0/"

    circ = Circuit()
    parse_r1cs("r1cs_files/PoseidonO0.r1cs", circ)
    
    actual_file = target_directory + "actual.json"

    fp = open(actual_file, 'r')
    actual_tree = json.load(fp)
    fp.close()

    def get_nodes(tree : "Node", acc = SharedInt(0)) -> List["Node"]:
        tree["node_id"] = acc.val
        acc.val += 1
        return list(itertools.chain([tree], *map(lambda n : get_nodes(n, acc), tree["subcomponents"])))

    actual_nodes = get_nodes(actual_tree)
    actual_dagnodes = json_to_dagnode(actual_nodes, False)

    nodelist_to_img(actual_dagnodes, outfile = target_directory + "/actual.png")

    print(len(actual_dagnodes))
    print("only nonlinear", len(list(filter(lambda n : any(map(lambda coni : len(circ.constraints[coni].A) > 0, n.constraints)), actual_dagnodes))))
    

    for clustering_type in ["nonlinear_attract", "louvain"]:
        filename = target_directory + clustering_type + ".json"
        fp = open(filename, 'r')
        clustering_tree = json.load(fp)
        fp.close()

        nodes = clustering_tree["nodes"]
        dagnodes = json_to_dagnode(nodes)

        print(clustering_type, len(clustering_tree["nodes"]))
        print("only nonlinear", len(list(filter(lambda n : any(map(lambda coni : len(circ.constraints[coni].A) > 0, n.constraints)), dagnodes))))
        nodelist_to_img(dagnodes, outfile = target_directory + "/" + clustering_type + ".png")

        


    



    
    