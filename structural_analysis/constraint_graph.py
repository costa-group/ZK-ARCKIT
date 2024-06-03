

import pydot
from typing import List

from r1cs_scripts.circuit_representation import Circuit
from r1cs_scripts.constraint import Constraint
from structural_analysis.graph import Graph

def getvars(con: Constraint) -> set:
    return set(con.A.keys()).union(con.B.keys()).union(con.C.keys()).difference(set([0]))

def shared_signal_graph(cons: List[Circuit]) -> Graph:

    graph = Graph(set([]), set([]), graph_type='graph')

    for i, con in enumerate( cons ):

        vars = getvars(con)

        for j, ocon in enumerate( cons ):

            if i == j:
                continue 

            if len( vars.intersection( getvars(ocon)) ) > 0:
                graph.add_edge(i, j)

    return graph