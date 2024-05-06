"Abstract Encoder Class"

from pysat.formula import CNF
from typing import Tuple, Dict, List
from pysat.solvers import Solver

from r1cs_scripts.circuit_representation import Circuit

class Encoder():

    def __init__(self):
        pass

    def get_solver(
            self,
            classes:Dict[str, Dict[str, List[int]]],
            in_pair: List[Tuple[str, Circuit]],
            offset: int,
            return_signal_mapping: bool = False,
            return_constraint_mapping = False, 
            return_engine: bool = False,
            debug: bool = False
    ) -> Solver:
        
        res = self.encode(classes, in_pair, offset, return_signal_mapping, return_constraint_mapping, debug)

        solver = Solver(name = 'cadical195', bootstrap_with=res[0])

        return [solver] + res[1:]

    def encode(
            self,
            classes: Dict[str, Dict[str, List[int]]],
            in_pair: List[Tuple[str, Circuit]],
            offset: int,
            return_signal_mapping: bool = False,
            return_constraint_mapping = False, 
            debug: bool = False
        ) -> CNF:
        pass