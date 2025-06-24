from abc import ABC, abstractmethod
from typing import Set, List

class Constraint(ABC):

    @abstractmethod
    def normalise(self) -> List["Constraint"]: pass

    @abstractmethod
    def normalisation_choices(self) -> List[int]: pass

    @abstractmethod
    def signals(self) -> Set[int]: pass