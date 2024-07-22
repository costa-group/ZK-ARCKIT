"""
Natural encoding but in the form of IU-II + at least 1 left
encoding.
"""

from typing import Dict, List, Tuple, Set
from pysat.formula import CNF
from pysat.card import CardEnc, EncType

from bij_encodings.encoder import Encoder
from bij_encodings.assignment import Assignment
from bij_encodings.reduced_encoding.red_class_encoder import reduced_encoding_class
from r1cs_scripts.circuit_representation import Circuit

def internal_consistency(
    in_pair: List[Tuple[str, Circuit]],
    mapp: Assignment,
    formula: CNF,
    assumptions: Set[int],
    signal_info: Dict[str, Dict[int, Set[int]]]
) -> None:
    
    internally_inconsistent = set([])

    # if one of Assignment(l, r) has definite Assignment(l, r) the other must too
    for i, (name, _) in enumerate(in_pair):

        oname = in_pair[1-i][0]

        for lsignal in signal_info[name].keys():
            if len(signal_info[name][lsignal]) == 1:

                assignment = next(iter(signal_info[name][lsignal]))

                rsignal = mapp.get_inv_assignment(assignment)[1-i]

                internally_inconsistent.update(filter(lambda x : x != assignment, signal_info[oname][rsignal]))
                signal_info[oname][rsignal].intersection_update(signal_info[name][lsignal])

                if len(signal_info[oname][rsignal]) == 0:
                    raise AssertionError(f"Signal {rsignal} in circuit {name} has no valid assignment")

    # if only one of Assignment(l, r) has Assignment(l, r) then it's false
    for i, (name, _) in enumerate(in_pair):

        oname = in_pair[1-i][0]
        
        for lsignal in signal_info[name].keys():

            internal_inconsistensies = [
                var for var in signal_info[name][lsignal]
                if var not in signal_info[oname][ mapp.get_inv_assignment(var)[1-i] ]
            ]

            internally_inconsistent.update(internal_inconsistensies)
            signal_info[name][lsignal].difference_update(internal_inconsistensies)

            if len(signal_info[name][lsignal]) == 0:
                    raise AssertionError(f"Signal {lsignal} in circuit {name} has no valid assignment")

    assumptions.update(map(lambda x : -x, internally_inconsistent))
    
    if len(internally_inconsistent) > 0:
        internal_consistency(in_pair, mapp, formula, assumptions, signal_info)

def natural_signal_encoder(
    in_pair: List[Tuple[str, Circuit]],
    mapp: Assignment,
    formula: CNF,
    assumptions: Set[int],
    signal_info: Dict[str, Dict[int, Set[int]]]
) -> None:

    internal_consistency(in_pair, mapp, formula, assumptions, signal_info)

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
            in_pair: List[Tuple[str, Circuit]],
            classes: Dict[str, Dict[str, List[int]]],
            clusters: Dict[str, Dict[str, Dict[int, Set[int]]]] = None,
            return_signal_mapping: bool = False,
            return_constraint_mapping: bool = False,
            return_encoded_classes: bool = False,  
            debug: bool = False,
            formula: CNF = CNF(),
            mapp: Assignment = Assignment(),
            ckmapp: Assignment = None,
            assumptions: Set[int] = set([]),
            signal_info: Dict[str, Dict[int, Set[int]]] = None
        ) -> CNF:

        return super(ReducedNaturalEncoder, self).encode(
            in_pair, classes, clusters, natural_signal_encoder,
            return_signal_mapping, return_constraint_mapping, return_encoded_classes,
            debug, formula, mapp, ckmapp, assumptions, signal_info
        )
                    


