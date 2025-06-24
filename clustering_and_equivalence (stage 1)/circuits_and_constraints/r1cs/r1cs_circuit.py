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

    def fingerprint_signal(self, signal: int, normalised_constraint_fingerprints: List[int], signal_to_normi: List[List[int]]):
        """
        Computes a fingerprint for a signal based on associated constraints and their fingerprints.

        Signal hashable is list of fingerprints of constraint norms that signal is in sorted by its characterstic in that norm.

        Parameters
        ----------
        signal : int
            Signal identifier.
        constraint_fingerprints : List[int]
            List of fingerprints for constraints.
        signal_to_normi : List[List[int]]
            Mapping from signals to constraints they appear in.
        norms : List[Constraint]
            List of all normalized constraints.

        Returns
        -------
        Tuple
            Hashable fingerprint for the signal.
        """
    
        fingerprint = []

        for normi in signal_to_normi[signal]:

            norm = self.norms[normi]
            is_ordered = sorted(norm.A.values()) != sorted(norm.B.values()) ## mayne have ordered lookup (more memory usage ...)

            if is_ordered:       
                Aval, Bval, Cval = [0 if signal not in part.keys() else part[signal] for part in [norm.A, norm.B, norm.C]]
                                                # weird structure here so comparable to unordered
                fingerprint.append((normalised_constraint_fingerprints[normi], ((Aval, 0), Bval, Cval)))
            else:
                inA, inB, inC = tuple(map(lambda part : signal in part.keys(), [norm.A, norm.B, norm.C]))
                cVal = 0 if not inC else norm.C[signal]

                if inA and inB:
                    fingerprint.append((normalised_constraint_fingerprints[normi], (tuple(sorted([norm.A[signal], norm.B[signal]])), 0, cVal)))
                else:
                    fingerprint.append((normalised_constraint_fingerprints[normi], ((0, 0), norm.A[signal] if inA else (norm.B[signal] if inB else 0), cVal)))

        return tuple(sorted(fingerprint))

    
    