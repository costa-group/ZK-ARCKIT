"""
Natural encoding but in the form of IU-II + at least 1 left
encoding.
"""

#TODO: update to be able to follow from the single-cons class preprocessor
#           classes will only have constraints that are yet to be processed into the formula
#           signal_options can process the known information and give accurate signal information.

from typing import Dict, List, Tuple, Set
from pysat.formula import CNF
from pysat.card import CardEnc, EncType
import itertools
from itertools import product
from functools import reduce

from pysat.solvers import Solver

from bij_encodings.encoder import Encoder
from bij_encodings.assignment import Assignment
from r1cs_scripts.circuit_representation import Circuit
from normalisation import r1cs_norm
from bij_encodings.single_cons_options import signal_options

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

        if ckmapp is None: ckmapp =  Assignment(offset, assignees=3)

        all_posibilities = {
            name: {}
            for name, _ in in_pair
        }

        class_counter = 1
        for class_ in classes[in_pair[0][0]].keys():

            if debug: print(f"Starting Class {class_counter} or {len(classes[in_pair[0][0]])}", end= '\r')
            class_counter += 1

            size = len(classes[in_pair[0][0]][class_])

            left_normed = [
                r1cs_norm(in_pair[0][1].constraints[i])[0] for i in classes[in_pair[0][0]][class_]
            ]

            right_normed = [
                r1cs_norm(in_pair[1][1].constraints[i]) for i in classes[in_pair[1][0]][class_]
            ]

            Options = [
                signal_options(left_normed[i], right_norm, mapp, signal_info) 
                for i, j in product(range(size), range(size)) for right_norm in right_normed[j]
            ]

            ind = -1
            for i in range(size):

                potential_pairings = []
                for j in range(size):
                    for k in range(len(right_normed[j])):
                        ind += 1

                        # is pairing non-viable
                        if not all(map(
                                lambda x : len(x) > 0,
                                itertools.chain(*[Options[ind][name].values() for name, _ in in_pair])
                            )):
                            continue

                        ijk = ckmapp.get_assignment(classes[in_pair[0][0]][class_][i], classes[in_pair[1][0]][class_][j], k)
                        clauses = map(
                            lambda x : list(x) + [-ijk],
                            itertools.chain(*[Options[ind][name].values() for name, _ in in_pair])
                        )

                        potential_pairings.append(ijk)
                        formula.extend(clauses)
                
                if not potential_pairings:
                    ## TODO: pass nonviable through encoding
                    raise AssertionError("Found constraint that cannot be mapped to") 
            
                formula.append(potential_pairings)
            
            def extend_options(opset_possibilities, options):
                # take union of all options
                for name, _ in in_pair:
                        for signal in options[name].keys():
                            opset_possibilities[name][signal] = opset_possibilities[name].setdefault(signal, set([])
                                                                                        ).union(options[name][signal])
                
                return opset_possibilities
            
            # union within classes
            class_posibilities = reduce(
                extend_options,
                Options,
                {
                    name: {}
                    for name, _ in in_pair
                }
            )

            # intersection accross classes
            for name, _ in in_pair:
                for signal in class_posibilities[name].keys():

                    wrong_rvars = all_posibilities[name].setdefault(signal, class_posibilities[name][signal]
                                                            ).symmetric_difference(class_posibilities[name][signal])
                    assumptions.update(map(lambda x : -x, wrong_rvars))
                    all_posibilities[name][signal] = all_posibilities[name][signal].intersection(class_posibilities[name][signal])

        # internal consistency
        for (name, _), (oname, _) in zip(in_pair, in_pair[::-1]):
            for lsignal in all_posibilities[name].keys():
                i = name == in_pair[0][0]

                internally_inconsistent = [
                    var for var in all_posibilities[name][lsignal]
                    if var not in all_posibilities[oname][ mapp.get_inv_assignment(var)[i] ]
                ]

                assumptions.update(map(lambda x : -x, internally_inconsistent))
                all_posibilities[name][lsignal] = all_posibilities[name][lsignal].difference(internally_inconsistent)

        for name, _ in in_pair:

            signal_counter = 1
            for signal in all_posibilities[name].keys():

                if debug: print(f"{name} {signal_counter}: {signal}, {len(all_posibilities[name][signal])}                  ", end='\r')
                signal_counter += 1


                if len(all_posibilities[name][signal]) == 0:
                    # TODO: implement passing false through encoding
                    raise AssertionError("Found variable that cannot be mapped to") 

                formula.extend(
                    CardEnc.equals(
                        all_posibilities[name][signal],
                        bound = 1,
                        encoding=EncType.pairwise
                    )
                )
        
        if debug: print("Negating non-existent variables", end = '\r')

        # TODO: smarter offset values to avoid this as it can explode
        #       causes search problems where solver is looking through variables that don't matter
        for i in range(mapp.curr, offset+1):
            assumptions.add(-i)

        res = [formula, assumptions]

        if return_signal_mapping: res.append(mapp)
        if return_constraint_mapping: res.append(ckmapp)
        return res
                    


