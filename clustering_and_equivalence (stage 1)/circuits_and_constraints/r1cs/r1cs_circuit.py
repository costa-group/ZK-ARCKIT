import itertools
from typing import Set, List, Tuple

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
    
    def update_header(self, field_size, prime_number, nWires, nPubOut, nPubIn, nPrvIn, nLabels, nConstraints):
        self.field_size = field_size
        self.prime_number = prime_number
        self.nWires = nWires
        self.nPubOut = nPubOut
        self.nPubIn = nPubIn
        self.nPrvIn = nPrvIn
        self.nLabels = nLabels
        self.nConstraints = nConstraints

    def add_constraint(self, con: R1CSConstraint) -> None:
        self.constraints.append(con)
    
    def signal_is_input(self, signal: int) -> bool:
        return self.nPubOut < signal <= self.nPrvIn + self.nPubIn + self.nPubOut
    
    def signal_is_output(self, signal: int) -> bool:
        return 0 < signal <= self.nPubOut
    
    def parse_file(self, file: str) -> None:
        parse_r1cs(file, self)


    