from typing import List, Dict, Iterable
from pysat.formula import CNF
from pysat.card import CardEnc, EncType
from pysat.solvers import Solver
import pysat as ps
import time 
import numpy as np
from functools import reduce

from comparison.compare_circuits import circuit_equivalence
from comparison_testing import get_circuits, shuffle_constraints
from comparison.constraint_preprocessing import hash_constraint, constraint_classes, known_split
from comparison.cluster_preprocessing import circuit_clusters, constraint_cluster_classes, groups_from_clusters
from r1cs_scripts.modular_operations import multiplyP
from r1cs_scripts.constraint import Constraint
from r1cs_scripts.circuit_representation import Circuit
from r1cs_scripts.read_r1cs import parse_r1cs
from bij_encodings.singular_preprocessing import singular_class_preprocessing
from bij_encodings.assignment import Assignment
from bij_encodings.reduced_encoding.red_class_encoder import reduced_encoding_class
from bij_encodings.reduced_encoding.red_natural_encoding import ReducedNaturalEncoder
from bij_encodings.reduced_encoding.red_pseudoboolean_encoding import ReducedPseudobooleanEncoder, pseudoboolean_signal_encoder
from bij_encodings.online_info_passing import OnlineInfoPassEncoder
from bij_encodings.batched_info_passing import BatchedInfoPassEncoder, recluster
from structural_analysis.graph_clustering.degree_clustering import twice_average_degree, ratio_of_signals
from structural_analysis.graph_clustering.signal_equivalence_clustering import naive_removal_clustering, is_signal_equivalence_constraint
from structural_analysis.graph_clustering.clustering_from_list import cluster_from_list
from comparison.static_distance_preprocessing import distances_to_static_preprocessing
from testing_harness import run_affirmative_test
from normalisation import r1cs_norm
import itertools

# REVEAL TEST TIMES (with singular preprocessing)
    # CLASS GEN <1s
    # NEWCLASS  ~30s
    # ENCODING  ~10min
    # SOLVING   ~9s

# NOTE: seems like even turning Reveal into a graph takes forever... 400s + loading so not too long tbh
#        - single iteration (first) of edge_betweeness takes 3000s, no significant speedup likely means this is too slow
#        - think of better algorithm

# REVEAL TEST CLUSTERING
    # naive nx method ~1000s
    # custom alg ~0.5s

# REVEAL GROUPS w/ CLUSTERING
    # no clustering ~7s
    # naive clustering ~12s 
    # better clustering ~13s --> 10x as many singular classes

# REVEAL SOLVING O0 w/ CLUSTERING w/ SINGULAR PREPROCESSING
    # grouping ~11s
    # tot constraints: 44K
    # sing preprocessing ~110s
    # new tot constra: 3.5K
    # encoding time ~19s
    # solving time ~0.1s

# PSEUDOBOOLEAN TESTING
    # filename   :: clausenumber -- max_lit_number
    # PoseidonO0 ::   557K / 86K -- 754.8K / 758.8K
    # RevealO0   ::   699K / 142K -- 1392.8K / 1400.2K

# ADJACENCY TESTING -- using twice_average_degree
    # filename   :: total #constraints -- maxclass #constraints -- preprocess time
    # RevealO1   :: 4381 / 3183 --  1280 / 1280   -- 51s/48s
    # MoveO1     :: 4398 / 3189 --  1280 / 1280   -- 185s/201s
    # BiomebaseO1:: 3901 / 3250 --  768  / 768    -- 48s/51s

# ONLINE PUSH TESTING -- using best clustering
    # filename    ::
    # RevealO1    :: 22s   / 1280
    # RevealO0    :: 29.5s / 905
    # PoseidonO1  :: 0.1s  / 1
    # PoseidonO0  :: 0.2s  / 15
    # MoveO1      :: 27.9s / 1280
    # MoveO0      :: 34s   / 993
    # BiomebaseO1 :: 15s   / 768
    # BiomebaseO0 :: 29.8  / 893

# TODO: investigate some error/misdjudgement with applying the knowledge


# Encoding hits a memory issue since we still have 20K constraints

def cons_eq(C1: Constraint, C2: Constraint):
    if type(C1) == int:
        return C1 == C2

    if C1.A.keys() != C2.A.keys() or C1.B.keys() != C2.B.keys() or C1.C.keys() != C2.C.keys():
        return False

    return all([C1.A[key] == C2.A[key] for key in C1.A.keys()]
            +  [C1.B[key] == C2.B[key] for key in C1.B.keys()]
            +  [C1.C[key] == C2.C[key] for key in C1.C.keys()])

def count_ints(lints : Iterable[int]) -> Dict[int, int]:
    res = {}
    for i in lints:
        res[i] = res.setdefault(i, 0) + 1
    return sorted(res.items())

def get_absmax_lit(clauses):
    return max(map(max, map(lambda x : map(abs, x), clauses)))

def getvars(con: Constraint) -> set:
    return set(con.A.keys()).union(con.B.keys()).union(con.C.keys()).difference(set([0]))
    
if __name__ == '__main__':
    pass

    # circ, circs = get_circuits(
    #     "r1cs_files/test_ecdsaO0.r1cs", seed=56, return_mapping=False
    # )

    # start = time.time()

    # in_pair = list(zip(["S1", "S2"], [circ, circs]))
    # mapp = Assignment()
    # assumptions = set([])
    # formula = CNF()
    # ckmapp = Assignment(assignees=3, link = mapp)
    # signal_info = None

    # clusters = circuit_clusters(in_pair, naive_removal_clustering, calculate_adjacency = True)
    # classes = groups_from_clusters(in_pair, clusters, signal_info, mapp)

    # setup = time.time()
    # print("setup time: ",setup - start)

    # files = ["Poseidon", "Reveal", "Biomebase", "Move"]
    # files = ["test_ecdsa", "test_ecdsa_verify"]
    # optimisation = "O0"

    # encoders = [OnlineInfoPassEncoder, BatchedInfoPassEncoder]
    # encoder_names = ["online_info", "batched_info"]

    # RNG = np.random.default_rng(seed = 42)

    # for file in files:
    #     for encoder, encoder_name in zip(encoders, encoder_names):
    #         seed = int(RNG.integers(low = 1, high = 25565))

    #         print("Testing: ", file + optimisation, encoder_name, "seed = ", seed)
    #         run_affirmative_test(
    #             "r1cs_files/" + file + optimisation + ".r1cs",
    #             "test_results/" + encoder_name + "/" + file + optimisation + ".json",
    #             seed,
    #             None,
    #             naive_removal_clustering,
    #             groups_from_clusters,
    #             None,
    #             encoder,
    #             class_encoding = reduced_encoding_class,
    #             signal_encoding = pseudoboolean_signal_encoder,
    #             debug=True
    #         )



    
