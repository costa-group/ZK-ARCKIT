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

# ---------------------------------------------------------------------------------------------------------------------------------

class ConsBijConstraint():
    """
        This represents the signal clauses for a bijection between some constraints i, j.
        i.e. for every norm in i, j.

        Since all the at most 1 logic is handled in the encoding itself all we care is the at least 1 logic,
            for i, j at least 1 of the k norm forms must be happy with the given encoding.

        The programming logic behind the propagator is relatively straight forward but what clause do we return to justify it,


    """

    def __init__(self, Options: List[dict], mapp: Assignment, in_pair: List[Tuple[str, Circuit]]) -> None:

        self.K = range(len(Options))

        self.in_pair = in_pair

        self.norm_options = Options

        self.valid_norms = [
            all([
                len(self.norm_options[k][name][signal])
                for name, _ in in_pair for signal in self.norm_options[k][name].keys()
            ])
            for k in self.K
        ]

        self.mapp = mapp

        self.signals = [
            reduce(
                lambda acc, k : acc.union(self.norm_options[k][name].keys()),
                self.K,
                set([])
            )
            for name, _ in self.in_pair
        ]

        self.vset = reduce(
            lambda acc, x : acc.union(x),
            chain( *[self.norm_options[k][name].values() for name, _ in self.in_pair for k in self.K] ),
            set([])
        )

        self.expl = {
            v: None
            for v in self.vset
        }

        self.assignment = None # will copy the assignment of the Engine
        self.fmod = None # will store falsified model for when falsified

    def attach_values(self, values) -> None:
        self.assignment = values

    def register_watched(self, to_watch) -> None:
        for var in self.vset:
            to_watch[-var].append(self)

    def propagate(self, lit: int = None) -> List[int]:
        propagated = []
        expl = [v for v in self.vset if self.assignment[v] == -v]

        if lit == None:
            
            # check each signal to see if it has only 1 option left
            curr_options = {
                name: defaultdict(lambda : set([]))
                for name, _ in self.in_pair
            }
            for k, (name, _) in product([k for k in self.K if self.valid_norms[k]], self.in_pair):

                for signal in self.norm_options[k][name].keys():

                    curr_options[name][signal].update([v for v in self.norm_options[k][name][signal] if self.assignment[v] != -v])

            for name, _ in self.in_pair:
                for signal in curr_options[name].keys():

                    if len(curr_options[name][signal]) == 1:
                        p = next(iter(curr_options[name][signal]))

                        propagated.append( p )

                        # Builds LHS of implication about if (curr relevant assignment) -> p
                            #   TODO: think to improve by choosing smaller set
                        self.expl[p] = expl

        elif lit < 0:
            var = abs(lit)
            l, r = self.mapp.get_inv_assignment(var)

            for (name, _), signal in zip(self.in_pair, self.mapp.get_inv_assignment(var)):
                opts = set([])

                for k in self.K:
                    if var not in self.norm_options[k][name][signal]:
                        continue

                    current_options = [v for v in self.norm_options[k][name][signal] if self.assignment[v] != -v and v != var]
                    
                    self.valid_norms[k] = self.valid_norms[k] and len(current_options) != 0

                    if self.valid_norms[k]: opts.update(current_options)
            
                if len(opts) == 1:
                    
                    p = next(iter(opts))
                    propagated.append( p )

                    # Builds LHS of implication about if (curr relevant assignment) -> p
                    #   TODO: think to improve by choosing smaller set
                    self.expl[p] = expl
    
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
    
    def falsified_by(self, model):
        """
        Logic for:
            In both directions,
                at least 1 norm factor
                    must have every signal
                        have at least 1 mapping
        """
        st = any([
            all([
                any( map(lambda v : model[v], self.norm_options[k][name][signal]) )
                for name, _ in self.in_pair for signal in self.norm_options[k][name].keys()
            ])
            for k in self.K
        ])

        if not st:
            self.fmod = [-lit for lit in model if abs(lit) in self.vset] 
        
        return st

    def explain_failure(self):
        return self.fmod
        
        

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
            lambda acc, x : acc.union(x.vset),
            self.cons,
            set([])
        )
        self.watching = defaultdict(lambda: [])

        # TODO: PreProcess Constraints?

        # Model Check handler
        self.falsified = None

        self.solver = None

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
            cs.attach_values(self.value)
    
    def setup_observe(self, solver: Solver) -> None:

        self.solver = solver

        for v in self.vset:
            self.solver.observe(v)

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

    def check_model(self, model: List[int]) -> bool:
        st = True

        for cs in self.cons:
            if cs.falsified_by(model):
                self.falsified = cs
                st = False
                break
        
        return st


    def add_clause(self) -> List[int]:
        if self.falsified is None:
            return []
        
        clause = self.falsified.explain_failure()
        self.falsified = None

        return clause
    

# ---------------------------------------------------------------------------------------------------------------------------------


def get_solver(
        classes:Dict[str, Dict[str, List[int]]],
        in_pair: List[Tuple[str, Circuit]],
        return_signal_mapping: bool = False,
        debug: bool = False
    ) -> Solver:

    mapp = Assignment()
    bijconstraints = []
    false_variables = []

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
            [ signal_options(left_normed[i], right_norm, mapp) for right_norm in right_normed[j] ]
            for i, j in comparison
        ]

        bijconstraints += [ConsBijConstraint(options, mapp, in_pair) for options in Options]

        def extend_opset(opset_possibilities, opset):
            # take union of all options
            for name, _ in in_pair:
                for options in opset:
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

                wrong_rvars = all_posibilities[name].setdefault(signal, class_posibilities[name][signal]
                                                        ).symmetric_difference(class_posibilities[name][signal])
                false_variables.extend( wrong_rvars )
                all_posibilities[name][signal] = all_posibilities[name][signal].intersection(class_posibilities[name][signal])

    # internal consistency
    for (name, _), (oname, _) in zip(in_pair, in_pair[::-1]):
        for lsignal in all_posibilities[name].keys():
            i = name == in_pair[0][0]

            internally_inconsistent = [
                var for var in all_posibilities[name][lsignal]
                if var not in all_posibilities[oname][ mapp.get_inv_assignment(var)[i] ]
            ]

            false_variables.extend( internally_inconsistent )
            all_posibilities[name][lsignal] = all_posibilities[name][lsignal].difference(internally_inconsistent)
    
    formula = CNF()

    for name, _ in in_pair:
        for signal in all_posibilities[name].keys():

            if len(all_posibilities[name][signal]) == 0:
                # TODO: implement passing false through encoding
                raise AssertionError("Found variable that cannot be mapped to") 

            formula.extend(
                CardEnc.equals(
                    all_posibilities[name][signal],
                    bound = 1,
                    encoding=EncType.pairwise
                )
            )  

    solver = Solver(name='cadical195', bootstrap_with=formula)
    engine = ConstraintEngine(bootstrap_with=bijconstraints)

    # TODO: Fix error causing formula to be UNSAT
    solver.connect_propagator(engine)
    engine.setup_observe(solver)

    res = [solver, [-var for var in false_variables]]

    if return_signal_mapping: res.append(mapp)
    return res