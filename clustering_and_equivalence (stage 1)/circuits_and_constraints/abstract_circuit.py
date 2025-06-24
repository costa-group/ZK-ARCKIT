from abc import ABC, abstractmethod
from typing import Iterable, Hashable, List
import warnings
from collections import deque
import itertools

from circuits_and_constraints.abstract_constraint import Constraint

class Circuit(ABC):

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
    def fingerprint_signal(self, signal: int) -> Hashable: pass

    @abstractmethod
    def take_subcircuit(self, constraint_subset: List[int], signal_map: List[int | None]) -> "Circuit": pass

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