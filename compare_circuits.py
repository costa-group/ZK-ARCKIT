"""
The idea is that we have two circuis S_1, S_2, which are equivalent up to renaming of variables and constant factor
    A proof of equivalence is a bijection mapping the variable names from S_1, to S_2 under the conditions of equivalent constraints
    This bijection will eventually require some SAT solve (most likely) so to reduce the search space we divide the constraints
        into classes based on how many variables there are in the class, whether it does/does not have a constant/quadratic term
        then whether the normalisation sets are the same -- problems with this up to norm..?
            -- maybe will need more work here
        then finally we build the SAT logic that will return the bijection
"""
from typing import Tuple, List

import time

import bij_encodings.prop_encoding
from r1cs_scripts.circuit_representation import Circuit
from r1cs_scripts.constraint import Constraint
from bij_encodings.encoder import Encoder
from bij_encodings.natural_encoding import NaturalEncoder

from normalisation import r1cs_norm

constSignal = 0

def get_classes(S1: Circuit,
                S2: Circuit,
                in_pair):
    
    N = S1.nConstraints
    K = S1.nWires

    groups = {
        name:{}
        for name, _ in in_pair
    }
    # separate by constant/quadtratic term

    def constant_quadratic_split(C: Constraint) -> str:
        """
        returns 4 length string
            - first bit is has quad
            - 2-4th are the const factor of A.B C has a constant factor
        """
        has_quad  =  str(int(len(C.A) * len(C.B) != 0))
        const_pos = ''.join( [ str(1 if int(constSignal in D.keys()) else 0) for D in [C.A, C.B, C.C]] ) # maybe reduce hash len?

        return has_quad + const_pos          

    def length_split(C: Constraint) -> str:
        """
        returns 3 lengths of A, B, C
        """
        return '_'.join([str(len(D)) for D in [C.A, C.B, C.C]])
    
    def norm_split(C: Constraint) -> str:
        """
        returns a sorted list of the normalised constraints in sorted order
        """
        def to_string(circ):
            AB = f"{list(circ.A.values())}*{list(circ.B.values())}" if len(circ.A) * len(circ.B) > 0 else ""
            C = f"{list(circ.C.values())}"

            return f"{AB}+{C}"
        
        def return_sorted_coefs(circ):
            return sorted( list(circ.A.values()) + list(circ.B.values()) + list(circ.C.values()))

        norms = r1cs_norm(C)
        if len(norms) > 1: norms = sorted(norms, key = return_sorted_coefs) ## need canonical order for returned normed constraints
        norms = list(map(
            to_string,
            norms
        ))

        # TODO: is there are significant performance dip for having long hashes?
        #   given that usually the list is not more than 4 this seems unlikely.. but something to think about
        return str(list(norms))
        

    # python loops are really slow... ~22s for 818 simple const 10^4 times..
    for i in range(N):
        for name, circ in in_pair:
            hashes = [
                constant_quadratic_split(circ.constraints[i]),
                length_split(circ.constraints[i]),
                norm_split(circ.constraints[i])
            ]

            hash_ = ':'.join(hashes)

            groups[name].setdefault(hash_, []).append(i)

    return groups

def circuit_equivalence(S1: Circuit, 
                        S2: Circuit,
                        encoder: Encoder = NaturalEncoder,
                        timing: bool = False,
                        debug: bool = False
                        ) -> Tuple[bool, List[Tuple[int, int]]]:
    """
    Currently assumes A*B + C = 0, where each A, B, C are equivalent up to renaming/factor
    """

    start = time.time()

    N = S1.nConstraints
    K = S1.nWires

    if K != S2.nWires:
        return (False, f"Number of signals differs: {S1.nWires, S2.nWires} ")

    if N != S2.nConstraints:
        return (False, f"Number of constraints differs: {S1.nConstraints, S2.nConstraints} ")
    
    in_pair = [('S1', S1), ('S2', S2)]

    groups = get_classes(S1, S2, in_pair)

    # Early Exiting
    hash_time = time.time()
    if timing: print(f"Hashing took: {hash_time - start}")

    for key in list(groups['S1'].keys()) + list(groups['S2'].keys()):
        try:
            if len(groups['S1'][key]) != len(groups['S2'][key]):
                return (False, f"Size of class {key} differs: {len(groups['S1'][key]), len(groups['S2'])}") 
        except KeyError as e:
            return (False, f"Circuit missing class {key} :: " + e)
    
    if timing: print([len(class_) for class_ in groups["S1"].values()])

    try:
        solver, assumptions, mapp, cmapp = encoder().get_solver(
            groups, in_pair, K**2, return_signal_mapping = True, return_constraint_mapping = True, debug = debug
        )
    except AssertionError as e:
        return False, e

    encoding_time = time.time()
    if timing: print(f"encoding took: {encoding_time - hash_time}")

    equal = solver.solve(assumptions)

    solving_time = time.time()
    if timing: print(f"solving took: {solving_time - encoding_time}")

    if not equal:
        # print(solver.get_core())
        # core = solver.get_core()
        # score = filter(lambda x : 0 < abs(x) < K**2, core)
        # ccore = filter(lambda x : K**2 < abs(x), core)
        # print('core_signals', [mapp.get_inv_assignment(abs(x)) for x in score])
        # print('core_cons', [cmapp.get_inv_assignment(abs(x)) for x in ccore])
        return False, "SAT solver determined final formula unsatisfiable"
    else:

        ## For testing
        assignment = filter(lambda x : 0 < x < K**2, solver.get_model()) ## retains only the assignment choices
        # cassignment = filter(lambda x : K**2 < x, solver.get_model()) ## retains only the assignment choices
        assignment = map(
            lambda x : mapp.get_inv_assignment(x),
            assignment
        )
        # cassignment = map(
        #     lambda x : cmapp.get_inv_assignment(x),
        #     cassignment
        # )
        # assignment = list(assignment)
        # cassignment = list(cassignment)

        return True, list(assignment)