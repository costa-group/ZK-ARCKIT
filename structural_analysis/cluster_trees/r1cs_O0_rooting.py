
from typing import Tuple, List, Dict

from utilities import getvars
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

    if len(input_vert) > 1:
        raise NotImplementedError(f"Handling multiple input_ver: {input_vert} not currently supported")
        # merge

        # find shortest path and merge all nodes along shortest path, repeat until all nodes merged
        # define new vertices/adjacencies so it works
        # TODO
        pass
    else:
        root = input_vert[0]

    # define rooted tree structure
    vert_to_adjacent_vert = {}
    for l, r in adjacencies:
        vert_to_adjacent_vert.setdefault(l, []).append(r)
        vert_to_adjacent_vert.setdefault(r, []).append(l)
    
    root_node = TreeNode(root, None, vertices[root])
    pipe = [root_node]

    while len(pipe) > 0:
        node = pipe.pop()
        node_id = node.node_id

        children_ids = filter(lambda id : node.parent is None or id != node.parent.node_id, vert_to_adjacent_vert.setdefault(node_id, []))
        node.children = list(map(lambda id : TreeNode(id, node, vertices[id]),children_ids))
        pipe.extend(node.children)

    return root_node
    


    
