import numpy as np
import networkx as nx
from typing import List, Tuple
from collections import defaultdict

from r1cs_scripts.circuit_representation import Circuit
from comparison.constraint_preprocessing import hash_constraint
# from structural_analysis.graph_clustering.HCS_clustering import HCS
# from structural_analysis.graph_clustering.nx_clustering_builtins import Louvain, Label_propagation
from structural_analysis.constraint_graph import shared_signal_graph
from structural_analysis.graph_clustering.stepped_girvan_newman import stepped_girvan_newman

def circuit_clusters(in_pair: List[Tuple[str, Circuit]], seed = None):
    
    results = {}

    for name, circ in in_pair:

        G = shared_signal_graph(circ.constraints)

        # stepped girvan_newman is pseudo-deterministic (technically can fail due to extreme floating-point errors)
        results[name] = stepped_girvan_newman(G, seed = seed)
    
    return results

def constraint_classes(in_pair: List[Tuple[str, Circuit]], seed = None):
    
    # We don't know which of the size-N clusters is equivalent to the other, so the constraint classes will

    # So initially group all classes with the same size, then split them by hash as before.

    clusters = circuit_clusters(in_pair, seed = seed)

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
