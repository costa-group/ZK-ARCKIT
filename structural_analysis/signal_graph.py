"""
Idea is to have a directed graph showing edge ab implies a circuit where signal a in A*B and b in C of a constraint
"""

import pydot
from typing import List
from itertools import chain

from structural_analysis.graph import Graph
from r1cs_scripts.constraint import Constraint

def negone_to_signal( cons: List[Constraint]) -> Graph:

    graph = Graph(set([]), set([]), 'digraph')
    p = cons[0].p

    for con in cons:

        for r in con.C.keys():
            
            if con.C[r] != p-1 or r == 0: continue
            
            for l in chain(con.A.keys(), con.B.keys(), con.C.keys()):

                if l == r or l == 0: continue

                graph.add_edge(l, r)
    return graph

def shared_constraint_graph( cons: List[Constraint] ) -> "Graph":
    
    graph = pydot.Dot(graph_type = 'digraph')

    for con in cons:

        for r in con.C.keys():
            if r == 0: continue
            
            for l in chain(con.A.keys(), con.B.keys(), con.C.keys()):
                if l == r or l == 0: continue
                
                graph.add_edge(l, r)
    
    return graph