from abc import ABC, abstractmethod
from typing import List, Set
import itertools

from circuits_and_constraints.abstract_constraint import Constraint

class ACIRComponent(ABC):

    @property
    @abstractmethod
    def coefficient(self): pass

    @abstractmethod
    def signals(self) -> Set[int]: pass

    @abstractmethod
    def map_signals(self, signal_map: List[int]) -> "ACIRComponent": pass

class ACIRLinear(ACIRComponent):
    
    def __init__(self, coeff, witness):
        self._coefficient = coeff
        self.signal = witness
    
    @property
    def coefficient(self):
        return self._coefficient

    def signals(self):
        return set([self.signal])
    
    def map_signals(self, signal_map: List[int]):
        return ACIRLinear(self.coefficient, signal_map[self.signal])
    
    def __repr__(self):
        return f"{self.coefficient}[{self.signal}]"

class ACIRMultiply(ACIRComponent):
    
    def __init__(self, coeff, witness1, witness2):
        self._coefficient = coeff
        self.signal1 = witness1
        self.signal2 = witness2
    
    @property
    def coefficient(self):
        return self._coefficient
    
    def signals(self):
        return set([self.signal1, self.signal2])

    def map_signals(self, signal_map: List[int]):
        return ACIRLinear(self.coefficient, signal_map[self.signal1], signal_map[self.signal2])

    def __repr__(self):
        return f"{self.coefficient}[{self.signal1}.{self.signal2}]"

class ACIRConstant(ACIRComponent):
    
    def __init__(self, coeff):
        self._coefficient = coeff
    
    @property
    def coefficient(self):
        return self._coefficient

    def signals(self):
        return set([])
    
    def map_signals(self, signal_map):
        return self
    
    def __repr__(self):
        return f"{self.coefficient}"

class ACIRConstraint(Constraint):
    
    def __init__(self):
        # TODO: maybe split this up into multiple parts if it helps
        self.parts: List[ACIRComponent] = []

    def __init__(self, parts):
        # TODO: maybe split this up into multiple parts if it helps
        self.parts: List[ACIRComponent] = parts

    def add_component(self, component: ACIRComponent) -> None:
        self.parts.append(component)
        
    def signals(self) -> Set[int]:
        return set(itertools.chain.from_iterable(map(lambda part : part.signals(), self.parts)))
    
    def signal_map(self, signal_map: List[int]) -> "ACIRConstraint":
        return ACIRConstraint()
    
    def normalisation_choices(self):
        raise NotImplementedError

    def normalise(self):
        raise NotImplementedError
    
    def fingerprint(self, signal_to_fingerprint):
        raise NotImplementedError
    
    def is_nonlinear(self):
        return any(map(lambda part : type(part) == ACIRMultiply, self.parts))
    
    def __repr__(self):
        return f"ACIRConstraint({self.parts})"


def parse_acir_constraint(json: dict) -> ACIRConstraint:

    cons = ACIRConstraint()

    for key, value in json.items():

        match key:

            case "linear": cons.parts.extend(map(lambda part : ACIRLinear(part["coeff"], part["witness"]), value))

            case "mul": cons.parts.extend(map(lambda part: ACIRMultiply(part["coeff"], part["witness1"], part["witness2"]), value))

            case "constant": 
                if int(value) != 0: cons.add_component(ACIRConstant(int(value)))

            case _: raise TypeError(f"Unknown ACIRComponent type {key}")
    
    return cons
