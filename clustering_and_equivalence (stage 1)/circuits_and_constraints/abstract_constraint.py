from abc import ABC, abstractmethod
from typing import Set, List, Hashable

class Constraint(ABC):

    @abstractmethod
    def normalise(self) -> List["Constraint"]: pass

    @abstractmethod
    def normalisation_choices(self) -> List[int]: pass

    @abstractmethod
    def signals(self) -> Set[int]: pass

    @abstractmethod
    def fingerprint(self, signal_to_fingerprint: List[int]) -> Hashable: pass

    @abstractmethod
    def is_nonlinear(self) -> bool: pass