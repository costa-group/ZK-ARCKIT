from typing import List, Set, Dict, Tuple
import itertools

from circuits_and_constraints.abstract_constraint import Constraint
from normalisation import divisionNorm, divideP

class ACIRConstraint(Constraint):
    
    def __init__(self, mult: Dict[Tuple[int, int], int], linear: Dict[int, int], constant: int, prime: int):
        # TODO: maybe split this up into multiple parts if it helps
        self.mult = mult
        self.linear = linear
        self.constant = constant
        self.p = prime

    def signals(self) -> Set[int]:
        return set(itertools.chain.from_iterable(map(lambda part : part.signals(), self.parts)))
    
    def signal_map(self, signal_map: List[int]) -> "ACIRConstraint":
        return ACIRConstraint(
            mult = {tuple(sorted(map(signal_map.__getitem__, k))) : v for k, v in self.mult.items()},
            linear= {signal_map[k] : v for k, v in self.linear.items()},
            constant=self.constant,
            prime=self.p
        )
    
    def normalisation_choices(self):

        if self.constant != 0: return [self.constant]
        elif len(self.mult) > 0: return divisionNorm(list(self.mult.values()), self.p, early_exit=True, select=True)
        else: return divisionNorm(list(self.linear.values()), self.p, early_exit=True, select=True)

    def normalise(self):
        return [
                ACIRConstraint(
                    mult = {k : v for v, k in sorted(itertools.starmap(lambda k, v : (divideP(v, divisor, self.p), k), self.mult.items()))},
                    linear = {k : v for v, k in sorted(itertools.starmap(lambda k, v : (divideP(v, divisor, self.p), k), self.linear.items()))},
                    constant = divideP(self.constant, divisor, self.p),
                    prime = self.p
                ) for divisor in self.normalisation_choices()
            ]
    
    def fingerprint(self, signal_to_fingerprint):
        raise NotImplementedError
    
    def is_nonlinear(self):
        return len(self.mult) > 0
    
    def __repr__(self):
        return f"ACIRConstraint({self.mult}, {self.linear}, {self.constant})"


def parse_acir_constraint(json: dict, prime: int) -> ACIRConstraint:
    ## Assumes each witness appears in each part at most once

    cons = ACIRConstraint(mult={}, linear = {}, constant=0, prime=prime)

    for key, value in json.items():
        match key:

            case "linear": cons.linear = {part["witness"] : int(part["coeff"]) for part in value}

            case "mul": cons.mult = {tuple(sorted(map(int, [part["witness1"], part["witness2"]]))) : int(part["coeff"]) for part in value}

            case "constant": 
                if int(value) != 0: cons.constant = int(value)

            case _: raise TypeError(f"Unknown ACIR constraint type {key}")
    
    return cons
