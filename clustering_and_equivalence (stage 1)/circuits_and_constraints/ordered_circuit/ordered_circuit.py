import itertools
import warnings
from functools import reduce
from typing import Iterable, List, Dict, Tuple, Hashable

from circuits_and_constraints.abstract_circuit import Circuit
from circuits_and_constraints.ordered_circuit.ordered_constraint import OrderedConstraint

from utilities.assignment import Assignment

class OrderedCircuit(Circuit):

    def __init__(self):
        self._constraints = []
        self._normalised_constraints = []
        self._normi_to_coni = []

        self._prime_number = None
        self._nWires = None
        self.input_signals = []
        self.output_signals = []
        self._nConstraints = None
        self.ordered_signals = False

    @property
    def prime(self) -> int:
        return self._prime_number

    @property
    def nConstraints(self) -> int:
        return self._nConstraints

    @property
    def nWires(self) -> int:
        return self._nWires

    @property
    def constraints(self) -> List[OrderedConstraint]:
        return self._constraints

    @property
    def normalised_constraints(self) -> List[OrderedConstraint]: 
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
        raise NotImplementedError

    def write_file(self, file: str) -> None:
        raise NotImplementedError

    # now required constraints_to_fingerprint provided to be able to fingerprint on an aribtrary list of constraints not just the norms
    def fingerprint_signal(self, signal: int, index_to_constraint: List[OrderedConstraint], normalised_constraint_fingerprints: List[int], prev_signal_to_fingerprint: Dict[int, Hashable], signal_to_normi: List[List[int]]) -> Hashable: 
        return tuple(sorted(
            (
            normalised_constraint_fingerprints[normi],
            ## Ordered/Unordered signal map for each signal in key, order of sig in key/ positions, normalised value -- term order maintained as OrderedCircuit 
            ( (tuple if self.ordered_signals else set)(map(lambda osig : prev_signal_to_fingerprint.get(osig, (-3, -3)), key)), (lambda x : x if self.ordered_signals else len)([ind for ind, osig in enumerate(key) if key == osig]), val ) 
                for key, val in zip( index_to_constraint[normi].keys, index_to_constraint[normi].values) if signal in key
            )
            for normi in signal_to_normi[signal]
            )
        )

    def take_subcircuit(self, constraint_subset: List[int], input_signals: List[int] | None = None, output_signals: List[int] | None = None, signal_map: Dict[int, int] | None = None):
        
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

        newcirc = OrderedCircuit()

        newcirc._constraints = [self.constraints[i].signal_map(signal_map) for i in constraint_subset]

        newcirc._prime_number = self.prime
        newcirc._nWires = sum(1 for _ in filter(lambda k: k is not None, signal_map))
        newcirc.input_signals = list(filter(lambda k: k is not None, map(lambda k : signal_map.get(k, None), input_signals)))
        newcirc.output_signals = list(filter(lambda k: k is not None, map(lambda k : signal_map.get(k, None), output_signals)))

        return newcirc


    @staticmethod
    def encode_single_norm_pair(
        names: List[str],
        norms: List[OrderedConstraint],
        is_ordered: bool,
        signal_pair_encoder: Assignment,
        signal_to_fingerprint: Dict[str, List[int]],
        fingerprint_to_signals: Dict[str, Dict[int, List[int]]],
        is_singular_class: bool = False
    ): pass

    @staticmethod
    def singular_class_requires_additional_constraints() -> bool:
        return True