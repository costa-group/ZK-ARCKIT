"""
Idea is to use the simplest signal-only encoding (no constraint logic)
And use Lazy Clause Generation with propagators (pysat.engine) to build the constraint logic as nogoods
"""

from pysat.formula import CNF
from pysat.card import CardEnc, EncType
from pysat.solvers import Solver
from pysat.engines import Propagator
from typing import Tuple, Dict, List
from itertools import product
from functools import reduce
from collections import defaultdict

from normalisation import r1cs_norm
from r1cs_scripts.circuit_representation import Circuit
from bij_encodings.single_cons_options import signal_options
from bij_encodings.assignment import Assignment


def get_solver(
        classes:Dict[str, Dict[str, List[int]]],
        in_pair: List[Tuple[str, Circuit]],
        return_signal_mapping: bool = False,
        debug: bool = False
    ) -> Solver:
    pass

class ConsBijConstraint():
    pass

class ConstraintEngine(Propagator):

    def __init__(self) -> None:

        # Init Constraints
        self.vset = set([])
        self.cons = []
        self.lins = []

        # PreProcess Constraints

        # Init Backtrack handler
        #   Method copied from pysat.engines.BooleanEngine by Alexei Igniatev -- https://github.com/pysathq/pysat/blob/master/pysat/engines.py 
        self.value = {v: None for v in self.vset}
        self.fixed = {v: False for v in self.vset}
        self.trail = []
        self.trlim = []
        self.props = defaultdict([])
        self.qhead = None

        self.decision_level = 0
        self.level = {v: 0 for v in self.vset}


        pass

    def on_assignment(self, lit: int, fixed: bool = False) -> None:
        pass

    def on_new_level(self) -> None:
        pass
    
    def on_backtrack(self, to: int) -> None:
        pass

    def check_model(self, model: List[int]) -> bool:
        pass

    def decide(self) -> int:
        pass

    def propagate(self) -> List[int]:
        pass

    def provide_reason(self, lit: int) -> List[int]:
        pass

    def add_clause(self) -> List[int]:
        pass

def encode(
        classes:Dict[str, Dict[str, List[int]]],
        in_pair: List[Tuple[str, Circuit]],
        return_signal_mapping: bool = False,
        debug: bool = False
    ) -> CNF:
    """
    multi-norm version of previous simple encoder
    """

    #TODO: update to include all seen variables but include assumptions about non-viable ones

    mapp = Assignment()

    all_posibilities = {
        name: {}
        for name, _ in in_pair
    }

    for class_ in classes[in_pair[0][0]].keys():

        left_normed = [
            r1cs_norm(in_pair[0][1].constraints[i])[0] for i in classes[in_pair[0][0]][class_]
        ]

        right_normed = [
            r1cs_norm(in_pair[1][1].constraints[i]) for i in classes[in_pair[1][0]][class_]
        ]

        comparison = product(
            range(len(classes[in_pair[0][0]][class_])), range(len(classes[in_pair[0][0]][class_]))
        )   

        # no constraint logic so can flatten list
        Options = [
            signal_options(left_normed[i], right_normed[j][k])
            for i, j in comparison for k in range(len(right_normed[j]))
        ]

        def extend_opset(opset_possibilities, options):
            # take union of all options

            for name, _ in in_pair:
                for signal in options[name].keys():
                    opset_possibilities[name][signal] = opset_possibilities[name].setdefault(signal, set([])
                                                                                ).union(options[name][signal])
            
            return opset_possibilities
        # union within classes
        class_posibilities = reduce(
            extend_opset,
            Options,
            {
                name: {}
                for name, _ in in_pair
            }
        )

        # intersection accross classes
        for name, _ in in_pair:
            for signal in class_posibilities[name].keys():
                all_posibilities[name][signal] = all_posibilities[name].setdefault(signal, class_posibilities[name][signal]
                                                                      ).intersection(class_posibilities[name][signal])
    # internal consistency
    for (name, _), (oname, _) in zip(in_pair, in_pair[::-1]):
        for lsignal in all_posibilities[name].keys():
            all_posibilities[name][lsignal] = [
                rsignal for rsignal in all_posibilities[name][lsignal]
                if lsignal in all_posibilities[oname][rsignal]
            ]
    
    formula = CNF()

    for name, _ in in_pair:
        for signal in all_posibilities[name].keys():

            lits = [ 
                mapp.get_assignment(signal, pair) if name == in_pair[0][0] else mapp.get_assignment(pair, signal)
                for pair in all_posibilities[name][signal]
            ]

            if len(all_posibilities[name][signal]) == 0:
                # TODO: implement passing false through encoding
                raise AssertionError("Found variable that cannot be mapped to") 

            formula.extend(
                CardEnc.equals(
                    lits,
                    bound = 1,
                    encoding=EncType.pairwise
                )
            )
    
    return (formula, []) if not return_signal_mapping else (formula, [], mapp)


    