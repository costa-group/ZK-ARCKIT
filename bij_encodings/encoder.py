"Abstract Encoder Class"

from pysat.formula import CNF
from typing import Tuple, Dict, List, Set
from pysat.solvers import Solver

from r1cs_scripts.circuit_representation import Circuit
from bij_encodings.assignment import Assignment

class Encoder():

    def __init__(self):
        pass

    def get_solver(
            self,
            classes:Dict[str, Dict[str, List[int]]],
            in_pair: List[Tuple[str, Circuit]],
            return_signal_mapping: bool = False,
            return_constraint_mapping = False, 
            return_engine: bool = False,
            debug: bool = False,
            formula: CNF = CNF(),
            mapp: Assignment = Assignment(),
            ckmapp: Assignment = None,
            assumptions: Set[int] = set([]),
            signal_info: Dict[str, Dict[int, int]] = None
    ) -> Solver:
        """
        Very basic default
        """
        
        res = self.encode(classes, in_pair, return_signal_mapping, return_constraint_mapping, debug, 
                          formula, mapp, ckmapp, assumptions, signal_info)

        solver = Solver(name = 'cadical195', bootstrap_with=res[0])

        return [solver] + res[1:]

    def encode(
            self,
            classes: Dict[str, Dict[str, List[int]]],
            in_pair: List[Tuple[str, Circuit]],
            return_signal_mapping: bool = False,
            return_constraint_mapping = False, 
            debug: bool = False,
            formula: CNF = CNF(),
            mapp: Assignment = Assignment(),
            ckmapp: Assignment = None,
            assumptions: Set[int] = set([]),
            signal_info: Dict[str, Dict[int, int]] = None
        ) -> CNF:
        pass