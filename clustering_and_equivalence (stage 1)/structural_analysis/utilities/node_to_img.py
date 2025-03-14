"""

A set of functions for converting node lists into graph png's

"""

from typing import List
import pydot as pd

from structural_analysis.cluster_trees.dag_from_clusters import DAGNode

def nodelist_to_img(nodes: List[DAGNode], outfile: str = "test.png", subgraph: List[int] | None = None, return_graph: bool = False
                    ) -> pd.Graph | None:
    g = pd.Dot(graph_type='digraph')

    if subgraph is not None:
        nodes = [nodes[i] for i in subgraph]

    for node in nodes:
        g.add_node(pd.Node(name = str(node.id)))

        for onode in node.successors:
            # given this will typically be on the other of max a few thousand (or the img is unusable, we don't need to be too efficient)
            if subgraph is not None and onode not in subgraph: continue
            g.add_edge(pd.Edge(str(node.id), str(onode)))
    
    if return_graph: return g
    g.write_png(outfile)
    


    