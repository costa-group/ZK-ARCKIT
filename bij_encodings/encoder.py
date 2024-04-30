"Abstract Encoder Class"

from pysat.formula import CNF
from typing import Tuple, Dict, List
from pysat.solvers import Solver

from r1cs_scripts.circuit_representation import Circuit

class Encoder():

    def __init__(self):
         pass

    def encode(
        self,
        classes: Dict[str, Dict[str, List[int]]],
        in_pair: List[Tuple[str, Circuit]],
        offset: int,
        return_signal_mapping: bool = False,
        return_engine: bool = False,
        debug: bool = False
    ) -> CNF:
        pass

    def get_solver(
        self,
        classes: Dict[str, Dict[str, List[int]]],
        in_pair: List[Tuple[str, Circuit]],
        offset: int,
        return_signal_mapping: bool = False,
        debug: bool = False
    ) -> Solver:
            pass