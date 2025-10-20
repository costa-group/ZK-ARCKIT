
from typing import List, Tuple, Dict
import igraph as ig
from itertools import combinations

from circuits_and_constraints.abstract_constraint import Constraint
from utilities.utilities import _signal_data_from_cons_list

def shared_signal_graph(cons: List[Constraint]) -> ig.Graph:
    """
    Given an input list of constraints, returns a igraph graph.
    Vertices in the graph are constraint, edges are between constraints with a shared non-constant signal

    Parameters
    ----------
        cons: List[Constraint]
            List of constraints passed to :func:`_signal_data_from_cons_list`
    Returns
    ----------
    ig.Graph
        Vertices in the graph are constraint, edges are between constraints with a shared non-constant signal
    """

    graph = ig.Graph()
    signal_to_coni = _signal_data_from_cons_list(cons)

    weights = {}

    graph.add_vertices(len(cons))
    graph.add_edges

    for signal in signal_to_coni.keys():

        for i, j in combinations(signal_to_coni[signal], r = 2):
            i, j = min(i,j), max(i,j)
            weights[(i, j)] = weights.get((i, j), 0) + 1

    graph.add_edges([(i, j) for i, j in weights.keys()], attributes={"weight": weights.values()})

    return graph

def shared_constraint_graph( cons: List[Constraint] ) -> ig.Graph:
    
    graph = ig.Graph()

    edges = set([])

    for con in cons:

        signals = con.signals()

        graph.add_vertices(map(str, signals)) ## dealing with non-comprehensive signals that can be quite common...
        edges.update(combinations(signals, r=2))
    
    graph.add_edges(edges)
    return graph