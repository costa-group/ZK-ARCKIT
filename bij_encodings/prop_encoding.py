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

# ---------------------------------------------------------------------------------------------------------------------------------

class ConsBijConstraint():
    """
        This represents the signal clauses for a bijection between constraints i, j.
        i.e. for every norm in i, j.

        Since all the at most 1 logic is handled in the encoding itself all we care is the at least 1 logic,
            for i, j at least 1 of the k norm forms must be happy with the given encoding.

        The programming logic behind the propagator is relatively straight forward but what clause do we return to justify it,


    """
    # TODO: handle falsification for check model

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

        self.signals = [
            reduce(
                lambda acc, k : acc.union(self.possible_norms[i][k].keys()),
                self.K,
                set([])
            )
            for i in range(2)
        ]

        self.vset = reduce(
            lambda acc, x : acc.union(x),
            chain( *[self.possible_norms[i][k].values() for i in range(2) for k in self.K] ),
            set([])
        )

        self.expl = {
            v: None
            for v in self.vset
        }

        self.assignment = None # will copy the assignment of the Engine

    def attach_values(self, values) -> None:
        self.assignment = values

    def register_watched(self, to_watch) -> None:
        for var in self.vset:
            to_watch[-var].append(self)

    def propagate(self, lit: int) -> List[int]:
        propagated = []
        var = abs(lit)
        l, r = self.mapp.inv_assignment(var)

        # If lit > 0, then we don't do anything
        if lit < 0:
            
            for i, signal in [(0, l, r), (1, r, l)]:
                opts = set([])

                for k in self.K:
                    if var not in self.possible_norms[i][k][signal]:
                        continue

                    current_options = [v for v in self.possible_norms[i][k][signal] if self.assignment[v] != -v and v != var]
                    
                    self.valid_norms[i][k] = self.valid_norms[i][k] and len(current_options) != 0

                    if self.valid_norms[i][k]: opts = opts.union(current_options)
            
                if len(opts) == 1:
                    
                    p = next(iter(opts))
                    propagated.append( p )

                    # Builds LHS of implication about if (curr relevant assignment) -> p
                    #   TODO: think to improve by choosing smaller set
                    self.expl[p] = [-v for v in self.vset if self.assignment[v] is not None]
    
        return propagated
    
    def propagated(self) -> List[int]:

        propagated = []

        # check each signal to see if it has only 1 option left
        for i in range(2):

            for signal in self.signals[i]:

                opts = reduce(
                    lambda acc, k : acc.union(  [v for v in self.possible_norms[i][k].get(signal, []) if self.assignment[v] != -v]  ) if self.valid_norms[i][k] else acc,
                    self.K,
                    set([])
                )

                if len(opts) == 1:
                    p = next(iter(opts))
                    propagated.append( p )

                    # Builds LHS of implication about if (curr relevant assignment) -> p
                        #   TODO: think to improve by choosing smaller set
                    self.expl[p] = [-v for v in self.vset if self.assignment[v] is not None]
        
        return propagated
        

    def unassign(self, lit: int) -> List[int]:
        var = abs(lit)

        while len(self.to_undo[lit]) > 0:
            i, k, signal = self.to_undo.pop()
            self.possible_norms[i][k][signal].add(var)

            if not self.valid_norms[i][k] and all(map(len, self.possible_norms[i][k].values())):
                self.valid_norms[i][k] = True

    def justify(self, lit) -> List[int]:
        return self.expl[abs(lit)] # propagator will never negate a variable but just in case take abs

    def abandon(self, lit) -> List[int]:
        self.expl[abs(lit)].clear() # propagator will never negate a variable but just in case take abs
    
    def is_falsified(self, model):
        pass

# ---------------------------------------------------------------------------------------------------------------------------------


class ConstraintEngine(Propagator):
    """
    A modified version of the BooleanEngine by Alexei Ignatiev
        available at: https://github.com/pysathq/pysat/blob/master/pysat/engines.py#L711 
    """

    def __init__(self, bootstrap_with: List[ConsBijConstraint] = []) -> None:

        # Init Constraints
        self.cons = bootstrap_with
        self.vset = reduce(
            lambda acc, x : acc.union(x),
            self.cons,
            set([])
        )
        self.watching = defaultdict(lambda: [])

        # TODO: PreProcess Constraints?

        # Init Backtrack handler
        self.value = {v: None for v in self.vset}
        self.fixed = {v: False for v in self.vset}
        self.trail = []
        self.trlim = []
        self.props = defaultdict(lambda: [])
        self.origin = defaultdict(lambda: None)
        self.qhead = None
        
        for cs in self.cons:
            # give constraints access to following
            cs.register_watched(self.watching)
            cs.attach_values(self.values)

    def on_assignment(self, lit: int, fixed: bool = False) -> None:
        
        var = abs(lit)
        
        if self.qhead is None:
            self.qhead = len(self.trail)
        
        self.trail.append(lit)

        if fixed:
            self.fixed[var] = True

    def on_new_level(self) -> None:
        
        self.trlim.append(len(self.trail))
    
    def on_backtrack(self, to: int) -> None:
        while len(self.trlim) > to:
            while len(self.trail) > self.trlim[-1]:
                lit = self.trail.pop()
                var = abs(lit)

                if self.value[var] is not None and not self.fixed[var]:
                    for cs in self.watching[lit]:
                        cs.unassign(lit)
                    
                    self.value[var] = None

                for l in self.props[lit]:
                    self.origin[l].abandon(l)
                    self.origin[l] = None
                self.props[lit] = None
            self.trlim.pop()

        self.qhead = None                 

    def check_model(self, model: List[int]) -> bool:
        # TODO
        pass

    def propagate(self) -> List[int]:
        results = []

        if self.qhead is not None:
            while self.qhead < len(self.trail):
                lit = self.trail[self.qhead]

                if self.origin[-lit] is not None:
                    break
                
                self.value[abs(lit)] = lit

                for cs in self.watching[lit]:
                    propagated = cs.propagate(lit)

                    for l in propagated:
                        if self.origin[l] is None:
                            self.origin[l] = cs
                            results.append(l)
                            self.props[lit].append(l)
            
            self.qhead += 1

        else:

            for cs in self.cons:
                propagated = cs.propagate()

                for l in propagated:
                    if self.origin[l] is None:
                        self.origin[l] = cs
                        results.append(l)

        return results


    def provide_reason(self, lit: int) -> List[int]:
        return [lit] + self.origin[lit].justify(lit)

    def add_clause(self) -> List[int]:
        # TODO
        pass

# ---------------------------------------------------------------------------------------------------------------------------------

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


    