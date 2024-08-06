
from typing import List
import networkx as nx
from itertools import combinations

from r1cs_scripts.circuit_representation import Circuit
from r1cs_scripts.constraint import Constraint

from structural_analysis.graph_clustering.degree_clustering import _signal_data_from_cons_list

def getvars(con: Constraint) -> set:
    return set(con.A.keys()).union(con.B.keys()).union(con.C.keys()).difference(set([0]))

def shared_signal_graph(cons: List[Circuit]) -> nx.Graph:

    graph = nx.Graph()
    _, signal_to_coni = _signal_data_from_cons_list(cons)

    for signal in signal_to_coni.keys():

        if len(signal_to_coni[signal]) == 1:
            graph.add_node(next(iter(signal_to_coni[signal])))
            continue

        for i, j in combinations(signal_to_coni[signal], r = 2):
            graph.add_edge(i, j)

    return graph