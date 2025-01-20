"""

A set of functions for converting circuit networkx graphs to png images

"""

from typing import List, Tuple, Dict
import networkx as nx
import pydot as pd
import itertools
import collections

from utilities import getvars
from r1cs_scripts.circuit_representation import Circuit
from structural_analysis.cluster_trees.dag_from_clusters import DAGNode
from utilities import _signal_data_from_cons_list, getvars

def circuit_graph_to_img(
        circ: Circuit, G: nx.Graph, induced_subgraph: List[int] | None = None,
        outfile: str = "test.png", return_graph: bool = False 
    ) -> pd.Graph | None :
    """
    Given a circuit, and shared signal graph of that circuit returns a pydot graph with some visual updates

    The pydot graph is the shared signal deck, constraints with input signals are squares, constraints with output 
    signals are triangles, nonlinear constraints are red.

    Parameters
    ----------
        circ: Circuit
            The input circuit
        G: nx.Graph
            networkx graph for the shared signal graph
        induced_subgraph: List[int] | None
            A list of integers representing the subset of vertices to induce a subgraph on. If None the whole graph is returned.
        outfile: String
            If writing to an img file this is the location of the output img
        return_graph: Bool
            Flag that determines if this will return a pydot graph or write the graph to an img file

    
    Returns
    ----------
    pd.Graph | None
        pydot version of the input graph
    """

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
    
    if return_graph: return g
    g.write_png(outfile)

def partition_graph_to_img(
        circ: Circuit, G: nx.Graph, partition: List[List[int]], outfile: str = "test.png", 
        return_graph: bool = False, **kwargs) -> pd.Graph | None:
    """
    Given a circuit, and shared signal graph and a partition, returns a pydot graph with partitions with some visual updates

    Parts in the pydot graph are marked by black squares surrounding vertices in the part. The pydot graph is the shared signal deck, 
    constraints with input signals are squares, constraints with output signals are triangles, nonlinear constraints are red.

    Parameters
    ----------
        circ: Circuit
            The input circuit
        G: nx.Graph
            networkx graph for the shared signal graph
        outfile: String
            If writing to an img file this is the location of the output img
        return_graph: Bool
            Flag that determines if this will return a pydot graph or write the graph to an img file
        kwargs:
            kwargs passed to `circuit_graph_to_img`
    Returns
    ----------
    pd.Graph | None
        pydot version of the input graph
    """
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

def dag_graph_to_img( circ: Circuit, G:nx.Graph, nodes: Dict[int, DAGNode], outfile: str = "test.png", **kwargs ) -> None:
    """
    Given a circuit, and shared signal graph and a DAGNodes, returns a pydot graph with partitions with some visual updates

    Parts in the pydot graph are marked by black squares surrounding vertices in the part. Arcs are directed, within a part these
    have no significance, between parts they indicate relations between parts. The pydot graph is the shared signal deck, 
    constraints with input signals are squares, constraints with output signals are triangles, nonlinear constraints are red.

    Parameters
    ----------
        circ: Circuit
            The input circuit
        G: nx.Graph
            networkx graph for the shared signal graph
        nodes: Dict[int, DAGNode]
            nodes representing a DAG on the circuit
        outfile: String
            If writing to an img file this is the location of the output img
        kwargs:
            kwargs passed to `partition_graph_to_img`
    Returns
    ----------
    None
    """
    g = partition_graph_to_img(circ, G, list(map(lambda n : n.constraints, nodes.values())), return_graph=True, **kwargs)
    g.set_type('digraph')

    for node in nodes.values():
        for rkey in node.successors:
            for src, dst in itertools.product(node.constraints, nodes[rkey].constraints):
                if len(getvars(circ.constraints[src]).intersection(getvars(circ.constraints[dst]))) > 0:
                    g.del_edge(*map(str, [dst, src]))
                    g.add_edge(pd.Edge(src, dst))

    g.write_png(outfile)
        

    