import json
import itertools
import warnings
from typing import Iterable, List, Hashable, Dict

from circuits_and_constraints.abstract_circuit import Circuit
from circuits_and_constraints.acir.acir_constraint import ACIRConstraint, parse_acir_constraint

class ACIRCircuit(Circuit):

    def __init__(self):
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

        self._prime = acir_json["prime"]
        self._nWires = acir_json["number_of_signals"]
        self.input_signals = acir_json["inputs"]
        self.output_signals = acir_json["outputs"]

        self._constraints = list(map(lambda cons : parse_acir_constraint(cons, self.prime), acir_json["constraints"]))

        ## fix any preprocessing bugs
        circ_signals = set(itertools.chain(self.input_signals, self.output_signals, itertools.chain.from_iterable(map(lambda con : con.signals(), self.constraints))))
        if len(circ_signals) != self._nWires: warnings.warn(f"Number of signals in file {self.nWires} does not match given value {len(circ_signals)}, fixing...")

        next_int = itertools.count().__next__
        sigmapp = {sig : next_int() for sig in sorted(circ_signals)}

        self._constraints = list(map(lambda con : con.signal_map(sigmapp), self._constraints))
        self._nWires = len(circ_signals)
        self.input_signals = list(map(sigmapp.__getitem__, self.input_signals))
        self.output_signals = list(map(sigmapp.__getitem__, self.output_signals))

    def take_subcircuit(self, constraint_subset: List[int], signal_map: List[int]):
        
        newcirc = ACIRCircuit()

        newcirc._constraints = [self.constraints[i].signal_map(signal_map) for i in constraint_subset]

        newcirc._prime = self.prime
        newcirc._nWires = sum(1 for _ in filter(lambda k: k is not None, signal_map))
        newcirc.input_signals = [filter(lambda k: k is not None, map(signal_map.__getitem__, self.input_signals))]
        newcirc.output_signals = [filter(lambda k: k is not None, map(signal_map.__getitem__, self.output_signals))]

        return newcirc

    @staticmethod
    def encode_single_norm_pair(names, norms, is_ordered, signal_pair_encoder, signal_to_fingerprint, fingerprint_to_signals):
        raise NotImplementedError
    
    def fingerprint_signal(self, signal: int, normalised_constraint_fingerprints: List[Hashable], prev_signal_to_fingerprint: Dict[int, Hashable], signal_to_normi: List[List[int]]) -> Hashable:
        ## for every norm that is in - convert norm to fingerprint
        ## for appearances in that norm (in mult each appearance) coeff needs to be the same

        return tuple(sorted(
                (normalised_constraint_fingerprints[normi], 
                    (
                    tuple(sorted(
                        (prev_signal_to_fingerprint.get(osignal, -3), val)

                        for osignal, val in map(lambda tup : (tup[0][0] if tup[0][0] != signal else tup[0][1], tup[1]), filter(lambda tup : any(k == signal for k in tup[0]), self.normalised_constraints[normi].mult.items()))
                    )), ## mult coefficients
                    self.normalised_constraints[normi].linear.get(signal, 0) # linear coefficient   
                    )
                )
                for normi in signal_to_normi[signal]
        ))
    
    @property
    def prime(self) -> int:
        return self._prime

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