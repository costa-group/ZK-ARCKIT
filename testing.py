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
from comparison.cluster_preprocessing import circuit_clusters, constraint_cluster_classes, groups_from_clusters
from r1cs_scripts.modular_operations import multiplyP
from r1cs_scripts.constraint import Constraint
from r1cs_scripts.circuit_representation import Circuit
from r1cs_scripts.read_r1cs import parse_r1cs
from bij_encodings.preprocessing.singular_preprocessing import singular_class_preprocessing
from bij_encodings.preprocessing.iterated_adj_reclassing import iterated_adjacency_reclassing
from bij_encodings.assignment import Assignment
from bij_encodings.reduced_encoding.red_class_encoder import reduced_encoding_class
from bij_encodings.reduced_encoding.red_natural_encoding import ReducedNaturalEncoder
from bij_encodings.reduced_encoding.red_pseudoboolean_encoding import ReducedPseudobooleanEncoder, pseudoboolean_signal_encoder
from bij_encodings.online_info_passing import OnlineInfoPassEncoder
from bij_encodings.batched_info_passing import BatchedInfoPassEncoder, recluster
from structural_analysis.graph_clustering.degree_clustering import twice_average_degree, ratio_of_signals
from structural_analysis.graph_clustering.signal_equivalence_clustering import naive_removal_clustering, is_signal_equivalence_constraint
from structural_analysis.graph_clustering.clustering_from_list import cluster_from_list
from structural_analysis.graph_clustering.topological_flow_clustering import circuit_topological_clusters
from comparison.static_distance_preprocessing import distances_to_static_preprocessing
from testing_harness import run_affirmative_test, run_current_best_test
from structural_analysis.connected_preprocessing import connected_preporcessing
from normalisation import r1cs_norm
from utilities import count_ints, _signal_data_from_cons_list, getvars
from comparison.static_distance_preprocessing import _distances_to_signal_set
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

def get_absmax_lit(clauses):
    return max(map(max, map(lambda x : map(abs, x), clauses)))

    
if __name__ == '__main__':

    # filenames = ["Reveal", "Biomebase", "Move"]
    # compilers = ["O0", "O1", "O2"]
    # RNG = np.random.default_rng(468)

    # for test, comp in product(filenames, compilers):

    #     print(test, comp)
    #     file = "r1cs_files/"+ test + comp + ".r1cs"

    #     run_affirmative_test(
    #         file,
    #         "test_results/iterated_reclassing/" + test + comp + ".json",
    #         int(RNG.integers(0, 25565)),
    #         None,
    #         naive_removal_clustering if comp == "O0" else twice_average_degree,
    #         groups_from_clusters,
    #         iterated_adjacency_reclassing,
    #         OnlineInfoPassEncoder,
    #         encoder_kwargs={
    #             "class_encoding": reduced_encoding_class,
    #             "signal_encoding": pseudoboolean_signal_encoder
    #         },
    #         debug=False
    #     )

    # TODO: maybe integrate idea into a re-clustering step?

    # TODO: at O1 starts slowing down but then finishes
        #   at O0 starts slowing down for seemingly no discernable reason 
        #   (likely memory but task manager shows very little disk usage... until ctrl+c then spike)
        #   need to look into improving the memory still I suspect
    
    run_current_best_test(
        "r1cs_files/test_ecdsaO0.r1cs",
        "r1cs_files/test_ecdsaO0.r1cs",
        "test_results/iterated_reclassing/ecdsaO0.json",
        "O0"
    )

    # filename = "r1cs_files/RevealO0.r1cs"

    # in_pair, cmapp = get_circuits(filename, seed=56, return_cmapping=True)

    # for _, c in in_pair: connected_preporcessing(c)

    # signal_to_distance = {
    #     name: {
    #         sourcename: _distances_to_signal_set(circ.constraints, source)
    #         for sourcename, source in [("input", range(circ.nPubOut+1, circ.nPubOut + circ.nPrvIn + circ.nPubIn + 1)), ("output", range(1, circ.nPubOut+1))]
    #     }
    #     for name, circ in in_pair
    # }

    # clusters = circuit_clusters(in_pair, naive_removal_clustering)

    # classes = groups_from_clusters(in_pair, clusters)

    # start = time.time()

    # post_classes = iterated_adjacency_reclassing(in_pair, classes)

    # print(time.time() - start)

    # print(count_ints(map(len, classes["S1"].values())))
    # print(count_ints(map(len, post_classes["S1"].values())))

    # origin = classes["S1"]["*2112"][0]
    # print(origin)

    # con = in_pair[0][1].constraints[origin]
    
    # # con.print_constraint_terminal()
    # # print(hash_constraint(con, "S1", None, None, signal_to_distance))

    # _, signal_to_coni = _signal_data_from_cons_list(in_pair[0][1].constraints)

    # con_to_other_coni = {v : signal_to_coni[v] for v in  getvars(con)}
    # print(con_to_other_coni)

    # for coni in filter(lambda x : x != origin, itertools.chain(*con_to_other_coni.values())):
    #     for key, item in classes["S1"].items():
    #         if coni in item: 
    #             print(coni, key)
    #             break



    # clusters = circuit_clusters(in_pair, naive_removal_clustering)

    # classes = groups_from_clusters(in_pair, clusters)

    # print(count_ints(map(len, classes["S1"].values())))

    # *2112
    # 4788

    # TODO: we have proof of runs, but it doesn't seem useful right now