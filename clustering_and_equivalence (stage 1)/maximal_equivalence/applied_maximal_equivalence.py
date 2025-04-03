"""
We have maximal equivalence but:
    only between two files -- ignores the input and ouput 

To apply this we process each node - check compatability with next node in set -- if pair is maximal already then:
"""
from typing import List, Dict
import itertools

from structural_analysis.cluster_trees.dag_from_clusters import DAGNode
from maximal_equivalence.maximal_equivalence import maximum_equivalence
from utilities import UnionFind

def pairwise_maximally_equivalent_classes(nodes: Dict[int, DAGNode], tol: float = 0.8) -> List[List[DAGNode]]:
    """
    each in nodes is potentially a pair so we check each

    returns new list of DAGNodes (with no input/output pair) s.t. each class is equivalent w/o inputs
    """
    # TODO: what happens if are closely maximally equivalent but the two first compared have an extra constraint -- deal with this case

    class_circuit = {}
    classes: Dict[int, List[DAGNode]] = {}
    
    names = ["Left", "Right"]

    for id, node in nodes.items():
        print(id, end='\r')

        matched = False
        
        for key in classes.keys():
            sub_circ = node.get_subcircuit()
            comp_circ = class_circuit[key]

            msize, lsize = sorted(map(lambda c : c.nConstraints, [sub_circ, comp_circ]))
            if msize * tol > lsize: continue

            coni_pairs, _ = maximum_equivalence(list(zip(names, [comp_circ, sub_circ])))

            if len(coni_pairs) > (1 if len(classes[key]) > 1 else tol) * comp_circ.nConstraints:
                matched = True
                if len(classes[key]) > 1:
                    # reduce sub_circ and append
                    # TODO: check here for input/output?
                    new_node = DAGNode(node.circ, node.id, list(map(node.constraints.__getitem__, map(lambda p : p[1], coni_pairs))), set([]), set([]))
                    classes[key].append(new_node)

                else:
                    # reduce both and calculate new pairs
                    comp_node = classes[key][0]
                    new_comp_node = DAGNode(comp_node.circ, comp_node.id, list(map(comp_node.constraints.__getitem__, map(lambda p : p[0], coni_pairs))), set([]), set([]))
                    new_node = DAGNode(node.circ, node.id, list(map(node.constraints.__getitem__, map(lambda p : p[1], coni_pairs))), set([]), set([]))
                    classes[key] = [new_comp_node, new_node]

                    class_circuit[key] = new_comp_node.get_subcircuit()
                    new_comp_node.subcircuit = None
                break

        if not matched:
            classes[node.id] = [node]
            class_circuit[node.id] = node.get_subcircuit()

    print('done: ', classes)
    return classes.values()

def maximally_equivalent_classes(nodes: Dict[int, DAGNode], tol: float = 0.8) -> List[List[DAGNode]]:
    ComparableKeys = UnionFind()

    for lkey, rkey in itertools.combinations(nodes.keys(), r=2):
        msize, lsize = max(len(nodes[lkey].constraints), len(nodes[rkey].constraints)), min(len(nodes[lkey].constraints), len(nodes[rkey].constraints))
        if msize * tol <= lsize or abs(msize - lsize) <= 1:
            ComparableKeys.union(lkey, rkey)

    key_classes = {}
    for key in nodes.keys():
        key_classes.setdefault(ComparableKeys.find(key), {}).__setitem__(key, nodes[key])

    from utilities import count_ints
    print(count_ints(map(len, key_classes.values())))
    classes = list(itertools.chain(*map(lambda ns : pairwise_maximally_equivalent_classes(ns, tol=tol), key_classes.values())))
    return classes

    