"""
Natural encoding but in the form of IU-II + at least 1 left
encoding.
"""

from typing import Dict, List, Tuple, Set
from pysat.formula import CNF
from pysat.card import CardEnc, EncType

from deprecated.bij_encodings.encoder import Encoder
from utilities.assignment import Assignment
from deprecated.bij_encodings.reduced_encoding.red_class_encoder import reduced_encoding_class
from r1cs_scripts.circuit_representation import Circuit

def natural_signal_encoder(
    in_pair: List[Tuple[str, Circuit]],
    mapp: Assignment,
    formula: CNF,
    assumptions: Set[int],
    signal_info: Dict[str, Dict[int, Set[int]]]
) -> None:
    """
    A very basic signal bijection encoder. 
    
    The encoding method for circuit equivalence relies on a bijection between signals. This method just encodes an exactly 1 constraint
    between a signals and the set of possible mappings.

    Parameters
    -----------
        in_pair: List[Tuple[str, Circuit]]
            Pair of circuit/name pairs for the input circuits
        mapp: Assignment
            Not used. Here for consistency amongst other signal encoders.
        formula: CNF
            If applicable a preexisting formula to append onto
        assumptions: Set[int]
            incoming fixed pairs
        signal_info
            incoming knowledge about signal potential pairs
    
    Returns
    ----------
    None
        Mutates the formula and assumptions.
    """

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
    """The most basic encoder, encodes the given constraint classes in the most naive way"""

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
        """
        The encode method for the ReducedNaturalEncoder

        A basic SAT encoding method. Given the constraint classes just uses the `reduced_encoding_class` method to encode each constraint
        class. The signals are encoded using the `natural_signal_encoder` pure bijection method.

        Parameters
        ----------
            in_pair: List[Tuple[str, Circuit]]
                Pair of circuit/name pairs for the input circuits
            classes: Dict[str, Dict[str, List[int]]]
                The constraint classes, for each circuitt name, and class hash the list of constraint indices that belong to that hash
            cluster:
                deprecated -- TODO: remove
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

        return super(ReducedNaturalEncoder, self).encode(
            in_pair, classes, clusters, natural_signal_encoder,
            return_signal_mapping, return_constraint_mapping, return_encoded_classes,
            debug, formula, mapp, ckmapp, assumptions, signal_info
        )
                    


