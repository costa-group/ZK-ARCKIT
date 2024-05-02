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
            return_engine: bool = False,
            debug: bool = False
    ) -> Solver:
        
        formula, assumptions, mapp = self.encode(classes, in_pair, offset, return_signal_mapping, debug)

        solver = Solver(name = 'cadical195', bootstrap_with=formula)

        res = [solver, assumptions]
        if return_signal_mapping: res.append(mapp)

        return res

    def get_solver(
        self,
        classes: Dict[str, Dict[str, List[int]]],
        in_pair: List[Tuple[str, Circuit]],
        offset: int,
        return_signal_mapping: bool = False,
        debug: bool = False
    ) -> Solver:
            pass