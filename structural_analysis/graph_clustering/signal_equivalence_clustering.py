"""
Clustering based around the fact that almost always a template being called is connected via a single constraint-constraint edge.
"""

import networkx as nx
from typing import List

from r1cs_scripts.constraint import Constraint
from structural_analysis.signal_graph import shared_constraint_graph
from normalisation import r1cs_norm

def naive_all_removal(cons: List[Constraint]) -> nx.Graph:

    def is_signal_equivalence_constraint(con: Constraint) -> bool:
        return len(con.A) + len(con.B) == 0 and len(con.C) == 2 and sorted(r1cs_norm(con)[0].C.values()) == [1, con.p - 1]

    return shared_constraint_graph(filter(lambda con : not is_signal_equivalence_constraint(con), cons))