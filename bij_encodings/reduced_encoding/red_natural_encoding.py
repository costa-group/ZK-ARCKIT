"""
Natural encoding but in the form of IU-II + at least 1 left
encoding.
"""

from typing import Dict, List, Tuple, Set
from pysat.formula import CNF
from pysat.card import CardEnc, EncType

from bij_encodings.encoder import Encoder
from bij_encodings.assignment import Assignment
from bij_encodings.red_class_encoder import reduced_encoding_class
from r1cs_scripts.circuit_representation import Circuit

def natural_signal_encoder(
    in_pair: List[Tuple[str, Circuit]],
    mapp: Assignment,
    formula: CNF,
    assumptions: Set[int],
    signal_info: Dict[str, Dict[int, Set[int]]]
) -> None:
    for name, _ in in_pair:

        for signal in signal_info[name].keys():

            if len(signal_info[name][signal]) == 1:
                assumptions.add(next(iter(signal_info[name][signal])))
                continue

            if len(signal_info[name][signal]) == 0:
                # TODO: implement passing false through encoding
                raise AssertionError("Found variable that cannot be mapped to") 

            formula.extend(
                CardEnc.equals(
                    signal_info[name][signal],
                    bound = 1,
                    encoding=EncType.pairwise
                )
            )
    

class ReducedNaturalEncoder(Encoder):

    def encode(
            self,
            classes: Dict[str, Dict[str, List[int]]],
            in_pair: List[Tuple[str, Circuit]],
            offset: int,
            return_signal_mapping: bool = False,
            return_constraint_mapping = False, 
            debug: bool = False,
            formula: CNF = CNF(),
            mapp: Assignment = Assignment(),
            ckmapp: Assignment = None,
            assumptions: Set[int] = set([]),
            signal_info: Dict[str, Dict[int, int]] = None
        ) -> CNF:

        return super(ReducedNaturalEncoder, self).encode(
            classes, in_pair, natural_signal_encoder,
            return_signal_mapping, return_constraint_mapping, 
            debug, formula, mapp, ckmapp, assumptions, signal_info
        )
                    


