import json
from typing import Iterable, List

from circuits_and_constraints.abstract_circuit import Circuit
from circuits_and_constraints.acir.acir_constraint import ACIRConstraint, parse_acir_constraint

class ACIRCircuit(Circuit):

    def __inti__(self):
        self._constraints = []
        self._normalised_constraints = []
        self._normi_to_coni = []

        self._nWires = None
        self.input_signals = []
        self.output_signals = []

    
    def add_constraint(self, con: ACIRConstraint) -> None:
        self.constraints.append(con)

    def signal_is_input(self, signal: int) -> bool:
        return signal in self.input_signals
    
    def signal_is_output(self, signal: int) -> bool:
        return signal in self.output_signals
    
    def get_signals(self) -> Iterable[int]:
        return range(0, self.nWires)

    def get_input_signals(self) -> Iterable[int]: 
        return self.input_signals

    def get_output_signals(self) -> Iterable[int]:
        return self.output_signals
    
    def parse_file(self, file: str) -> None:
        fp = open(file, 'r')
        acir_json = json.load(fp)
        fp.close()

        self._constraints = list(map(parse_acir_constraint, acir_json["constraints"]))

        self._nWires = acir_json["number_of_signals"]
        self.input_signals = acir_json["inputs"]
        self.output_signals = acir_json["outputs"]

    def take_subcircuit(self, constraint_subset: List[int], signal_map: List[int]):
        raise NotImplementedError

    @staticmethod
    def encode_single_norm_pair(names, norms, is_ordered, signal_pair_encoder, signal_to_fingerprint, fingerprint_to_signals):
        raise NotImplementedError
    
    def fingerprint_signal(self, signal, normalised_constraint_fingerprints, signal_to_normi):
        raise NotImplementedError
    
    @property
    def nConstraints(self) -> int:
        return len(self.constraints)

    @property
    def nWires(self) -> int:
        return self._nWires

    @property
    def constraints(self) -> List[ACIRConstraint]:
        return self._constraints
    
    @property
    def normalised_constraints(self) -> List[ACIRConstraint]:
        return self._normalised_constraints
    
    @property
    def normi_to_coni(self) -> List[int]:
        return self._normi_to_coni

    @property
    def nInputs(self) -> int:
        return len(self.input_signals)

    @property
    def nOutputs(self) -> int:
        return len(self.output_signals)