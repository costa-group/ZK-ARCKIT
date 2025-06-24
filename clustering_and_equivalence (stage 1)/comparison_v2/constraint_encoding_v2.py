"""
Methods for encoding classes as defined by fingerprints into a SAT/ MaxSAT formula
"""

from typing import Dict, List, Tuple, Set
from pysat.formula import CNF, WCNF
from pysat.pb import PBEnc, EncType
from functools import reduce
import itertools

from circuits_and_constraints.abstract_circuit import Circuit
from circuits_and_constraints.abstract_constraint import Constraint

from utilities.assignment import Assignment

def encode_classes_v2(
        in_pair: List[Tuple[str, Circuit]],
        fingerprint_to_normi: Dict[str, Dict[int, List[int]]],
        signal_to_fingerprint: Dict[str, List[int]],
        fingerprint_to_signals: Dict[str, Dict[int, List[int]]],
        weighted_cnf: bool = False,
    ) -> Tuple[CNF | WCNF, Set[int], Assignment, Assignment]:
    """
    Top-level encoder for constraint & signals classes intor a SAT/MaxSAT Formula.

    For each class of norms it calculates viable signal pairs and encodes the implication of pair -> signal constraints, additionally encodes at-least-one
    constraints for left circuit pairings. Encodes, for each signal class, SAT constraints enforcing a bijection between the signal subsets of each circuit 
    in the class.

    If weighted_cnf is True, the implication constraints are treated as hard, as they are rules that must be obeyed. All cardinality constraints are labeled
    soft with 1 weights, hence the MaxSAT encodings is attempting to maximise the number of constraint + signals that are deemed equivalent.

    Parameters
    -----------
        names: List[str]
            Top-level index set for following dicts.
        normalised_constraints: Dict[str, List[Constraint]]
            For each circuit, the list of constraint norms, sorted by original constraint order.
        fingerprint_to_normi: Dict[str, Dict[any, List[int]]]
            For each circuit, the partition of norms into classes, indexed by the encoded fingerprint label.
        signal_to_fingerprint: Dict[str, List[int]]
            For each circuit, signal to signal figerprint mapping. Assumed to be consistent with fingerprint_to_signals.
        fingerprint_to_signals: Dict[str, Dict[int, List[int]]]
            For each circuit, the partition of signals into classes, indexed by the encoded fingerprint label. Assumed to be consistent with fingerprint_to_signals.
        weighted_cnf: bool, optional
            Flag for whether We are encoding for a SAT or MaxSAT problem. Default False.
    
    Return
    ---------
    Tuple[CNF | WCNF, Set[int], Assignment, Assignment]
        Returns the calculated formula, the set of literal assumptions (empty is MaxSAT), and the Assignment encoder for norm and signal pairs.
    """

    names = [in_pair[0][0], in_pair[1][0]]

    # encode classes

    formula = WCNF() if weighted_cnf else CNF()
    assumptions = set([])

    norm_pair_encoder   = Assignment(assignees=2)
    signal_pair_encoder = Assignment(assignees=2, link=norm_pair_encoder)

    classes_to_encode = sorted(
        filter(lambda key : len(fingerprint_to_normi[names[0]][key]) > 1, fingerprint_to_normi[names[0]].keys()), 
        key = lambda k : len(fingerprint_to_normi[names[0]][k]
        ))
    
    ## NOTE: why is this necessary?
    #   norm pairs may be uniquely identifiable and incident to some reverted signal
    #       given the pair has been set, that signal must be constrained by the pair 
    #       but will not be by the fingerprinting w/ reverting. These clauses are
    #       then hard by necessity
    if weighted_cnf:

        in_both_keys = set(fingerprint_to_normi[names[0]].keys()).intersection(fingerprint_to_normi[names[1]].keys())

        for key in filter(lambda key : all(len(fingerprint_to_normi[name][key]) == 1 for name in names), in_both_keys):
            
            norm = in_pair[0][1].normalised_constraints[fingerprint_to_normi[names[0]][key][0]]
            is_ordered = not ( len(norm.A) > 0 and len(norm.B) > 0 and sorted(norm.A.values()) == sorted(norm.B.values()) )

            viable_pairs = in_pair[0][1].encode_single_norm_pair(
                names,
                [circ.normalised_constraints[fingerprint_to_normi[name][key][0]] for name, circ in in_pair],
                is_ordered,
                signal_pair_encoder,
                signal_to_fingerprint,
                fingerprint_to_signals
            )

            formula.extend(viable_pairs)

    # Add clauses for classes of size > 1
    for key in classes_to_encode:
        encode_single_norm_class(
            names, in_pair , {name: fingerprint_to_normi[name][key] for name in names}, norm_pair_encoder,
            signal_pair_encoder, signal_to_fingerprint, fingerprint_to_signals, formula, weighted_cnf = weighted_cnf
        )

    # Add bijection clauses for all signals
    for key in fingerprint_to_signals[names[0]].keys():

        if len(fingerprint_to_signals[names[0]][key]) == 1:
            literal = signal_pair_encoder.get_assignment(fingerprint_to_signals[names[0]][key][0], fingerprint_to_signals[names[1]][key][0])
            if weighted_cnf: formula.append([literal])
            else: assumptions.add(literal)
        else:
            encode_single_signal_class([fingerprint_to_signals[name][key] for name in names], signal_pair_encoder, formula, weighted_cnf = weighted_cnf)
    
    return formula, assumptions, norm_pair_encoder, signal_pair_encoder

