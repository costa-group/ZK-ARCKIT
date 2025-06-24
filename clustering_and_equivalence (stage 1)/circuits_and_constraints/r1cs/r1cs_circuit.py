import itertools
from typing import Iterable, List

from circuits_and_constraints.abstract_circuit import Circuit
from circuits_and_constraints.r1cs.r1cs_constraint import R1CSConstraint
from circuits_and_constraints.r1cs.parse_r1cs import parse_r1cs

class R1CSCircuit(Circuit):
    def __init__(self):
        self.constraints = []
        self.normalised_constraints = []
        self.normi_to_coni = []

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

    def take_subcircuit(self, constraint_subset: List[int], signal_map: List[int | None]):
    
        new_circ = R1CSCircuit()

        for coni in constraint_subset:

            cons = self.constraints[coni]

            new_circ.constraints.append(R1CSConstraint(
                *[{signal_map[sig]:value for sig, value in dict_.items()} for dict_ in 
                [cons.A, cons.B, cons.C]], cons.p))

        in_next_circuit = lambda sig : signal_map[sig] is not None

        new_circ.update_header(
            self.field_size, self.prime_number, max(filter(lambda x : x is not None, signal_map)),
            nPubOut=len(list(filter(in_next_circuit, self.get_output_signals))),
            nPubIn=len(list(filter(in_next_circuit, self.get_input_signals))),
            nPrvIn=0, # TODO: may need to change if this becomes relevant..
            nLabels=None, # ??
            nConstraints=len(new_circ.constraints)
            )

        return new_circ







    