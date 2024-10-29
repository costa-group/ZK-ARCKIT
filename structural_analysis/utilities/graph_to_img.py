from typing import List, Tuple
import networkx as nx
import pydot as pd
import itertools

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

def partition_graph_to_img(circ: Circuit, G: nx.Graph, partition: List[List[int]], outfile: str = "test.png", return_graph: bool = False) -> pd.Graph:
    g = circuit_graph_to_img(circ, G)

    for i, part in enumerate(partition):
        c = pd.Cluster(str(i))
        for _ in map(lambda n : c.add_node(g.get_node(str(n))[0]), part): pass
    
        g.add_subgraph(c)
    
    if return_graph: return g
    g.write_png(outfile)

def dag_graph_to_img(circ: Circuit, G: nx.Graph, partition: List[List[int]], arcs: List[Tuple[int, int]], outfile: str = "test.png"):

    g = partition_graph_to_img(circ, G, partition, return_graph = True)
    g.set_type("digraph")

    coni_to_part = [None for _ in range(circ.nConstraints)]
    for i, part in enumerate(partition):
        for coni in part: coni_to_part[coni] = i

    partition_outgoing = [ [] for part in partition ]

    for edge in g.get_edge_list(): partition_outgoing[coni_to_part[int(edge.get_source())]].append(edge)

    for arc in arcs:
        parti, partj = arc

        edges_between = itertools.chain(
            filter(lambda edge : partj == coni_to_part[int(edge.get_destination())], partition_outgoing[parti]),
            filter(lambda edge : parti == coni_to_part[int(edge.get_destination())], partition_outgoing[partj])
        )
        edges_between = list(edges_between)

        for edge in edges_between:
            src, dst = edge.get_source(), edge.get_destination()
            if int(src) in partition[parti]: continue
            g.del_edge(src, dst)
            g.add_edge(pd.Edge(dst, src))

    g.write_png(outfile)
        

    