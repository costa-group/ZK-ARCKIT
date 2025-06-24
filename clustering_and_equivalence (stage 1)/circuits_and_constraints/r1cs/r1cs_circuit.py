import itertools
from typing import Iterable

from circuits_and_constraints.abstract_circuit import Circuit
from circuits_and_constraints.r1cs.r1cs_constraint import R1CSConstraint
from circuits_and_constraints.r1cs.parse_r1cs import parse_r1cs

class R1CSCircuit(Circuit):
    def __init__(self):
        self.constraints = []

        self.field_size = None
        self.prime_number = None
        self.nWires = None
        self.nPubOut = None
        self.nPubIn = None
        self.nPrvIn = None
        self.nLabels = None
        self.nConstraints = None

        self.nOutputs = None
        self.nInputs = None
    
    def update_header(self, field_size, prime_number, nWires, nPubOut, nPubIn, nPrvIn, nLabels, nConstraints):
        self.field_size = field_size
        self.prime_number = prime_number
        self.nWires = nWires
        self.nPubOut = nPubOut
        self.nPubIn = nPubIn
        self.nPrvIn = nPrvIn
        self.nLabels = nLabels
        self.nConstraints = nConstraints

        self.nOutputs = nPubOut
        self.nInputs = nPubIn + nPrvIn

    def add_constraint(self, con: R1CSConstraint) -> None:
        self.constraints.append(con)
    
    def signal_is_input(self, signal: int) -> bool:
        return self.nPubOut < signal <= self.nPrvIn + self.nPubIn + self.nPubOut
    
    def signal_is_output(self, signal: int) -> bool:
        return 0 < signal <= self.nPubOut
    
    def get_signals(self) -> Iterable[int]:
        return range(1, self.nWires)

    def get_input_signals(self) -> Iterable[int]: 
        return range(self.nPubOut+1, self.nPrvIn + self.nPubIn+self.nPubOut+1)

    def get_output_signals(self) -> Iterable[int]:
        return range(1, self.nPubOut+1)
    
    def parse_file(self, file: str) -> None:
        parse_r1cs(file, self)


    