
from typing import List, Tuple, Dict
import igraph as ig
import networkx as nx
from itertools import combinations

from circuits_and_constraints.abstract_constraint import Constraint
from circuits_and_constraints.abstract_circuit import Circuit

from utilities.utilities import _signal_data_from_cons_list

def shared_signal_graph_igraph(circ: Circuit) -> ig.Graph:
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
    signal_to_coni = _signal_data_from_cons_list(circ.constraints)

    graph.add_vertices(len(circ.constraints))

    weights = {}
    pair_to_num = lambda pair : pair[0] * circ.nConstraints + pair[1]
    num_to_pair = lambda num : (num // circ.nConstraints, num % circ.nConstraints)

    for signal in signal_to_coni.keys():
        for pair in map(pair_to_num, combinations(signal_to_coni[signal], r = 2)):
            weights[pair] = weights.get(pair, 0) + 1

    graph.add_edges(map(num_to_pair, weights.keys()), attributes={"weight": weights.values()})

    return graph

def shared_signal_graph_nx(cons: List[Constraint], names: List[int] | None = None) -> nx.Graph:
    """
    Given an input list of constraints, returns a networkx graph.
    Vertices in the graph are constraint, edges are between constraints with a shared non-constant signal

    Parameters
    ----------
        cons: List[Constraint]
            List of constraints passed to :func:`_signal_data_from_cons_list`
        names: List[int] | None
            Indices for constraints passed to :func:`_signal_data_from_cons_list`
    
    Returns
    ----------
    nx.Graph
        Vertices in the graph are constraint, edges are between constraints with a shared non-constant signal
    """

    graph = nx.Graph()
    signal_to_coni = _signal_data_from_cons_list(cons, names)

    weights = {}

    for signal in signal_to_coni.keys():

        if len(signal_to_coni[signal]) == 1:
            graph.add_node(next(iter(signal_to_coni[signal])))
            continue

        for i, j in combinations(signal_to_coni[signal], r = 2):
            i, j = min(i,j), max(i,j)
            weights[(i, j)] = weights.setdefault((i, j), 0) + 1

    for i, j in weights.keys():
        graph.add_edge(i, j, weight = weights[(i, j)])

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