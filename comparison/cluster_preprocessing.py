import numpy as np
from typing import List, Tuple

from r1cs_scripts.circuit_representation import Circuit
from structural_analysis.graph_clustering.nx_clustering_builtins import Louvain, Label_propagation
from structural_analysis.constraint_graph import shared_signal_graph

def circuit_clusters(in_pair: List[Tuple[str, Circuit]], seed = None):
    
    seed_ = np.random.randint(0, 25565)
    results = {}

    for name, circ in in_pair:

        G = shared_signal_graph(circ.constraints)

        # partitions are not necessarily ordered

        results[name] = Louvain(G, seed = seed_)
    
    return results