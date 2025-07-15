from abc import ABC, abstractmethod
from typing import Iterable, Hashable, List, Dict
import warnings
from collections import deque
import itertools

from circuits_and_constraints.abstract_constraint import Constraint
from utilities.assignment import Assignment

class Circuit(ABC):

    @property
    @abstractmethod
    def prime(self) -> int: pass

    @property
    @abstractmethod
    def nConstraints(self) -> int: pass

    @property
    @abstractmethod
    def nWires(self) -> int: pass

    @property
    @abstractmethod
    def constraints(self) -> List[Constraint]: pass

    @property
    @abstractmethod
    def normalised_constraints(self) -> List[Constraint]: pass
    
    @property
    @abstractmethod
    def normi_to_coni(self) -> List[int]: pass

    @property
    @abstractmethod
    def nInputs(self) -> int: pass

    @property
    @abstractmethod
    def nOutputs(self) -> int: pass

    @abstractmethod
    def signal_is_input(self, signal: int) -> bool: pass

    @abstractmethod
    def signal_is_output(self, signal: int) -> bool: pass

    @abstractmethod
    def get_signals(self) -> Iterable[int]: pass

    @abstractmethod
    def get_input_signals(self) -> Iterable[int]: pass

    @abstractmethod
    def get_output_signals(self) -> Iterable[int]: pass

    @abstractmethod
    def parse_file(self, file: str) -> None: pass

    @abstractmethod
    def write_file(self, file: str) -> None: pass

    # now required constraints_to_fingerprint provided to be able to fingerprint on an aribtrary list of constraints not just the norms
    @abstractmethod
    def fingerprint_signal(self, signal: int, constraints_to_fingerprint: List[Constraint], normalised_constraint_fingerprints: List[int], prev_signal_to_fingerprint: Dict[int, Hashable], signal_to_normi: List[List[int]]) -> Hashable: pass

    @abstractmethod
    def take_subcircuit(self, constraint_subset: List[int], input_signals: List[int] | None = None, output_signals: List[int] | None = None, signal_map: Dict[int, int] | None = None): pass

    @staticmethod
    @abstractmethod
    def encode_single_norm_pair(
        names: List[str],
        norms: List[Constraint],
        is_ordered: bool,
        signal_pair_encoder: Assignment,
        signal_to_fingerprint: Dict[str, List[int]],
        fingerprint_to_signals: Dict[str, Dict[int, List[int]]],
        is_singular_class: bool = False
    ): pass

    @staticmethod
    @abstractmethod
    def singular_class_requires_additional_constraints() -> bool: pass

    def normalise_constraints(self) -> None:

        if len(self.normalised_constraints) != 0: 
            warnings.warn("Attempting to normalised already normalised constraints")
        else:

            def _normalised_constraint_building_step(coni: int, cons: Constraint):
                norms = cons.normalise()
                self.normalised_constraints.extend(norms)
                self.normi_to_coni.extend(coni for _ in range(len(norms)))

            deque(
                maxlen=0,
                iterable = itertools.starmap(_normalised_constraint_building_step, enumerate(self.constraints))
            )