import itertools
from typing import List, Dict, Set, Hashable
from collections import deque

from circuits_and_constraints.acir.acir_constraint import ACIRConstraint
from utilities.assignment import Assignment

def encode_single_norm_pair(
        names: List[str], 
        norms: List[ACIRConstraint], 
        signal_pair_encoder: Assignment, 
        signal_to_fingerprint: Dict[str, Dict[int, int]]
    ):
    ## Worse Encoding than in R1CS because of arbitrary two-pair... explodes for arbitrary polynomials very quickly
    # each n-ary equivalence implies up to k-1 (n-1)-ary equivalences which are unordered and so on for O(kn) layers each of which takes... etc

    ### options limited to those with same linear coeff and number + coefficient of nonlinear for this specific norm
    ###     for every potential pair (a,b) from the above values
    ###         if (a,b) match implies various other bi-implications based on the coefficients in their separate nonlinear pairs

    inverse_nonlinear_part = {name: {} for name in names}
    for name, norm in zip(names, norms):
        for (l, r), v in norm.mult.items():
            inverse_nonlinear_part[name].setdefault(l, {}).setdefault(v, []).append(r)
            inverse_nonlinear_part[name].setdefault(r, {}).setdefault(v, []).append(l)

    curr_fingerprint_to_signals = fingerprint_signals_in_current_norms(names, norms, inverse_nonlinear_part, signal_to_fingerprint)

    # if they have different keys or signals with different keys then
    if len(set(curr_fingerprint_to_signals[names[0]].keys()).symmetric_difference(curr_fingerprint_to_signals[names[1]])) > 0 or any(len(curr_fingerprint_to_signals[names[0]][key]) != len(curr_fingerprint_to_signals[names[1]][key]) for key in curr_fingerprint_to_signals[names[0]].keys()):
        return []

    return encode_from_fingerprints(names, inverse_nonlinear_part, signal_pair_encoder, curr_fingerprint_to_signals)


def fingerprint_signals_in_current_norms(
        names: List[str], 
        norms: List[ACIRConstraint], 
        inverse_nonlinear_part: Dict[str, Dict[int, Dict[int, List[int]]]], 
        signal_to_fingerprint: Dict[str, Dict[int, int]]
    ):
    signals = {name: norm.signals() for name, norm in zip(names, norms)}

    norm_pair_assignment = Assignment(assignees=1)
    curr_signal_to_fingerprint = {
        name: {sig : norm_pair_assignment.get_assignment(signal_to_fingerprint[name][sig]) for sig in signals[name]}
        for name in names
    }

    def get_hashable(name: str, norm: ACIRConstraint, sig: int) -> Hashable:
        return (norm.linear.get(sig, 0), tuple(sorted(
            (curr_signal_to_fingerprint[name][osig], val) for val, osigs in inverse_nonlinear_part[name].get(sig, {}).items() for osig in osigs
        )))

    ## TODO: could do multiple rounds but feels like overkill to refactor fingerprinting_v2 to work in this context just for that when one round

    curr_fingerprint_to_signals = {name: {} for name in names}
    signal_hashables = {name: {sig : get_hashable(name, norm, sig) for sig in signals[name]} for name, norm in zip(names, norms)}
    deque(
        maxlen=0, iterable= itertools.starmap(lambda name, sig: curr_fingerprint_to_signals[name].setdefault(norm_pair_assignment.get_assignment(signal_hashables[name][sig]), []).append(sig), 
                                                itertools.chain.from_iterable(map(lambda name : itertools.product([name], signals[name]), names)))
    )

    return curr_fingerprint_to_signals

def encode_from_fingerprints(
        names: List[str], 
        inverse_nonlinear_part: Dict[str, Dict[int, Dict[int, List[int]]]], 
        signal_pair_encoder: Assignment, 
        curr_fingerprint_to_signals: Dict[str, Dict[int, List[int]]]
    ):

    clauses = []

    for key in curr_fingerprint_to_signals[names[0]].keys():
        for i in range(2):
            name, oname = names[i], names[1-i]

            for lsig in curr_fingerprint_to_signals[name][key]:

                # at least one
                clauses.append(list(map(lambda rsig : signal_pair_encoder.get_assignment(*((lsig, rsig) if i == 0 else (rsig, lsig))), curr_fingerprint_to_signals[oname][key])))

                if lsig in inverse_nonlinear_part[name].keys():
                    for rsig in curr_fingerprint_to_signals[oname][key]:
                        # correctness clauses
                        ## for every pair of potential signals
                        ##      each sig in mult with lsig and val v is bijected to at least one such sig for rsig

                        pair_assignment = signal_pair_encoder.get_assignment(*((lsig, rsig) if i == 0 else (rsig, lsig)))
                        sigs = [lsig, rsig]

                        clauses.extend(
                            [signal_pair_encoder.get_assignment(*((lopt, ropt) if i == 0 else (ropt, lopt))) for ropt in inverse_nonlinear_part[names[1-j]][sigs[1-j]][key]] + [-pair_assignment]
                            for j in range(2) for key in inverse_nonlinear_part[names[j]][sigs[j]].keys() for lopt in inverse_nonlinear_part[names[j]][sigs[j]][key]
                        )
    
    return clauses