def encode_single_norm_class(
        names: List[str],
        in_pair: List[Tuple[str, Circuit]],
        class_: Dict[str, List[int]],
        norm_pair_encoder: Assignment,
        signal_pair_encoder: Assignment,
        signal_to_fingerprint: Dict[str, List[int]],
        fingerprint_to_signals: Dict[str, Dict[int, List[int]]],
        formula: WCNF | CNF,
        weighted_cnf: bool = False
    ):
    """
    SAT encoder for a single norm-class

    Given two sets of constraint norms. Encodes the following constraints; for each norm in the 'left' circuit it is mapped to at least one norm in the 'right' circuit,
    for each pair of norms (l,r) if they are mapped together then each signal in 'l' is mapped to at least one viable signal in 'r' and vice versa. 'viable pairs' calculated
    by encode_single_norm_pair. If encoding into MaxSAT then implication circuits are hard constraints and other cosntraints are soft.

    Parameters
    -----------
        names: List[str]
            Top-level index set for following dicts.
        normalised_constraints: Dict[str, List[Constraint]]
            For each circuit, the list of constraint norms, sorted by original constraint order.
        class_: Dict[str, List[int]]
            For each circuit, the index set of constraints in the class
        norm_pair_encoder: Assignment
            Assigment dict wrapper for norm_pairs
        signal_pair_encoder: Assignment
            Assigment dict wrapper for signal_pairs
        signal_to_fingerprint: Dict[str, List[int]]
            For each circuit, signal to signal figerprint mapping. Assumed to be consistent with fingerprint_to_signals
        fingerprint_to_signals: Dict[str, Dict[int, List[int]]]
            For each circuit, the partition of signals into classes, indexed by the encoded fingerprint label. Assumed to be consistent with fingerprint_to_signals.
        formula: WCNF | CNF
            SAT/MaxSAT formula to be extended
        weighted_cnf: bool
            Flag for whether We are encoding for a SAT or MaxSAT problem. Default False.
    
    Return
    ---------
    None
        Function returns nothing, formula is mutated.
    """
    norm = in_pair[0][1].normalised_constraints[class_[names[0]][0]]
    is_ordered = not ( len(norm.A) > 0 and len(norm.B) > 0 and sorted(norm.A.values()) == sorted(norm.B.values()) )

    # for each norm pair we isolate the restriction clauses and add a if_pair -> clauses set to the clauses
    for normi in class_[names[0]]:

        normi_options = []

        for normj in class_[names[1]]:

            ij_clauses = in_pair[0][1].encode_single_norm_pair(names, [in_pair[0][1].normalised_constraints[normi], in_pair[0][1].normalised_constraints[normj]], 
                                        is_ordered, signal_pair_encoder, signal_to_fingerprint, fingerprint_to_signals)

            if len(ij_clauses) == 0: continue

            sat_variable = norm_pair_encoder.get_assignment(normi, normj)
            normi_options.append(sat_variable)

            formula.extend(map(lambda clause: clause + [-sat_variable] , ij_clauses))
    
        if len(normi_options) == 0 and not weighted_cnf:
            raise AssertionError(f"norm {normi} cannot be mapped to")
        
        if len(normi_options) > 0:
            formula.append(normi_options, *([1] if weighted_cnf else []))

    # for each norm, we need to pair it with one norm on the right
        # for each pair we encode the if_pair -> restriction clauses
    
def encode_single_signal_class(signals: List[List[int]], signal_pair_encoder: Assignment, formula : WCNF | CNF, weighted_cnf: bool = False):
    """
    Encodes a mutual exclusion constraint among pairs of signals into a CNF or WCNF formula.

    This encodes the bijection between the two sets of signals. The function uses pseudo-Boolean constraints (at most one) and
    encodes them into CNF or weighted CNF format.

    Parameters
    -----------
        signals: List[List[int]]
            A list containing two sublists of signal identifiers. The function
                ensures mutual exclusivity between each signal in one sublist
                and all signals in the other.
        signal_pair_encoder: Assignment
            An object responsible for assigning unique variable identifiers
            to signal pairs.
        formula: WCNF | CNF
            The formula to which the encoded clauses will be added.
        weighted_cnf: bool, optional
            Flag whether to treat the formula as a weighted CNF/WCNF. If True,
            adds a weight of 1 to the 'at least one' clause. Defaults to False.

    Returns
    -----------
    None
        Mutates the provided formula object

    Notes
    -----------
    - Uses `PBEnc.atmost` from the PySAT library to create at-most-one constraints.
    - Auxiliary variables introduced during encoding are re-mapped to avoid clashes.
    """
    # Adaptation of red_pseudoboolean_encoding to new class system
    sign = lambda x: -1 if x < 0 else 1

    for index in range(2):
        for signal in signals[index]:

            sat_variables = list(map(lambda osignal: signal_pair_encoder.get_assignment(*((signal, osignal) if not index else (osignal, signal))), signals[1-index]))

            atleast_clause = sat_variables
            atmost_clauses = PBEnc.atmost(
                lits = sat_variables,
                bound = 1,
                encoding = EncType.best
            ).clauses

            maxval = max(sat_variables)

            # PBEnc adds new variables which might already be used, they will always be bigger than the largest introduced variable
            aux_variable_reencoding = Assignment(assignees=1, link = signal_pair_encoder)
            
            formula.append(atleast_clause, *([1] if weighted_cnf else []))
            formula.extend(map(
                lambda clause : list(map(lambda x : x if abs(x) <= maxval else sign(x) * aux_variable_reencoding.get_assignment(abs(x)),
                                    clause)),
                atmost_clauses,
            )) # weights if appropriate
        
