from typing import List, Dict, Iterable
from pysat.formula import CNF
from pysat.card import CardEnc, EncType
from pysat.pb import PBEnc
from pysat.solvers import Solver
import pysat as ps
import time 
from functools import reduce

from comparison_testing import get_circuits, shuffle_constraints
from comparison.constraint_preprocessing import hash_constraint, constraint_classes
from comparison.cluster_preprocessing import circuit_clusters, constraint_cluster_classes, groups_from_clusters
from r1cs_scripts.modular_operations import multiplyP
from r1cs_scripts.constraint import Constraint
from r1cs_scripts.circuit_representation import Circuit
from r1cs_scripts.read_r1cs import parse_r1cs
from bij_encodings.singular_preprocessing import singular_class_preprocessing
from bij_encodings.assignment import Assignment
from bij_encodings.red_natural_encoding import ReducedNaturalEncoder
from bij_encodings.red_pseudoboolean_encoding import ReducedPseudobooleanEncoder
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

# REVEAL SOLVING w/ CLUSTERING w/ SINGULAR PREPROCESSING
    # grouping ~11s
    # tot constraints: 44K
    # sing preprocessing ~110s
    # new tot constra: 3.5K
    # encoding time ~19s
    # solving time ~0.1s

# PSEUDOBOOLEAN TESTING
    # filename   :: clausenumber -- max_lit_number
    # PoseidonO0 ::   557K / 86K -- 754.8K / 758.8K
    # Revealo0   ::   699K / 142K -- 1392.8K / 1400.2K


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
    
if __name__ == '__main__':
    filename = "r1cs_files/RevealOO.r1cs"

    circ, circs, mapp, cmapp = get_circuits(filename, seed = 42, 
        const_factor=True, shuffle_sig=True, shuffle_const=True,
        return_mapping=True, return_cmapping=True)

    in_pair = [("S1", circ), ("S2", circs)]

    # n = 5

    # g = CNF()

    # f = PBEnc.atmost(list(range(1,n+1)), encoding=1)
    # # g = CardEnc.atmost(list(range(1, n+1)), encoding=EncType.pairwise)

    # print(len(f.clauses), get_absmax_lit(f.clauses))
    # # print(len(g.clauses), get_absmax_lit(g.clauses))

    # g.extend(list(map(lambda y: list(map(lambda x : x,y)), f)))

    # solver = Solver(name = 'cadical195', bootstrap_with=g)

    from normalisation import r1cs_norm
    from structural_analysis.graph_clustering.signal_equivalence_clustering import naive_all_removal, is_signal_equivalence_constraint, naive_removal_clustering

    start = time.time()

    clusters = circuit_clusters(in_pair)
    classes = groups_from_clusters(in_pair, clusters)

    post_classes = time.time()

    print("grouping time: ",post_classes - start)

    print("total num of constraint: ",sum(list(map(len, classes["S1"].values()))))

    mapp = Assignment()
    cmapp = Assignment(assignees = 3, link = mapp)
    assumptions = set([])
    formula = CNF()

    # TODO: let singular_class_preprocessing utilise clustering info
    # new_classes, known_info = classes, None
    new_classes, known_info = singular_class_preprocessing(
        in_pair, classes, clusters,
        mapp, cmapp, assumptions, formula
    )

    post_new_classes = time.time()

    print("singular preprocessing time: ",post_new_classes - post_classes)

    print("new total num of constraint: ",sum(list(map(len, new_classes["S1"].values()))))

    formula, assumptions = ReducedPseudobooleanEncoder().encode(
        new_classes, in_pair, 0, False, False, True, formula, mapp, cmapp, assumptions, known_info
    )

    solver = Solver(name='cadical195', bootstrap_with=formula)

    encoding = time.time()

    print(len(formula.clauses), get_absmax_lit(formula.clauses), "                                                           ")

    print("encoding time: ",encoding - post_new_classes)

    result = solver.solve(assumptions)

    solving = time.time()

    print("solving time: ",solving - encoding)

    print(result)



    
