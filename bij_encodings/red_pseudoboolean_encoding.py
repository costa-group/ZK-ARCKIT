
from typing import Dict, List, Tuple, Set
from pysat.formula import CNF
from pysat.pb import PBEnc, EncType

from bij_encodings.encoder import Encoder
from bij_encodings.assignment import Assignment
from bij_encodings.red_class_encoder import reduced_encoding_class
from r1cs_scripts.circuit_representation import Circuit

class ReducedPseudobooleanEncoder(Encoder):

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
        
        if ckmapp is None: ckmapp =  Assignment(assignees=3, link=mapp)
        if signal_info is None: signal_info = {
            name: {}
            for name, _ in in_pair
        }

        keyset = sorted(classes[in_pair[0][0]].keys(), key = lambda k : len(classes[in_pair[0][0]][k]))

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


        sign = lambda x: -1 if x < 0 else 1

        for name, _ in in_pair:

            signal_counter = 1
            for signal in signal_info[name].keys():

                if len(signal_info[name][signal]) == 1:
                    continue

                if debug: print(f"{name} {signal_counter}: {signal}, {len(signal_info[name][signal])}                  ", end='\r')
                signal_counter += 1


                if len(signal_info[name][signal]) == 0:
                    # TODO: implement passing false through encoding
                    raise AssertionError("Found variable that cannot be mapped to") 

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

        res = [formula, assumptions]

        if return_signal_mapping: res.append(mapp)
        if return_constraint_mapping: res.append(ckmapp)
        return res