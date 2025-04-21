
from typing import List
import networkx as nx
from itertools import combinations

from r1cs_scripts.constraint import Constraint
from utilities import _signal_data_from_cons_list, getvars

def shared_signal_graph(cons: List[Constraint], names: List[int] | None = None) -> nx.Graph:
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