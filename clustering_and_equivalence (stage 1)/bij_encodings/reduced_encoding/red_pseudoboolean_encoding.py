
from typing import Dict, List, Tuple, Set
from pysat.formula import CNF
from pysat.pb import PBEnc, EncType

from bij_encodings.assignment import Assignment
from bij_encodings.reduced_encoding.reduced_encoder import ReducedEncoder
from r1cs_scripts.circuit_representation import Circuit

def pseudoboolean_signal_encoder(
    in_pair: List[Tuple[str, Circuit]],
    mapp: Assignment,
    formula: CNF,
    assumptions: Set[int],
    signal_info: Dict[str, Dict[int, Set[int]]]
) -> None:
    """
    Encodes a signals bijection using pseudoboolean constraints. 
    
    The encoding method for circuit equivalence relies on a bijection between signals. This method just encodes an exactly 1 constraint
    between a signals and the set of possible mappings. Each exactly 1 is encoded using a pseudoboolean constraint, typically using
    a Binary Decision Diagram (BDD)

    Parameters
    -----------
        in_pair: List[Tuple[str, Circuit]]
            Pair of circuit/name pairs for the input circuits
        mapp: Assignment
            The current set of key assignment for the signal pairs
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

    sign = lambda x: -1 if x < 0 else 1

    for name, _ in in_pair:

        for signal in signal_info[name].keys():

            if len(signal_info[name][signal]) == 1:
                assumptions.add(next(iter(signal_info[name][signal])))
                continue

            if len(signal_info[name][signal]) == 0:
                # TODO: implement passing false through encoding
                raise AssertionError(f"Found signal {signal} for {name} that cannot be mapped to") 

            # this links to mapp to ensure that we don't double assign a value
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
    """Instance of `ReducedEncoder` that encodes signals with `pseudoboolean_signal_encoder`"""

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
        The encode method for the ReducedPseudobooleanEncoder

        A basic SAT encoding method. Given the constraint classes just uses the `reduced_encoding_class` method to encode each constraint
        class. The signals are encoded using the `pseudoboolean_signal_encoder` pure bijection method.

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
        
        return super(ReducedPseudobooleanEncoder, self).encode(
            in_pair, classes, clusters, pseudoboolean_signal_encoder,
            return_signal_mapping, return_constraint_mapping, return_encoded_classes,
            debug, formula, mapp, ckmapp, assumptions, signal_info
        )

        