
from typing import List
import networkx as nx

from r1cs_scripts.circuit_representation import Circuit
from r1cs_scripts.constraint import Constraint

def getvars(con: Constraint) -> set:
    return set(con.A.keys()).union(con.B.keys()).union(con.C.keys()).difference(set([0]))

def shared_signal_graph(cons: List[Circuit]) -> nx.Graph:

    graph = nx.Graph()
    for i, con in enumerate( cons ):

        vars = getvars(con)

        for j, ocon in enumerate( cons ):

            if i == j:
                continue 

            if len( vars.intersection( getvars(ocon)) ) > 0:
                graph.add_edge(i, j)

    return graph