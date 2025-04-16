from typing import List, Dict, Iterable
from pysat.formula import CNF
from pysat.card import CardEnc, EncType
from pysat.solvers import Solver
import pysat as ps
import time 
import numpy as np
import json
from functools import reduce
from itertools import product

from comparison.compare_circuits import circuit_equivalence
from comparison_testing import get_circuits, shuffle_constraints
from comparison.constraint_preprocessing import hash_constraint, constraint_classes, known_split
from deprecated.cluster_preprocessing import circuit_clusters, constraint_cluster_classes, groups_from_clusters
from r1cs_scripts.modular_operations import multiplyP
from r1cs_scripts.constraint import Constraint
from r1cs_scripts.circuit_representation import Circuit
from r1cs_scripts.read_r1cs import parse_r1cs
from deprecated.preprocessing.singular_preprocessing import singular_class_preprocessing
from bij_encodings.preprocessing.iterated_adj_reclassing import iterated_adjacency_reclassing
from deprecated.preprocessing.joint_fingerprinting import signal_constraint_fingerprinting
from bij_encodings.assignment import Assignment
from bij_encodings.reduced_encoding.red_class_encoder import reduced_encoding_class
from bij_encodings.reduced_encoding.red_natural_encoding import ReducedNaturalEncoder
from bij_encodings.reduced_encoding.red_pseudoboolean_encoding import ReducedPseudobooleanEncoder, pseudoboolean_signal_encoder
from bij_encodings.online_info_passing import OnlineInfoPassEncoder
from bij_encodings.batched_info_passing import BatchedInfoPassEncoder
from structural_analysis.clustering_methods.naive.degree_clustering import twice_average_degree, ratio_of_signals
from structural_analysis.clustering_methods.naive.signal_equivalence_clustering import naive_removal_clustering, is_signal_equivalence_constraint
from deprecated.modularity.topological_flow_clustering import circuit_topological_clusters
from comparison.static_distance_preprocessing import distances_to_static_preprocessing
from testing_harness import run_affirmative_test, run_current_best_test
from structural_analysis.utilities.connected_preprocessing import connected_preprocessing
from normalisation import r1cs_norm
from utilities import count_ints, _signal_data_from_cons_list, getvars
from comparison.static_distance_preprocessing import _distances_to_signal_set
from maximal_equivalence.shortest_minimum_span import shortest_minimum_span
from maximal_equivalence.maximal_equivalence import maximum_equivalence
from structural_analysis.cluster_trees.dag_from_clusters import DAGNode
from maximal_equivalence.applied_maximal_equivalence import maximally_equivalent_classes, pairwise_maximally_equivalent_classes
import itertools

def cons_eq(C1: Constraint, C2: Constraint):
    if type(C1) == int:
        return C1 == C2

    if C1.A.keys() != C2.A.keys() or C1.B.keys() != C2.B.keys() or C1.C.keys() != C2.C.keys():
        return False

    return all([C1.A[key] == C2.A[key] for key in C1.A.keys()]
            +  [C1.B[key] == C2.B[key] for key in C1.B.keys()]
            +  [C1.C[key] == C2.C[key] for key in C1.C.keys()])

def get_absmax_lit(clauses):
    return max(map(max, map(lambda x : map(abs, x), clauses)))

def to_dagnode(circ, node):
    return DAGNode(circ, node["node_id"], node["constraints"], set(node["input_signals"]), set(node["output_signals"]))
    
if __name__ == '__main__':

    filenames = ["binsub_test", "Poseidon", "Reveal", "Biomebase", "Move", "sha256", "test_ecdsa", "test_ecdsa_verify"]
    compilers = ["O0", "O1"]

    clustering = "louvain"
    test_dir = "with_mapping"

    for name, comp in itertools.product(filenames[:-1], compilers[:]):

        print(f"########################### {name} {comp} ###########################")

        try:
            circ = Circuit()
            parse_r1cs(f"r1cs_files/{name}{comp}.r1cs", circ)

            jsonfile = f"clustering_tests/{test_dir}/{name}{comp}_{clustering}.json"

            fp = open(jsonfile, 'r')
            clusters = json.load(fp)
            fp.close()
        except FileNotFoundError as e:
            print(e)
            continue

        nodes = clusters["nodes"]
        dagnodes = { node["node_id"] : to_dagnode(circ, node) for node in nodes}
        equivalency = list(map(lambda lst : lst[0], clusters["equivalency"]))

        added_inputs = False
        added_output = False
        for node, dagnode in zip(nodes, dagnodes.values()):
            if not set(filter(lambda sig : 0 < sig <= circ.nPubOut, node["signals"])).issubset(dagnode.output_signals): added_output = True
            if not set(filter(lambda sig : circ.nPubOut < sig <= circ.nPubOut + circ.nPrvIn + circ.nPubIn, node["signals"])).issubset(dagnode.input_signals): added_inputs = True

            dagnode.input_signals.update(filter(lambda sig : circ.nPubOut < sig <= circ.nPubOut + circ.nPrvIn + circ.nPubIn, node["signals"]))
            dagnode.output_signals.update(filter(lambda sig : 0 < sig <= circ.nPubOut, node["signals"]))
            # assert set(filter(lambda sig : 0 < sig <= circ.nPubOut, node["signals"])).issubset(dagnode.output_signals), f"{dagnode.output_signals}, {list(filter(lambda sig : 0 < sig <= circ.nPubOut, node['signals']))}"
            # assert set(filter(lambda sig : circ.nPubOut < sig <= circ.nPubOut + circ.nPrvIn + circ.nPubIn, node["signals"])).issubset(dagnode.input_signals), f"{dagnode.output_signals}, {list(filter(lambda sig : circ.nPubOut < sig <= circ.nPubOut + circ.nPrvIn + circ.nPubIn, node['signals']))}"
        print(f"Had to fix outputs: {added_output}, and inputs: {added_inputs}")


        start = time.time()
        # names = ["S1", "S2"]
        # circ = [dagnodes[38].get_subcircuit(), dagnodes[48].get_subcircuit()]
        # in_pair = list(zip(names, circ))
        # coni_pairs, _ = maximum_equivalence(in_pair, debug=True, solver_timeout = 5)
        # print(len(coni_pairs), circ[0].nConstraints)

        # indices = [38, 48, 73, 83, 103, 113]
        # res = pairwise_maximally_equivalent_classes({ ind : dagnodes[ind] for ind in indices}, tol=0.8, solver_timeout=5)
        # print(res)

        # print(len(clusters["equivalency"]), count_ints(map(len, clusters["equivalency"])))
        # classes = maximally_equivalent_classes(dagnodes, tol=0.80, solver_timeout = 5, exit_max_classes=True)
        # print(classes)

        # print(time.time() - start)

        # start = time.time()
        # classes = maximally_equivalent_classes(dagnodes, clusters["equivalency"], clusters["equiv_mappings"], tol=0.80, solver_timeout = 5, exit_max_classes=True)
        # print(classes)
        
        nodes, equivalency = maximally_equivalent_classes(dagnodes, clusters["equivalency"], clusters["equiv_mappings"], solver_timeout = 5)

        print(time.time() - start)
        
