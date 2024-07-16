
from typing import Dict, List, Tuple, Set
from pysat.formula import CNF
from pysat.pb import PBEnc, EncType

from bij_encodings.assignment import Assignment
from bij_encodings.reduced_encoding.reduced_encoder import ReducedEncoder
from bij_encodings.reduced_encoding.red_natural_encoding import internal_consistency
from r1cs_scripts.circuit_representation import Circuit

def pseudoboolean_signal_encoder(
    in_pair: List[Tuple[str, Circuit]],
    mapp: Assignment,
    formula: CNF,
    assumptions: Set[int],
    signal_info: Dict[str, Dict[int, Set[int]]]
) -> None:
    
    internal_consistency(in_pair, mapp, formula, assumptions, signal_info)

    sign = lambda x: -1 if x < 0 else 1

    for name, _ in in_pair:

        for signal in signal_info[name].keys():

            if len(signal_info[name][signal]) == 1:
                assumptions.add(next(iter(signal_info[name][signal])))
                continue

            if len(signal_info[name][signal]) == 0:
                # TODO: implement passing false through encoding
                raise AssertionError(f"Found signal {signal} for {name} that cannot be mapped to") 

            sig_mapp = Assignment(assignees=1, link = mapp)

            clauses = PBEnc.equals(
                list(signal_info[name][signal]), # PBEnc can only handle list
                bound = 1,
                encoding=EncType.best
            )

            # new values for each set of supporting lits
            maxval = max(signal_info[name][signal])

            clauses = map(
                lambda clause : list(map(lambda x : x if abs(x) <= maxval else sign(x) * sig_mapp.get_assignment(abs(x)),
                                    clause)),
                clauses
            )

            formula.extend(list(clauses))

class ReducedPseudobooleanEncoder(ReducedEncoder):

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
        
        return super(ReducedPseudobooleanEncoder, self).encode(
            in_pair, classes, clusters, pseudoboolean_signal_encoder,
            return_signal_mapping, return_constraint_mapping, return_encoded_classes,
            debug, formula, mapp, ckmapp, assumptions, signal_info
        )

        