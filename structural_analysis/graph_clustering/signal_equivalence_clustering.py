"""
Clustering based around the fact that almost always a template being called is connected via a single constraint-constraint edge.
"""

import networkx as nx
from typing import List
import itertools
from functools import reduce

from structural_analysis.graph_clustering.clustering_from_list import cluster_from_list
from r1cs_scripts.constraint import Constraint
from structural_analysis.signal_graph import shared_constraint_graph
from structural_analysis.constraint_graph import shared_signal_graph, getvars
from normalisation import r1cs_norm

def is_signal_equivalence_constraint(con: Constraint) -> bool:
        return len(con.A) + len(con.B) == 0 and len(con.C) == 2 and sorted(r1cs_norm(con)[0].C.values()) == [1, con.p - 1]

def naive_all_removal(cons: List[Constraint]) -> nx.Graph:

    #TODO: why did this version not drop constraints?

    g = shared_signal_graph(cons)

    to_remove = [i for i, con in enumerate(cons) if is_signal_equivalence_constraint(con)]

    g.remove_nodes_from(to_remove)

    return list(nx.connected_components(g)), [[i] for i in to_remove]

def naive_removal_clustering(cons: List[Constraint], **kwargs) -> List[List[int]]:

    return cluster_from_list(cons, ignore_func=is_signal_equivalence_constraint, **kwargs)

