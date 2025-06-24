from abc import ABC, abstractmethod
from typing import Iterable

class Circuit(ABC):

    @property
    @abstractmethod
    def nConstraints(self): pass

    @property
    @abstractmethod
    def nWires(self): pass

    @property
    @abstractmethod
    def constraints(self): pass

    @property
    @abstractmethod
    def nInputs(self): pass

    @property
    @abstractmethod
    def nOutputs(self): pass

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