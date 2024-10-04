
from typing import Tuple, List, Dict
import itertools

from utilities import getvars, BFS_shortest_path
from r1cs_scripts.circuit_representation import Circuit

class TreeNode():

    def __init__(self, node_id: int, parent: "TreeNode", constraints: List[int], children: List["TreeNode"] = []):
        self.node_id = node_id
        self.parent = parent # can be None for root
        self.constraints = constraints
        self.children = children
    
    def to_json(self) -> dict:
        return {
            "node_id": self.node_id,
            "constraints": self.constraints,
            "subcomponents":list(map(lambda n : n.to_json(), self.children))
        }

def r1cs_O0_rooting(
        circ: Circuit,
        vertices: Dict[int, list[int]],
        adjacencies: List[Tuple[int, int]]
) -> TreeNode:
    """
    Modifies an unrooted tree merging all input nodes into a single component and producing a rooted tree structure
    """

    inputs = list(range(circ.nPubOut+1, circ.nPubOut + circ.nPrvIn + circ.nPubIn + 1))

    input_coni = list(filter(lambda coni : len(getvars(circ.constraints[coni]).intersection(inputs)) > 0, range(circ.nConstraints)))
    input_vert = list(filter(lambda repr : any([l in vertices[repr] for l in input_coni]), vertices.keys()))

    # define rooted tree structure
    vert_to_adjacent_vert = {}
    for l, r in adjacencies:
        vert_to_adjacent_vert.setdefault(l, []).append(r)
        vert_to_adjacent_vert.setdefault(r, []).append(l)
    vert_to_adjacent_vert = {k: set(v) for k,v in vert_to_adjacent_vert.items()}

    while len(input_vert) > 1:

        # TODO: maybe think about doing choosing s,t to do less BFS searches e.g. should be furthest distance from each other?
        path = BFS_shortest_path(*input_vert[:2], vert_to_adjacent_vert)
        root, to_merge = path[0], path[1:]

        vertices[root].extend(itertools.chain(map(vertices.__getitem__, to_merge)))
        
        adjacent_to_root = set(filter(lambda v : v not in path, itertools.chain(*map(vert_to_adjacent_vert.__getitem__, path))))
        for v in to_merge:
            for u in vert_to_adjacent_vert[v]:
                vert_to_adjacent_vert[u].remove(v)
            del vert_to_adjacent_vert[v] # more memory efficient

        vert_to_adjacent_vert[root] = adjacent_to_root
        input_vert = [v for v in input_vert if v not in to_merge]

    root = input_vert[0]
    root_node = TreeNode(root, None, vertices[root])
    pipe = [root_node]

    while len(pipe) > 0:
        node = pipe.pop()
        node_id = node.node_id

        children_ids = filter(lambda id : node.parent is None or id != node.parent.node_id, vert_to_adjacent_vert.setdefault(node_id, []))
        node.children = list(map(lambda id : TreeNode(id, node, vertices[id]),children_ids))
        pipe.extend(node.children)

    return root_node
    


    
