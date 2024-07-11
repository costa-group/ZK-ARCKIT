
from typing import Dict, List, Tuple, Set, Callable
from pysat.formula import CNF
from pysat.card import CardEnc, EncType

from bij_encodings.encoder import Encoder
from bij_encodings.assignment import Assignment
from bij_encodings.red_class_encoder import reduced_encoding_class
from r1cs_scripts.circuit_representation import Circuit

class ReducedEncoder(Encoder):
    
    def encode(
            self,
            classes: Dict[str, Dict[str, List[int]]],
            in_pair: List[Tuple[str, Circuit]],
            signal_encoding: Callable,
            return_signal_mapping: bool = False,
            return_constraint_mapping = False, 
            debug: bool = False,
            formula: CNF = CNF(),
            mapp: Assignment = Assignment(),
            ckmapp: Assignment = None,
            assumptions: Set[int] = set([]),
            signal_info: Dict[str, Dict[int, int]] = None
        ) -> CNF:

        if ckmapp is None: ckmapp =  Assignment(assignees=3, link=mapp)
        if signal_info is None: signal_info = {
            name: {}
            for name, _ in in_pair
        }
            
        keyset = sorted(classes[in_pair[0][0]].keys(), key = lambda k : len(classes[in_pair[0][0]][k]))

        # Encode Class Information
        class_counter = 1
        for class_ in keyset:
            if debug: print(f"Starting Class {class_counter} of {len(classes[in_pair[0][0]])}: of size {len(classes[in_pair[0][0]][class_])}                             ", end= '\r')
            class_counter += 1
            reduced_encoding_class(
                { name: classes[name][class_] for name, _ in in_pair },
                in_pair, mapp, ckmapp, formula, assumptions, signal_info
            )

        # internal consistency
        for (name, _), (oname, _) in zip(in_pair, in_pair[::-1]):
            for lsignal in signal_info[name].keys():
                i = name == in_pair[0][0]

                internally_inconsistent = [
                    var for var in signal_info[name][lsignal]
                    if var not in signal_info[oname][ mapp.get_inv_assignment(var)[i] ]
                ]

                assumptions.update(map(lambda x : -x, internally_inconsistent))
                signal_info[name][lsignal] = signal_info[name][lsignal].difference(internally_inconsistent)
        
        signal_encoding(in_pair, mapp, formula, assumptions, signal_info)

        res = [formula, assumptions]

        if return_signal_mapping: res.append(mapp)
        if return_constraint_mapping: res.append(ckmapp)
        return res