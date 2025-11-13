import json
import itertools
import warnings
from typing import Iterable, List, Hashable, Dict

from circuits_and_constraints.abstract_circuit import Circuit
from circuits_and_constraints.acir.acir_constraint import ACIRConstraint, parse_acir_constraint
from circuits_and_constraints.acir.acir_encode_single_norm_pair import encode_single_norm_pair

from utilities.assignment import Assignment

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

        self._prime = int(acir_json["prime"])
        self._nWires = int(acir_json["number_of_signals"])
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
    
    def write_file(self, file: str) -> None:
        raise NotImplementedError()

    def take_subcircuit(self, constraint_subset: List[int], input_signals: List[int] | None = None, output_signals: List[int] | None = None, signal_map: Dict[int, int] | None = None, return_signal_mapping: bool = False):
        
        if (input_signals is None and output_signals is not None) or (input_signals is not None and output_signals is None):
            raise AssertionError("Gave only 1 of input and output signals to take_subcircuit")
        
        if signal_map is None:
            signals_in_subcirc = set(itertools.chain(
                input_signals,
                output_signals,
                itertools.chain.from_iterable(map(lambda con : con.signals(), map(self.constraints.__getitem__, constraint_subset)))
            ))

            next_int = itertools.count().__next__
            signal_map = {k : next_int() for k in signals_in_subcirc}
        if input_signals is None:
            input_signals = self.input_signals
            output_signals = self.output_signals

        newcirc = ACIRCircuit()

        newcirc._constraints = [self.constraints[i].signal_map(signal_map) for i in constraint_subset]

        newcirc._prime = self.prime
        newcirc._nWires = sum(1 for _ in filter(lambda k: k is not None, signal_map))
        newcirc.input_signals = list(filter(lambda k: k is not None, map(lambda k : signal_map.get(k, None), input_signals)))
        newcirc.output_signals = list(filter(lambda k: k is not None, map(lambda k : signal_map.get(k, None), output_signals)))

        return ( newcirc, signal_map ) if return_signal_mapping else newcirc
    
    def fingerprint_signal(self, signal: int, constraints_to_fingerprint: List[ACIRConstraint], normalised_constraint_fingerprints: List[Hashable], prev_signal_to_fingerprint: Dict[int, Hashable], signal_to_normi: List[List[int]]) -> Hashable:
        ## for every norm that is in - convert norm to fingerprint
        ## for appearances in that norm (in mult each appearance) coeff needs to be the same

        return tuple(sorted(
                (normalised_constraint_fingerprints[normi], 
                    (
                    tuple(sorted(
                        (prev_signal_to_fingerprint.get(osignal, (-3, -3)), val) # Needs to be a tuple as fingerprint is of formate (round_got, val)

                        for osignal, val in map(lambda tup : (tup[0][0] if tup[0][0] != signal else tup[0][1], tup[1]), filter(lambda tup : any(k == signal for k in tup[0]), constraints_to_fingerprint[normi].mult.items()))
                    )), ## mult coefficients
                    constraints_to_fingerprint[normi].linear.get(signal, 0) # linear coefficient   
                    )
                )
                for normi in signal_to_normi[signal]
        ))
    
    @staticmethod
    def encode_single_norm_pair(
        names: List[str],
        norms: List[ACIRConstraint],
        is_ordered: bool,
        signal_pair_encoder: Assignment,
        signal_to_fingerprint: Dict[str, List[int]],
        fingerprint_to_signals: Dict[str, Dict[int, List[int]]],
        is_singular_class: bool = False
    ):
        return encode_single_norm_pair(names, norms, signal_pair_encoder, signal_to_fingerprint, fingerprint_to_signals, is_singular_class)
    
    @staticmethod
    def singular_class_requires_additional_constraints(): return True
    
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