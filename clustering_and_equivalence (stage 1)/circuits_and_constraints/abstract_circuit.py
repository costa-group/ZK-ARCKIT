from abc import ABC, abstractmethod, a

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

    @abstractmethod
    def signal_is_input(self, signal: int) -> bool: pass

    @abstractmethod
    def signal_is_output(self, signal: int) -> bool: pass

    @property
    @abstractmethod
    def nInputs(self): pass

    @property
    @abstractmethod
    def nOutputs(self): pass

    @abstractmethod
    def parse_file(self, file: str) -> None: pass