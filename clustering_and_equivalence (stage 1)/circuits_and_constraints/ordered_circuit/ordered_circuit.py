import itertools
import warnings
from functools import reduce
from typing import Iterable, List, Dict, Tuple, Hashable

from circuits_and_constraints.abstract_circuit import Circuit
from circuits_and_constraints.ordered_circuit.ordered_constraint import OrderedConstraint

from utilities.assignment import Assignment

class OrderedCircuit(Circuit):

    def __init__(self):
        self._constraints = []
        self._normalised_constraints = []
        self._normi_to_coni = []

        self._prime_number = None
        self._nWires = None
        self.inputs = []
        self.outputs = []
        self._nConstraints = None

    @property
    def prime(self) -> int:
        return self._prime_number

    @property
    def nConstraints(self) -> int:
        return self._nConstraints

    @property
    def nWires(self) -> int:
        return self._nWires

    @property
    def constraints(self) -> List[OrderedConstraint]:
        return self._constraints

    @property
    def normalised_constraints(self) -> List[OrderedConstraint]: 
        return self._normalised_constraints
    
    @property
    def normi_to_coni(self) -> List[int]: 
        return self._normi_to_coni

    @property
    def nInputs(self) -> int:
        return len(self.inputs)

    @property
    def nOutputs(self) -> int:
        return len(self.outputs)

    def signal_is_input(self, signal: int) -> bool: 
        return signal in self.inputs

    def signal_is_output(self, signal: int) -> bool: 
        return signal in self.outputs

    def get_signals(self) -> Iterable[int]: 
        return range(0, self.nWires)

    def get_input_signals(self) -> Iterable[int]: 
        return self.inputs

    def get_output_signals(self) -> Iterable[int]: 
        return self.outputs

    def parse_file(self, file: str) -> None:
        raise NotImplementedError

    def write_file(self, file: str) -> None:
        raise NotImplementedError

    # now required constraints_to_fingerprint provided to be able to fingerprint on an aribtrary list of constraints not just the norms
    def fingerprint_signal(self, signal: int, constraints_to_fingerprint: List[OrderedConstraint], normalised_constraint_fingerprints: List[int], prev_signal_to_fingerprint: Dict[int, Hashable], signal_to_normi: List[List[int]]) -> Hashable: pass

    def take_subcircuit(self, constraint_subset: List[int], input_signals: List[int] | None = None, output_signals: List[int] | None = None, signal_map: Dict[int, int] | None = None): pass

    @staticmethod
    def encode_single_norm_pair(
        names: List[str],
        norms: List[OrderedConstraint],
        is_ordered: bool,
        signal_pair_encoder: Assignment,
        signal_to_fingerprint: Dict[str, List[int]],
        fingerprint_to_signals: Dict[str, Dict[int, List[int]]],
        is_singular_class: bool = False
    ): pass

    @staticmethod
    def singular_class_requires_additional_constraints() -> bool: pass