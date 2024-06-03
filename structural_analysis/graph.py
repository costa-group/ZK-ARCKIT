
import pydot
import itertools
from typing import Set, Tuple

class Graph():
    """
    represents an undirected graph
    """

    def __init__(self, vertices = Set[int], edges = Set[Tuple[int, int]], graph_type = 'graph') -> "Graph":

        # avoids annoying pointer bugs
        self.vertices = set(vertices)
        self.edges = set(edges)

        assert all([ v in  vertices for v in itertools.chain.from_iterable(edges)]), "edges contain illegal vertices"

        self.dot = pydot.Dot(graph_type=graph_type, strict=True)

        for v in vertices:
            self.dot.add_node(
                pydot.Node(label = v)
            )

        for l, r in edges:
            self.dot.add_edge(
                pydot.Node(label = v)
            )
    
    def add_vertex(self, v: int):

        self.vertices.add(v)
        self.dot.add_node(pydot.Node(label = v))

    def add_edge(self, l: int, r: int):

        self.vertices.update([l,r])
        self.edges.add((l, r))
        self.dot.add_edge(pydot.Edge(l, r))
    
    def write_png(self, outfile: str):
        self.dot.write_png(outfile)