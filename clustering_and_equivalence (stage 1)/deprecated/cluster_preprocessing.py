import numpy as np
import networkx as nx
from typing import List, Tuple, Dict, Set, Callable
from collections import defaultdict

from utilities.assignment import Assignment
from utilities.iterated_adj_reclassing import iterated_label_propagation
from r1cs_scripts.circuit_representation import Circuit
from r1cs_scripts.constraint import Constraint
from deprecated.comparison.constraint_preprocessing import hash_constraint
from structural_analysis.clustering_methods.naive.signal_equivalence_clustering import naive_removal_clustering
from deprecated.comparison.static_distance_preprocessing import _distances_to_signal_set

def circuit_clusters(
        in_pair: List[Tuple[str, Circuit]], 
        clustering_algorithm: Callable[[List[Constraint]], Tuple[Dict[int, List[int]], Dict[int, List[int]], List[int]]] = naive_removal_clustering,
        **kwargs) -> List[List[int]]:
    
    results = {}

    for name, circ in in_pair:

        clusters, adjacency, removed = clustering_algorithm(circ, **kwargs)

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
    
    signal_to_distance = {
        name: {
            sourcename: _distances_to_signal_set(circ.constraints, source)
            for sourcename, source in [("input", range(circ.nPubOut+1, circ.nPubOut + circ.nPrvIn + circ.nPubIn + 1)), ("output", range(1, circ.nPubOut+1))]
        }
        for name, circ in in_pair
    }

    # NOTE: clusters not necessarily in the same order
    internally_hashed_clusters = {
        name: {}
        for name, _ in in_pair
    }

    # give internal hash to each cluster
    for name, circ in in_pair:

        clusters[name]["coni_to_cluster"] = {}
        
        for key, cluster in clusters[name]["clusters"].items():

            hashes = {}

            for consi in cluster:
                clusters[name]["coni_to_cluster"].setdefault(consi, set([])).add(key)

                hash_ = hash_constraint(circ.constraints[consi], name, mapp, known_signal_mapping, signal_to_distance)

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

        hashed_clusters = iterated_label_propagation(
            [name for name, _ in in_pair],
            {name: clusters[name]["clusters"].keys() for name, _ in in_pair},
            {name: clusters[name]["adjacency"] for name, _ in in_pair},
            hashed_clusters
        )

        # re_cluster_hashmapp = Assignment(assignees=1)

        # hashed_clusters = {
        #     name: {
        #         # sorting is important to remain order agnostic

        #         # TODO: maybe don't use setdefault
        #         key: re_cluster_hashmapp.get_assignment(f"{hashed_clusters[name][key]}:{sorted([hashed_clusters[name][adj] for adj in clusters[name]['adjacency'].setdefault(key, [])])}")
        #         for key in clusters[name]["clusters"].keys()
        #     }
        #     for name, _ in in_pair
        # }

    for name, _ in in_pair:
        clusters[name]["clusters_to_hash"] = hashed_clusters[name]

    cluster_groups = {
        name: {}
        for name, _ in in_pair
    }

    re_constraint_hashmapp = Assignment(assignees=1)

    # prepend constraint hash in group with group hash to build new groups
    for name, circ in in_pair:
        # group clusters by internal hashes -- step can be skipped but useful for later for time done logically in next step

        for key in clusters[name]["clusters"].keys():
            chash_ = hashed_clusters[name][key]

            for hash_, consi_list in internally_hashed_clusters[name][key].items():
 
                cluster_groups[name].setdefault(
                    f"{chash_}:{re_constraint_hashmapp.get_assignment(hash_)}", # makes cluster data smaller 
                    []).extend(consi_list)

        for consi in clusters[name]["removed"]:

            cluster_groups[name].setdefault(
                f"*{re_constraint_hashmapp.get_assignment(hash_constraint(circ.constraints[consi], name, mapp, known_signal_mapping, signal_to_distance))}",
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
