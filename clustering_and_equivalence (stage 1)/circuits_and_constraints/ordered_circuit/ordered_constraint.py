import itertools
from collections import deque
from typing import Set, List, Tuple, Hashable, Dict
from circuits_and_constraints.abstract_constraint import Constraint

from r1cs_scripts.modular_operations import divideP

class OrderedConstraint(Constraint):
    ## For this constraint the order of terms in the polynomial are set, but the order of the signals in the keys is determined by the flag.

    def __init__(self, keys: List[List[int] | Set[int]], values: List[int], constant: int, prime: int, ordered_signals: bool = False):
        self.p = prime
        self.ordered_signals = ordered_signals
        
        self.keys = keys
        self.values = values
        self.constant = constant
        
    def normalise(self) -> List["OrderedConstraint"]:
        # normalises the first coefficient to be one
        return OrderedConstraint(self.keys, list(map(lambda x : divideP(x, self.values[0], self.p), self.values)), divideP(self.constant, self.values[0], self.p), self.p, ordered_signals=self.ordered_signals) 

    def normalisation_choices(self) -> List[int]:
        # normalises the first coefficient to be one
        return self.values[0]

    def signals(self) -> Set[int]:
        return set(itertools.chain.from_iterable(self.keys))

    def fingerprint(self, signal_to_fingerprint: List[int]) -> Hashable:
        return (
            (( (lambda x : tuple(x if self.ordered_signals else sorted(x)))(map(signal_to_fingerprint.__getitem__, key)), val )
            for key, val in zip(self.keys, self.values)), 
            self.constant
        )

    def is_nonlinear(self) -> bool:
        return any(map(lambda x : len(x) > 1))

    def get_coefficients(self) -> Hashable:
        return (tuple(self.values), self.constant)
    
    def signal_map(self, signal_map: List[int]) -> "OrderedConstraint":
        return OrderedConstraint(
            keys = [(list if self.ordered_signals else set)(map(signal_map.__getitem__, term)) for term in self.keys],
            values = self.values,
            constant = self.constant,
            prime = self.p,
            ordered_signals = self.ordered_signals
        )