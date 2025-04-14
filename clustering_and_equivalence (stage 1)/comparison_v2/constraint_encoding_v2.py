##
    ## we have constraint classes and signal classes
    ## 

        ## when we go to encode we do it by constraint class
        ## constraint classes with length > 1 are encoded
        ##  use singular_options_v2 to further restrict signal mappings for > 1
        ##  then to signal_bijection on signals classes of length > 1
from typing import Dict, List, Tuple, Set
from pysat.formula import CNF, WCNF
from pysat.pb import PBEnc, EncType
from functools import reduce
import itertools

from r1cs_scripts.constraint import Constraint

from bij_encodings.assignment import Assignment
from bij_encodings.single_cons_options import _compare_norms_with_ordered_parts, _compare_norms_with_unordered_parts

from utilities import getvars

def encode_classes_v2(
        names,
        normalised_constraints,
        fingerprint_to_normi,
        signal_to_fingerprint,
        fingerprint_to_signals,
        weighted_cnf: bool = False,
    ):

    # encode classes

    formula = WCNF() if weighted_cnf else CNF()
    assumptions = set([])

    norm_pair_encoder   = Assignment(assignees=2)
    signal_pair_encoder = Assignment(assignees=2, link=norm_pair_encoder)

    classes_to_encode = sorted(
        filter(lambda key : len(fingerprint_to_normi[names[0]][key]) > 1, fingerprint_to_normi[names[0]].keys()), 
        key = lambda k : len(fingerprint_to_normi[names[0]][k]
        ))
    
    if weighted_cnf:
        for key in filter(lambda key : len(fingerprint_to_normi[names[0]][key]) == 1, fingerprint_to_normi[names[0]].keys()):
            if len(fingerprint_to_normi[names[1]].setdefault(key, [])) == 1:
                literal = norm_pair_encoder.get_assignment(fingerprint_to_normi[names[0]][key][0], fingerprint_to_normi[names[1]][key][0])
                formula.append([literal])

    # Add clauses for classes of size > 1
    for key in classes_to_encode:
        encode_single_norm_class(
            names, normalised_constraints, {name: fingerprint_to_normi[name][key] for name in names}, norm_pair_encoder,
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
        normalised_constraints: Dict[str, List[Constraint]],
        class_: Dict[str, List[int]],
        norm_pair_encoder: Assignment,
        signal_pair_encoder: Assignment,
        signal_to_fingerprint: Dict[str, List[int]],
        fingerprint_to_signals: Dict[str, Dict[int, List[int]]],
        formula: WCNF | CNF,
        weighted_cnf: bool = False
    ):
    norm = normalised_constraints[names[0]][class_[names[0]][0]]
    is_ordered = not ( len(norm.A) > 0 and len(norm.B) > 0 and sorted(norm.A.values()) == sorted(norm.B.values()) )

    # for each norm pair we isolate the restriction clauses and add a if_pair -> clauses set to the clauses
    for normi in class_[names[0]]:

        normi_options = []

        for normj in class_[names[1]]:

            ij_clauses = encode_single_norm_pair(names, [normalised_constraints[names[0]][normi], normalised_constraints[names[1]][normj]], 
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


def encode_single_norm_pair(
        names: List[str],
        norms: List[Constraint],
        is_ordered: bool,
        signal_pair_encoder: Assignment,
        signal_to_fingerprint: Dict[str, List[int]],
        fingerprint_to_signals: Dict[str, Dict[int, List[int]]]
    ):

    ## version from single_cons_options adapted to new signal fingerprints

    ## this restriction is necessary:
    #       e.g. two signals are in 'class' 3 that gives characteristics (6,4,0) and (2,4,6) for norms with class 5
    #              when encoding class 5 we need to restrict choices for (6,4,0) <-> (6,4,0) and (6,4,0) <-> (2,4,6)

    dicts = list(map(lambda norm : [norm.A, norm.B, norm.C], norms))
    allkeys = list(map(getvars, norms))
    
    app, inv = (_compare_norms_with_ordered_parts if is_ordered else _compare_norms_with_unordered_parts)(dicts, allkeys)

    for j in range(3):
        if len( set(inv[0][j].keys()).symmetric_difference(inv[1][j].keys()) ) != 0:
            # These are not equivalent constraints, hence the option is inviable

            return []

    clauses = []

    def _get_values_for_key(i, j, key) -> int | Tuple[int, int]:
        if is_ordered or j == 2: return dicts[i][j][key]
        if j == 0: return tuple(sorted(map(lambda j : dicts[i][j][key], range(2))))
        return next(iter([dicts[i][j][key] for j in range(2) if key in dicts[i][j].keys()]))
    
    for i, name in enumerate(names):
        for key in allkeys[i]:

            # ensures consistency amongst potential pairs
            oset = reduce(
                lambda x, y : x.intersection(y),
                [ inv[1-i][j][_get_values_for_key(i, j, key)] for j in app[i][key] ], 
                allkeys[1-i]
            )

            oset.intersection_update(fingerprint_to_signals[names[1-i]].setdefault(signal_to_fingerprint[names[i]][key], []))

            if len(oset) == 0: return []

            clauses.append(list(map(
                lambda pair : signal_pair_encoder.get_assignment(*((key, pair) if i == 0 else (pair, key))),
                oset
            )))
    
    return clauses
    
def encode_single_signal_class(signals: List[List[int]], signal_pair_encoder: Assignment, formula : WCNF | CNF, weighted_cnf: bool = False):
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
        
