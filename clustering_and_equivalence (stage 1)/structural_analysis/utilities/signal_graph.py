"""
Idea is to have a directed graph showing edge ab implies a circuit where signal a in A*B and b in C of a constraint
"""

import networkx as nx
from typing import List
from itertools import chain, combinations

from r1cs_scripts.constraint import Constraint
from utilities.utilities import getvars

def negone_to_signal( cons: List[Constraint]) -> nx.DiGraph:

    graph = nx.DiGraph()
    p = cons[0].p

    for con in cons:

        for r in con.C.keys():
            
            if con.C[r] != p-1 or r == 0: continue
            
            for l in chain(con.A.keys(), con.B.keys(), con.C.keys()):

                if l == r or l == 0: continue

                graph.add_edge(l, r)
    return graph

def shared_constraint_graph( cons: List[Constraint] ) -> nx.Graph:
    
    graph = nx.Graph()

    for con in cons:

        signals = getvars(con)

        if len(signals) == 1:
            graph.add_node(next(iter(signals)))
            continue

        for l, r in combinations(signals, r=2):
            graph.add_edge(l, r)
    
    return graph