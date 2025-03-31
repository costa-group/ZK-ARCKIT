"""
Clustering based around the fact that almost always a template being called is connected via a single constraint-constraint edge.
"""

import networkx as nx
from typing import List, Callable
import itertools
from functools import reduce

from structural_analysis.clustering_methods.naive.clustering_from_list import cluster_by_ignore
from r1cs_scripts.circuit_representation import Circuit
from r1cs_scripts.constraint import Constraint
from structural_analysis.utilities.signal_graph import shared_constraint_graph
from structural_analysis.utilities.constraint_graph import shared_signal_graph, getvars
from normalisation import r1cs_norm

def is_signal_equivalence_constraint(con: Constraint) -> bool:
    "Returns true for linear constraints that when normalised are of the form x = y"
    return len(con.A) + len(con.B) == 0 and len(con.C) == 2 and sorted(r1cs_norm(con)[0].C.values()) == [1, con.p - 1]

def nonorm_relaxes_signal_equivalence_constraint(con: Constraint) -> bool:
    "Returns true for linear constraints that are of the form x = y + c for constant c"
    return len(con.A) + len(con.B) == 0 and len(getvars(con)) == 2 and all(map(lambda sig : con.C[sig] in [1, con.p-1], getvars(con)))

def naive_removal_clustering(circ: Circuit, clustering_method: int = 0, ignore_pattern: Callable[[Constraint], bool] = is_signal_equivalence_constraint, **kwargs) -> List[List[int]]:
    """
    Clustering Method

    Clusters constraint in a circuit by the connected components achieved by ignoring all constrain that matcha a given pattern.
    Default pattern is signal_equivalence_constraint

    Parameters
    ----------
        circ: Circuit
            The input circuit to cluster
        clustering_method: int
            Deprecated option picker, kept to not break un-refactored code -- TODO: clean up
        ignore_pattern: Constraint -> Bool
            Pattern match function to determine which constraints to ignore
    
    Returns
    ---------
    (clusters, adjacency, removed)
        cluster: Dict[int, List[int]]
            Partition of the input graph given by connected components. Clusters are indexed by an arbitrary element of the cluster. 
            Dictionary used to later be able to remove and reindex elements without remapping indices.

        adjacency: Dict[int, List[int]]
            Maps cluster index to adjacent cluster indices. Empty if calculate_adjacency is False

        removed: List[int]
            List of removed constraints.
    """

    match clustering_method:
        case 0: return cluster_by_ignore(circ, 2, ignore_pattern, **kwargs)
        case _: raise AssertionError(f"Invalid method {clustering_method} in naive cluster")
