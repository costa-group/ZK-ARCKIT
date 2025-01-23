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

    filenames = ["Poseidon", "Reveal", "Biomebase", "Move", "test_ecdsa", "test_ecdsa_verify"]
    compilers = ["O0", "O1", "O2"]

    filenames = filenames[:]
    compilers = compilers[:]

    RNG = np.random.default_rng(312)

    # test_dir = "no_preprocessing/"
    # preprocessing = None

    # TODO: memory optimisation
    test_dir = "official_tests/"
    preprocessing = iterated_adjacency_reclassing

    # test_dir = "method_tests/"

    for test, comp in product(filenames, compilers):

        if test == "Poseidon" and comp == "O2": continue

        print(test, comp, "                                      ")
        file = "r1cs_files/"+ test + comp +".r1cs"
    
        circ = Circuit()
        parse_r1cs(file, circ)
        print(file, circ.nConstraints, circ.nConstraints**2)

        run_affirmative_test(
            file,
            "test_results/" + test_dir + test + comp + "_60min.json",
            int(RNG.integers(0, 25565)),
            None,
            constraint_classes, # groups_from_clusters,
            preprocessing,
            OnlineInfoPassEncoder,
            encoder_kwargs={
                "class_encoding": reduced_encoding_class,
                "signal_encoding": pseudoboolean_signal_encoder
            },
            debug=False,
            time_limit= 60 * 60
        )

    # NOTE: previous slowdowns likely due to overuse of memory bc of not itersection with known info at signal level
        # TODO: investigate weirdly slow encodings of small classes (e.g. 4 x 3)