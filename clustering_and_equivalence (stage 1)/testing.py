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

from circuit_shuffle import get_circuits, shuffle_constraints
from r1cs_scripts.modular_operations import multiplyP
from r1cs_scripts.constraint import Constraint
from r1cs_scripts.circuit_representation import Circuit
from r1cs_scripts.read_r1cs import parse_r1cs
from utilities.iterated_adj_reclassing import iterated_adjacency_reclassing
from utilities.assignment import Assignment
from structural_analysis.clustering_methods.naive.degree_clustering import twice_average_degree, ratio_of_signals
from structural_analysis.clustering_methods.naive.signal_equivalence_clustering import naive_removal_clustering, is_signal_equivalence_constraint
from testing_harness import run_affirmative_test, run_current_best_test
from structural_analysis.utilities.connected_preprocessing import connected_preprocessing
from normalisation import r1cs_norm
from utilities.utilities import count_ints, _signal_data_from_cons_list, getvars
from maximal_equivalence.shortest_minimum_span import shortest_minimum_span
from maximal_equivalence.applied_maximal_equivalence import maximally_equivalent_classes
from structural_analysis.cluster_trees.dag_from_clusters import DAGNode
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
    
    filenames = ["Poseidon", "Reveal", "Biomebase", "Move", "sha256_test512", "test_ecdsa", "test_ecdsa_verify"]
    compilers = ["O0", "O1"]

    clustering = "louvain"
    test_dir = "with_mapping"

    for name, comp in itertools.product(filenames[1:-1], compilers):

        print(f"########################### {name} {comp} ###########################")

        try:
            circ = Circuit()
            parse_r1cs(f"r1cs_files/{name}{comp}.r1cs", circ)

            jsonfile = f"clustering_tests/{test_dir}/{name}{comp}_{clustering}_maxequiv.json"

            fp = open(jsonfile, 'r')
            clusters = json.load(fp)
            fp.close()
        except FileNotFoundError:
            continue

        from utilities import _is_nonlinear

        for node in clusters["nodes"]:
            if len(node["constraints"]) == 1 and not _is_nonlinear(circ.constraints[node["constraints"][0]]) and len(node["successors"]) > 1:
                print(node["constraints"], node["successors"])

        # print(len(clusters["nodes"]))
        # nodes = clusters["nodes"]

        # def node_to_dagnode(node):
        #     return DAGNode(circ, node["node_id"], node["constraints"], set(node["input_signals"]), set(node["output_signals"]))

        # dagnodes = { node["node_id"] : node_to_dagnode(node) for node in nodes }
        
        # results = maximally_equivalent_classes(dagnodes, clusters["equivalency"], clusters["equiv_mappings"], tol=0.8, solver_timeout=5)
        
        # fp = open(f"clustering_tests/{test_dir}/{name}{comp}_{clustering}_maxequiv.json", 'w')
        # json.dump(results, fp, indent=4)
        # fp.close()
