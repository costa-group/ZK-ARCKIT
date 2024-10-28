from typing import List
import networkx as nx
import pydot as pd

from utilities import getvars
from r1cs_scripts.circuit_representation import Circuit

def circuit_graph_to_img(circ: Circuit, G: nx.Graph) -> pd.Graph:

    g = nx.nx_pydot.to_pydot(G)

    in_outputs = lambda sig : 0 < sig <= circ.nPubOut
    in_inputs = lambda sig : circ.nPubOut < sig <= circ.nPubOut+circ.nPrvIn+circ.nPubIn

    for coni, con in enumerate(circ.constraints):
        node = g.get_node(str(coni))[0]

        if any(map(in_outputs, getvars(con))):
            node.set('shape','triangle')
        if any(map(in_inputs, getvars(con))):
            node.set('shape','square')
        if len(con.A) > 0 and len(con.B) > 0:
            node.set('color','red')
    
    return g

def partition_graph_to_img(circ: Circuit, G: nx.Graph, partition: List[List[int]], outfile: str = "test.png"):
    g = circuit_graph_to_img(circ, G)

    for i, part in enumerate(partition):
        c = pd.Cluster(str(i))
        for _ in map(lambda n : c.add_node(g.get_node(str(n))[0]), part): pass
    
        g.add_subgraph(c)
    
    g.write_png(outfile)
