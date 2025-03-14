
from typing import Dict, List, Tuple, Set, Callable
from pysat.formula import CNF
from pysat.card import CardEnc, EncType

from bij_encodings.encoder import Encoder
from bij_encodings.assignment import Assignment
from bij_encodings.reduced_encoding.red_class_encoder import reduced_encoding_class
from r1cs_scripts.circuit_representation import Circuit

# TODO: fix unordered AB not being handled

class ReducedEncoder(Encoder):
    """
    Partial implementation of a SAT encoder. Still requires signal encoding.
    """
    
    def encode(
            self,
            in_pair: List[Tuple[str, Circuit]],
            classes: Dict[str, Dict[str, List[int]]],
            clusters: Dict[str, Dict[str, Dict[int, Set[int]]]],
            signal_encoding: Callable,
            return_signal_mapping: bool = False,
            return_constraint_mapping: bool = False, 
            return_encoded_classes: bool = False, 
            debug: bool = False,
            formula: CNF = CNF(),
            mapp: Assignment = Assignment(),
            ckmapp: Assignment = None,
            assumptions: Set[int] = set([]),
            signal_info: Dict[str, Dict[int, int]] = None
        ) -> CNF:
        """
        The encode method for the ReducedEncoder

        The basic SAT encoding method. Given the constraint classes just uses the `reduced_encoding_class` method to encode each constraint
        class. 

        Parameters
        ----------
            in_pair: List[Tuple[str, Circuit]]
                Pair of circuit/name pairs for the input circuits
            classes: Dict[str, Dict[str, List[int]]]
                The constraint classes, for each circuitt name, and class hash the list of constraint indices that belong to that hash
            cluster:
                deprecated -- TODO: remove
            signal_encoding: Callable
                the method of encoding the signal clauses into a pysat.CNF
            return_signal_mapping: Bool
                flag to return the signal_mapping Assignment object
            return_constraint_mapping: Bool
                flag to return the constraint_mapping Assignment object
            debug: Bool
                flag to print progress updates
            formula: CNF
                If applicable a preexisting formula to append onto
            mapp: Assignment
                incoming signal_mapping Assignment object
            ckmapp: Assignment
                incoming constraint_mapping Assignment object
            assumptions: Set[int]
                incoming fixed pairs
            signal_info
                incoming knowledge about signal potential pairs
        
        Returns
        ---------
        (formula, assumptions [, signal_mapping, constraint_mapping])
            Types and semantics as with parameters of the same name
        """

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
        
        signal_encoding(in_pair, mapp, formula, assumptions, signal_info)

        res = [formula, assumptions]

        if return_signal_mapping: res.append(mapp)
        if return_constraint_mapping: res.append(ckmapp)
        if return_encoded_classes: res.append("See Previous")
        return res