from typing import Dict, List
from structural_analysis.cluster_trees.dag_from_clusters import DAGNode

def get_subclasses_by_nonlinear_shortest_path(nodes: Dict[int, DAGNode]) -> List[Dict[int, DAGNode]]:
    ## weighted shortest path where weight is number of nonlinears in target vertex.
    # doesn't seem super necessary rn

    pass