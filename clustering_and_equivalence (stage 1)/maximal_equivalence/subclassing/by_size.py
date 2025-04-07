from typing import List, Dict
import itertools

from structural_analysis.cluster_trees.dag_from_clusters import DAGNode
from utilities import UnionFind

def get_subclasses_by_size(nodes: Dict[int, DAGNode], tol: float = 0.8) -> List[Dict[int, DAGNode]]:
    ComparableKeys = UnionFind()

    # size tolerance based
    for lkey, rkey in itertools.combinations(nodes.keys(), r=2):
        msize, lsize = max(len(nodes[lkey].constraints), len(nodes[rkey].constraints)), min(len(nodes[lkey].constraints), len(nodes[rkey].constraints))
        if msize * tol <= lsize or abs(msize - lsize) <= 1:
            ComparableKeys.union(lkey, rkey)

    key_classes = {}
    for key in nodes.keys():
        key_classes.setdefault(ComparableKeys.find(key), {}).__setitem__(key, nodes[key])

    return key_classes.values()