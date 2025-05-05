"Abstract Encoder Class"

from pysat.formula import CNF
from typing import Tuple, Dict, List, Set
from pysat.solvers import Solver

from r1cs_scripts.circuit_representation import Circuit
from utilities.assignment import Assignment

class Encoder():
    """
    Abstract Incoder Class
    """

    def __init__(self):
        pass

    def get_solver(
            self,
            in_pair: List[Tuple[str, Circuit]],
            classes: Dict[str, Dict[str, List[int]]],
            clusters: Dict[str, Dict[str, Dict[int, Set[int]]]] = None,
            return_signal_mapping: bool = False,
            return_constraint_mapping: bool = False, 
            return_encoded_classes: bool = False,
            return_engine: bool = False,
            debug: bool = False,
            formula: CNF = CNF(),
            mapp: Assignment = Assignment(),
            ckmapp: Assignment = None,
            assumptions: Set[int] = set([]),
            signal_info: Dict[str, Dict[int, int]] = None
    ) -> Solver:
        """
        Very basic default solver return function
        """
        
        res = self.encode(in_pair, classes, clusters, return_signal_mapping, return_constraint_mapping, return_encoded_classes, debug, 
                          formula, mapp, ckmapp, assumptions, signal_info)

        solver = Solver(name = 'cadical195', bootstrap_with=res[0])

        return [solver] + res[1:]

    def encode(
            self,
            in_pair: List[Tuple[str, Circuit]],
            classes: Dict[str, Dict[str, List[int]]],
            clusters: Dict[str, Dict[str, Dict[int, Set[int]]]] = None,
            return_signal_mapping: bool = False,
            return_constraint_mapping: bool = False,
            return_encoded_classes: bool = False, 
            debug: bool = False,
            formula: CNF = CNF(),
            mapp: Assignment = Assignment(),
            ckmapp: Assignment = None,
            assumptions: Set[int] = set([]),
            signal_info: Dict[str, Dict[int, int]] = None
        ) -> CNF:
        """
        encode an input into a CNF formula
        """
        pass