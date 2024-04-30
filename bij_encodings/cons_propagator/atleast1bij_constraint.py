
from typing import List, Dict
from functools import reduce
from collections import defaultdict

from bij_encodings.cons_propagator.singlebij_constraint import ConsBijConstraint

class ConsAtLeast1BijConstraint():
    def __init__(self, bijconstraints: List[ConsBijConstraint], in_pair):
        
        self.cons = bijconstraints

        self.watchlist = defaultdict(lambda : [])

        for cs in self.cons:
            for var in cs.vset:
                self.watchlist[var].append(cs)

        self.vset = set(self.watchlist.keys())

        self.assignment = None

    def attach_values(self, values) -> None:

        self.assignment = values

        for cs in self.cons:
            cs.attach_values(values)

    def register_watched(self, to_watch) -> None:
        for var in self.vset:
            to_watch[var].append(self)
        

    def propagate(self, lit: int = None) -> List[int]:
        """
        Need at least 1 value potential bijection to be true.

        Propagate when only 1 option left accross all bijconstraints
        """
        pass

    def justify(self, lit: int) -> List[int]:
        pass

    def abandon(self, lit: int) -> List[int]:
        pass

    def falsified_by(self, model: Dict[int, int]) -> bool:
        pass

    def explain_failure(self):
        pass