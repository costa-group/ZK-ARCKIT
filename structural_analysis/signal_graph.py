"""
Idea is to have a directed graph showing edge ab implies a circuit where signal a in A*B and b in C of a constraint
"""

import pydot
from typing import List
from itertools import chain

from r1cs_scripts.constraint import Constraint

def negone_to_signal( cons: List[Constraint]) -> "Graph":

    graph = pydot.Dot(graph_type = 'digraph', strict=True)
    p = cons[0].p

    for con in cons:

        for r in con.C.keys():

            
            if con.C[r] != p-1:
                continue
            
            for l in chain(con.A.keys(), con.B.keys(), con.C.keys()):

                if l == r:
                    continue

                graph.add_edge(
                    pydot.Edge(l, r)
                )
    return graph

def abc_signal_graph( cons: List[Constraint] ) -> "Graph":
    
    graph = pydot.Dot(graph_type = 'digraph')

    for con in cons:

        for r in con.C.keys():
            
            for l in chain(con.A.keys(), con.B.keys(), con.C.keys()):
                if l == r:
                    continue
                
                graph.add_edge(
                    pydot.Edge(l, r)
                )
    
    return graph

def write_png(graph: "Graph", location: str):
    graph.write_png(location)