import numpy as np
import networkx as nx
from typing import List, Tuple, Dict, Set, Callable
from collections import defaultdict

from bij_encodings.assignment import Assignment
from r1cs_scripts.circuit_representation import Circuit
from r1cs_scripts.constraint import Constraint
from comparison.constraint_preprocessing import hash_constraint
# from structural_analysis.graph_clustering.HCS_clustering import HCS
# from structural_analysis.graph_clustering.nx_clustering_builtins import Louvain, Label_propagation
from structural_analysis.constraint_graph import shared_signal_graph
from structural_analysis.graph_clustering.stepped_girvan_newman import stepped_girvan_newman
from structural_analysis.graph_clustering.signal_equivalence_clustering import naive_removal_clustering

def circuit_clusters(
        in_pair: List[Tuple[str, Circuit]], 
        clustering_algorithm: Callable[[List[Constraint]], Tuple[Dict[int, List[int]], Dict[int, List[int]], List[int]]] = naive_removal_clustering,
        **kwargs) -> List[List[int]]:
    
    results = {}

    for name, circ in in_pair:

        clusters, adjacency, removed = clustering_algorithm(circ.constraints, **kwargs)

        results[name] = {
            "clusters": clusters,
            "adjacency": adjacency,
            "removed": removed
        }
    
    return results

def groups_from_clusters(
        in_pair: List[Tuple[str, Circuit]], 
        clusters: Dict[str, Tuple[Dict[int, List[int]], Dict[int, List[int]], List[int]]],
        known_signal_mapping: Dict[str, Dict[int, Set[int]]] = None,
        mapp: Assignment = None):

    # NOTE: clusters not necessarily in the same order
    internally_hashed_clusters = {
        name: {}
        for name, _ in in_pair
    }

    # give internal hash to each cluster
    for name, circ in in_pair:
        for key, cluster in clusters[name]["clusters"].items():

            hashes = {}

            for consi in cluster:
                hash_ = hash_constraint(circ.constraints[consi], name, mapp, known_signal_mapping)

                hashes.setdefault(hash_, []).append(consi)
            
            internally_hashed_clusters[name][key] = hashes

    def hash_cluster(hashed_cluster, hmapp: Assignment) -> str:

        sizes = {hmapp.get_assignment(hash_): len(constraints) for hash_, constraints in hashed_cluster.items()}
        return ":".join(map(str,sorted(sizes.items())))
    
    hashmapp = Assignment(assignees=1)
    cluster_hashmapp = Assignment(assignees=1)

    hashed_clusters = {
        name: {
            key: cluster_hashmapp.get_assignment(hash_cluster(internal_cluster_hash, hashmapp))
            for key, internal_cluster_hash in internally_hashed_clusters[name].items()
        }
        for name, _ in in_pair
    }

    if clusters[in_pair[0][0]]["adjacency"] != {}:

        re_cluster_hashmapp = Assignment(assignees=1)

        hashed_clusters = {
            name: {
                # sorting is important to remain order agnostic
                key: re_cluster_hashmapp.get_assignment(f"{hashed_clusters[name][key]}:{sorted([hashed_clusters[name][adj] for adj in clusters[name]['adjacency'].setdefault(key, [])])}")
                for key in clusters[name]["clusters"].keys()
            }
            for name, _ in in_pair
        }

    cluster_groups = {
        name: {}
        for name, _ in in_pair
    }

    re_constraint_hashmapp = Assignment(assignees=1)

    # group clusters by internal hashes -- step skipped for time done logically in next step
    # prepend constraint hash in group with group hash to build new groups
    for name, circ in in_pair:
        for key in clusters[name]["clusters"].keys():
            chash_ = hashed_clusters[name][key]

            for hash_, consi_list in internally_hashed_clusters[name][key].items():
 
                cluster_groups[name].setdefault(
                    f"{chash_}:{re_constraint_hashmapp.get_assignment(hash_)}", # makes cluster data smaller 
                    []).extend(consi_list)

        for consi in clusters[name]["removed"]:

            cluster_groups[name].setdefault(
                f"*{re_constraint_hashmapp.get_assignment(hash_constraint(circ.constraints[consi], name, mapp, known_signal_mapping))}",
                []).append(consi)

    return cluster_groups


def constraint_cluster_classes(in_pair: List[Tuple[str, Circuit]]):
    """
    Very basic usage of clusters splitting internal hashes by cluster size
    """
    
    # We don't know which of the size-N clusters is equivalent to the other, so the constraint classes will

    # So initially group all classes with the same size, then split them by hash as before.

    clusters = circuit_clusters(in_pair)

    groups = {}
    
    for name, circ in in_pair:
        
        classes = defaultdict(lambda : [])
        partition_by_length = defaultdict(lambda : [])

        for cluster in clusters[name]:
            partition_by_length[(len(cluster))] += cluster

        for length, constraints in partition_by_length.items():
            for cons in constraints:
                classes[f"{length}:{hash_constraint(circ.constraints[cons])}"].append(cons)
    
        groups[name] = classes

    # TODO: add the cluster encoding logic to SAT solver/ MiniZinc solver
    return groups
