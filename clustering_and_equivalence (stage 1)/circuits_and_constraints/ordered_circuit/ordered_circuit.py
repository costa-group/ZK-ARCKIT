import itertools
import warnings
from functools import reduce
from typing import Iterable, List, Dict, Tuple, Hashable

from circuits_and_constraints.abstract_circuit import Circuit
from circuits_and_constraints.ordered_circuit.ordered_constraint import OrderedConstraint

from utilities.assignment import Assignment

class OrderedCircuit(Circuit):

    @property
    def prime(self) -> int: pass

    @property
    def nConstraints(self) -> int: pass

    @property
    def nWires(self) -> int: pass

    @property
    def constraints(self) -> List[OrderedConstraint]: pass

    @property
    def normalised_constraints(self) -> List[OrderedConstraint]: pass
    
    @property
    def normi_to_coni(self) -> List[int]: pass

    @property
    def nInputs(self) -> int: pass

    @property
    def nOutputs(self) -> int: pass

    def signal_is_input(self, signal: int) -> bool: pass

    def signal_is_output(self, signal: int) -> bool: pass

    def get_signals(self) -> Iterable[int]: pass

    def get_input_signals(self) -> Iterable[int]: pass

    def get_output_signals(self) -> Iterable[int]: pass

    def parse_file(self, file: str) -> None: pass

    def write_file(self, file: str) -> None: pass

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