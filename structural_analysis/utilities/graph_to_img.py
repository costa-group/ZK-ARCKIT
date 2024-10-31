from typing import List, Tuple
import networkx as nx
import pydot as pd
import itertools
import collections

from utilities import getvars
from r1cs_scripts.circuit_representation import Circuit

def circuit_graph_to_img(circ: Circuit, G: nx.Graph, induced_subgraph: List[int] | None = None) -> pd.Graph:

    if induced_subgraph is not None:
        G = nx.induced_subgraph(G, induced_subgraph)

    g: pd.Graph = nx.nx_pydot.to_pydot(G)

    in_outputs = lambda sig : 0 < sig <= circ.nPubOut
    in_inputs = lambda sig : circ.nPubOut < sig <= circ.nPubOut+circ.nPrvIn+circ.nPubIn

    for node in g.get_node_list(): # coni, con in enumerate(circ.constraints):
        con = circ.constraints[ int( node.get_name() ) ]

        if any(map(in_outputs, getvars(con))):
            node.set('shape','triangle')
        if any(map(in_inputs, getvars(con))):
            node.set('shape','square')
        if len(con.A) > 0 and len(con.B) > 0:
            node.set('color','red')
    
    return g

def partition_graph_to_img(
        circ: Circuit, G: nx.Graph, partition: List[List[int]], outfile: str = "test.png", 
        return_graph: bool = False, **kwargs) -> pd.Graph:
    
    g = circuit_graph_to_img(circ, G, **kwargs)

    # formatted this way to work with induced subgraphs
    for i, part in enumerate(partition):
        c = pd.Cluster(str(i))
        
        # pythonic hack to have efficient looping
        collections.deque(
            map(lambda nonempty_node_list: c.add_node( nonempty_node_list[0] ),
            filter(lambda node_list : len(node_list) > 0,
            map(g.get_node,
            map(str, part
        )))), maxlen=0)

        if len( c.get_node_list() ) > 0: g.add_subgraph(c)
    
    if return_graph: return g
    g.write_png(outfile)

def dag_graph_to_img(
        circ: Circuit, G: nx.Graph, partition: List[List[int]], arcs: List[Tuple[int, int]], 
        outfile: str = "test.png", **kwargs):

    g = partition_graph_to_img(circ, G, partition, return_graph = True, **kwargs)
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
        

    