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
from maximal_equivalence.max_equiv_encoding import maximal_equivalence_encoding
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

    
if __name__ == '__main__':

    filenames = ["Poseidon", "Reveal", "Biomebase", "Move", "sha256", "test_ecdsa", "test_ecdsa_verify"]
    compilers = ["O0", "O1"]

    clustering = "louvain"
    test_dir = "official"

    for name, comp in itertools.product(filenames[:-1], compilers):

        print(f"########################### {name} {comp} ###########################")

        try:
            circ = Circuit()
            parse_r1cs(f"r1cs_files/{name}{comp}.r1cs", circ)

            jsonfile = f"clustering_tests/{test_dir}/{name}{comp}_{clustering}.json"

            fp = open(jsonfile, 'r')
            clusters = json.load(fp)
            fp.close()
        except FileNotFoundError:
            continue

        print(len(clusters["nodes"]))

        num_in_core = map(len, map(lambda node : shortest_minimum_span(circ, node["constraints"], node["signals"]), clusters["nodes"]))
        pairs = zip(map(lambda node : len(node["constraints"]), clusters["nodes"]), num_in_core)
        
        print(count_ints(pairs))
