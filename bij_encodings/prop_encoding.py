"""
Idea is to use the simplest signal-only encoding (no constraint logic)
And use Lazy Clause Generation with propagators (pysat.engine) to build the constraint logic as nogoods
"""

from pysat.formula import CNF
from pysat.card import CardEnc, EncType
from pysat.solvers import Solver
from pysat.engines import Propagator
from typing import Tuple, Dict, List
from itertools import product, chain
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
    """
        This represents the signal clauses for a bijection between constraints i, j.
        i.e. for every norm in i, j.

        Since all the at most 1 logic is handled in the encoding itself all we care is the at least 1 logic,
            for i, j at least 1 of the k norm forms must be happy with the given encoding.

        The programming logic behind the propagator is relatively straight forward but what clause do we return to justify it,

    """

    def __init__(self, i: int, j: int, Options: List[dict], mapp: Assignment, in_pair: List[Tuple[str, Circuit]]) -> None:

        self.info = (i, j)
        self.K = range(len(Options))

        # TODO: get magic string out of there
        (name1, _), (name2, _) = in_pair

        # split by name and convert to mapping
        self.possible_norms = [
            [
                { 
                    key: set(map(
                        lambda pair : mapp.get_assignment(key, pair) if name == in_pair[0][0] else mapp.get_assignment(pair, key),
                        options[name][key]
                    )) 
                    for key in options[name].keys()
                }
                for options in Options
            ]
            for name, _ in in_pair
        ]

        self.valid_norms = [
            [
                all(map(len, self.possible_norms[i][k].values())) # checks if every len is > 0, i.e. every signal has a potential match
                for k in self.K
            ]
            for i in range(2)
        ]

        self.mapp = mapp

        self.vset = reduce(
            lambda acc, x : acc.union(x),
            chain( *[self.possible_norms[i][k].values() for i in range(2) for k in self.K] ),
            set([])
        )

        self.to_undo = {
            v: []
            for v in self.vset
        }

        self.assignment = None # will copy the assignment of the Engine

    def attach_values(self, values) -> None:
        self.assignment = values

    def register_watched(self, to_watch) -> None:
        for var in self.vset:
            to_watch[var].append(self)

    def propagate(self, lit: int) -> List[int]:
        propagated = []
        var = abs(lit)
        l, r = self.mapp.inv_assignment(var)

        # update 
        if lit < 0:
            
            for i, signal in [(0, l, r), (1, r, l)]:
                opts = set([])

                for k in self.K:
                    if var not in self.possible_norms[i][k][signal]:
                        continue
                    
                    self.to_undo[var].append((i, k, signal))
                    self.possible_norms[i][k][signal].remove(var)
                    self.valid_norms[i][k] = self.valid_norms[i][k] and len(self.possible_norms[i][k][signal]) != 0

                    if self.valid_norms[i][k]: opts = opts.union(self.possible_norms[i][k][signal])
            
                if len(opts) == 1:
                    
                    propagated.append( next(iter(opts)) )
                    #TODO: be able to justify
    
        return propagated
    
    def propagated(self) -> List[int]:

        propagated = []

        for i, var in product(range(2), filter(lambda x : self.assignment[x] is None, self.vsets)):
            
            opts = reduce(
                lambda acc, k : acc.union(self.possible_norms[i][k][var]) if self.valid_norms[i][k] else acc,
                self.K,
                set([])
            )

            if len(opts) == 1:
                propagated.append( next(iter(opts)) )
                #TODO: be able to justify
        
        return propagated
        

    def unassign(self, lit: int) -> List[int]:
        var = abs(lit)

        while len(self.to_undo[var]) > 0:
            i, k, signal = self.to_undo.pop()
            self.possible_norms[i][k][signal].add(var)

            if not self.valid_norms[i][k] and all(map(len, self.possible_norms[i][k].values())):
                self.valid_norms[i][k] = True

    def justify(self, lit) -> List[int]:
        pass

    def abandon(self, lit) -> List[int]:
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


    