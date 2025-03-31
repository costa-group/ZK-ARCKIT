
from typing import List
from functools import reduce
from collections import defaultdict

from pysat.solvers import Solver
from pysat.engines import Propagator

from bij_encodings.cons_propagator.singlebij_constraint import ConsBijConstraint

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

        model_ = defaultdict(lambda: None)
        for lit in model:
            model_[abs(lit)] = lit

        curr = 0

        for cs in self.cons:
            curr += 1

            if not cs.falsified_by(model_):
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