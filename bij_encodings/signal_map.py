
from pysat.formula import CNF
from pysat.card import CardEnc, EncType
from typing import Tuple, Dict, List
from itertools import product
from functools import reduce

from normalisation import r1cs_norm
from r1cs_scripts.circuit_representation import Circuit
from bij_encodings.single_cons_options import signal_options
from bij_encodings.assignment import Assignment

def encode(
        classes:Dict[str, Dict[str, List[int]]],
        in_pair: List[Tuple[str, Circuit]],
        return_signal_mapping: bool = False
    ) -> CNF:
    mapp = Assignment()

    # TODO: ignore 0 signal
    potential = {
        name: {}
        for name, _ in in_pair
    }

    for class_ in classes[in_pair[0][0]].keys():
        if 'n' in class_:

            ## Not exactly 1 canonical form..
            raise NotImplementedError
    
        else:

            ## Collect 'additively' the options within a class
            class_potential = {
                name: {}
                for name, _ in in_pair
            }

            comparisons = product(*[ 
                                    [r1cs_norm(circ.constraints[i])[0] for i in classes[name][class_]] 
                                    for name, circ in in_pair] 
            )

            Options = [
                signal_options(c1, c2)
                for c1, c2 in comparisons
            ]

            def merge(class_potential, options):
                for name, _ in in_pair:
                    for key in options[name].keys():
                        class_potential[name][key] = class_potential[name].setdefault(key, set([])).union(options[name][key])
                return class_potential
            
            class_potential = reduce(
                merge,
                Options,
                class_potential
            )
            
            ## Collect 'intersectionally' the options accross classes
            for name, circ in in_pair:
                for signal in class_potential[name].keys():
                    if len(class_potential[name][signal]) == 0:
                        continue
                    potential[name][signal] = potential[name].setdefault(
                                                                signal, class_potential[name][signal]
                                                         ).intersection(
                                                                class_potential[name][signal]
                                                         )
    
    # Internal consistency.
    for (name, _), (oname, _) in zip(in_pair, in_pair[::-1]):
        for signal in potential[name].keys():
            potential[name][signal] = [
                pair for pair in potential[name][signal]
                    if signal in potential[oname][pair]
            ]

    formula = CNF()
    for name, _ in in_pair:
        for key in potential[name].keys():
            
            lits = [
                mapp.get_assignment(key, pair) if (name == in_pair[0][0]) else mapp.get_assignment(pair, key)
                for pair in potential[name][key]
            ]

            if lits == []:
                ## Not possible for equivalent circuits -- TODO: check
                return (False, f"Signal {key} in circuit {name} has no potential mapping.")

            formula.extend(
                CardEnc.equals(
                    lits = lits,
                    bound = 1,
                    encoding = EncType.pairwise
                )
            )
    
    return formula if not return_signal_mapping else (formula, mapp)