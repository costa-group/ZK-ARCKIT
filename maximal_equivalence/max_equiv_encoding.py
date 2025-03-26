from typing import List, Dict, Tuple, Set
from pysat.formula import CNF
import itertools
import collections

from r1cs_scripts.circuit_representation import Circuit
from r1cs_scripts.constraint import Constraint
from utilities import _signal_data_from_cons_list, UnionFind, getvars
from bij_encodings.assignment import Assignment
from normalisation import r1cs_norm

def coefficient_only_fingerprinting(circ: Circuit, names: Tuple[str], conspair: Dict[str, List[int]], normspair: Dict[str, Dict[int, List[Constraint]]]) -> Dict[str, Dict[int, List[int]]]:
    
    def cons_to_coef(C: Constraint):
        return tuple(map(lambda part: tuple(part.values()), [C.A, C.B, C.C]))

    classes = {name: {} for name in names}
    coef_hash = Assignment(assignees=1)

    collections.deque(
        maxlen=0, 
        iterable=itertools.starmap(lambda name, coni: classes[name].setdefault(coef_hash.get_assignment(cons_to_coef(circ.constraints[coni])), []).append(coni), 
                                itertools.chain(*map(lambda name: itertools.product([name], conspair[name]), names)))
    )

    return classes


def maximal_equivalence_encoding(circ: Circuit, conspair: Dict[str, List[int]]) -> CNF:
    # fingerprint constraints only on coefficients 
    #   -- its the older version of fingerprinting where we only look at the 

    # then directly move to encoding with the online signal passing as before

    # just to test the smaller versions

    names = conspair.keys()

    normspair = {name : {coni : r1cs_norm(circ.constraints[coni]) for coni in conspair[name]} for name in names}

    classes = coefficient_only_fingerprinting(circ, names, conspair, normspair)

    return classes

