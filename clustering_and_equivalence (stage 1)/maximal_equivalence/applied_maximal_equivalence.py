"""
We have maximal equivalence but:
    only between two files -- ignores the input and ouput 

To apply this we process each node - check compatability with next node in set -- if pair is maximal already then:
"""
from typing import List, Dict
import itertools
import time

from r1cs_scripts.circuit_representation import Circuit
from structural_analysis.cluster_trees.dag_from_clusters import DAGNode
from maximal_equivalence.maximal_equivalence import maximum_equivalence
from utilities import count_ints, _is_nonlinear
from maximal_equivalence.subclassing.by_nonlinears import get_subclasses_by_nonlinear_relation
from maximal_equivalence.subclassing.by_size import get_subclasses_by_size
from maximal_equivalence.subclassing.by_nonlinear_shortest_path import get_subclasses_by_nonlinear_shortest_path
from structural_analysis.cluster_trees.dag_from_clusters import dag_from_partition, dag_to_nodes
from structural_analysis.cluster_trees.full_equivalency_partitions import subcircuit_fingerprint_with_structural_augmentation_equivalency
from structural_analysis.cluster_trees.dag_postprocessing import merge_passthrough, merge_only_nonlinear

def pairwise_maximally_equivalent_classes(nodes: Dict[int, DAGNode], tol: float = 0.8, solver_timeout: int | None = None) -> List[List[DAGNode]]:
    """
    each in nodes is potentially a pair so we check each

    returns new list of DAGNodes (with no input/output pair) s.t. each class is equivalent w/o inputs
    """
    # TODO: what happens if are closely maximally equivalent but the two first compared have an extra constraint -- deal with this case

    if len(nodes) == 1:
        return [list(nodes.values())]

    class_circuit = {}
    classes: Dict[int, List[DAGNode]] = {}
    
    names = ["Left", "Right"]

    for id, node in nodes.items():

        matched = False
        
        for key in classes.keys():
            sub_circ = node.get_subcircuit()
            comp_circ = class_circuit[key]

            msize, lsize = sorted(map(lambda c : c.nConstraints, [sub_circ, comp_circ]))
            if msize * tol > lsize: continue

            coni_pairs, _ = maximum_equivalence(list(zip(names, [comp_circ, sub_circ])), solver_timeout=solver_timeout)

            if len(coni_pairs) >= (1 if len(classes[key]) > 1 else tol) * comp_circ.nConstraints:
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
    return classes.values()

def maximally_equivalent_classes(
            nodes: Dict[int, DAGNode], 
            equivalency: List[List[int]] | None = None, 
            equivalent_coni_map: List[List[List[int]]] | None = None,
            tol: float = 0.8, 
            solver_timeout: int | None = None,
            exit_subclasses : bool = False,
            exit_max_classes : bool = False,
            return_json : bool = True
        ) -> List[List[DAGNode]]:
    """
    Step 1: Split nodes into classes
    Step 2: Find maximally equivalent classes (up to size tol) which define new partitions
    Step 3 - TODO: Redo the partitioning -> DAGNodes calculations.
    """
    # TODO: with no equivalent
    timing = {}

    # filter by nonlinear shortest path
    if equivalency is None:
        equivalent = { nodeid : [nodeid] for nodeid in nodes.keys() }
    else:
        equivalent = { lst[0] : lst for lst in equivalency }
        equivalent_index = {lst[0] : i for i, lst in enumerate(equivalency)}

    start = time.time()
    last_time = start

    equivalent_with_nonlinear = list(filter(lambda id : any(map(_is_nonlinear, map(nodes[id].circ.constraints.__getitem__, nodes[id].constraints))), equivalent.keys()))
    classes = get_subclasses_by_nonlinear_shortest_path(nodes, equivalent_with_nonlinear)
    # classes = get_subclasses_by_nonlinear_shortest_path(nodes, equivalent.keys())
    
    # filter by nonlinear fingerprinting
    classes = itertools.chain(*map(get_subclasses_by_nonlinear_relation, classes))
    # filter by size tolerance
    classes = itertools.chain(*map(lambda class_ : get_subclasses_by_size(class_, tol=tol), classes))

    if exit_subclasses: return count_ints(map(len, classes))

    res = list(itertools.chain(*map(lambda ns : pairwise_maximally_equivalent_classes(ns, tol=tol, solver_timeout = solver_timeout), classes)))
    timing["maxequiv_timing"] = time.time() - last_time
    last_time = time.time()
    
    if exit_max_classes: 
        return len(res), count_ints( map(lambda class_ : sum(map(lambda id : len(equivalent[id]), map(lambda node : node.id, class_))), res))

    ## get into format of partition of constraints

    partition = []

    # parts from linear nodes that are not equivalenced
    for key in filter(lambda id : not any(map(_is_nonlinear, map(nodes[id].circ.constraints.__getitem__, nodes[id].constraints))), equivalent.keys()):
        partition.extend(map(lambda id : nodes[id].constraints, equivalent[key]))

    # parts from nonlinear nodes now made equivalent
    # TODO: some coni are appearing in two or more partitions
    for class_ in res:
        for node in class_:
            removed_coni = set(nodes[node.id].constraints).difference(node.constraints)

            partition.append(node.constraints) # self coni
            partition.extend(itertools.starmap(lambda onode_id, mapping : 
                                list(map(nodes[onode_id].constraints.__getitem__, map(mapping.__getitem__, map(nodes[node.id].constraints.index, node.constraints))))
                                , zip(equivalent[node.id][1:], equivalent_coni_map[equivalent_index[node.id]])
                                )) # coni from equivalent

            partition.extend(map(lambda int_ : [int_], removed_coni)) # removed coni - left unclustered
            partition.extend(itertools.chain(*itertools.starmap(lambda onode_id, mapping : 
                            map(lambda int_ : [int_], map(nodes[onode_id].constraints.__getitem__, map(mapping.__getitem__, map(nodes[node.id].constraints.index, removed_coni))))   
                            , zip(equivalent[node.id][1:], equivalent_coni_map[equivalent_index[node.id]]) 
                            ))) # equiv removed coni - left unclustered
    
    timing["partitioning"] = time.time() - last_time
    last_time = time.time()

    circ = next(iter(nodes.values())).circ            
    partition, arcs = dag_from_partition(circ, partition)
    nodes = dag_to_nodes(circ, partition, arcs)

    ## TODO: deside relevance
    nodes = merge_passthrough(circ, nodes)
    nodes = merge_only_nonlinear(circ, nodes)

    equivalency, mapping = subcircuit_fingerprint_with_structural_augmentation_equivalency(nodes)

    timing["conversion_to_dag"] = time.time() - last_time
    last_time = time.time()

    if not return_json: return nodes, equivalency
    
    results = {
        "timing" : timing,
        "nodes" : list(map(lambda n : n.to_dict(), nodes.values())),
        "equivalency": equivalency,
        "equiv_mappings": mapping
    }

    return results

    ### need to find maps for non-equivalent circuits .. TODO: is this worth it? it seems like the timing doesn't support it

    

    