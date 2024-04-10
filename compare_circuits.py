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
from math import log10

from r1cs_scripts.circuit_representation import Circuit
from r1cs_scripts.constraint import Constraint
from r1cs_scripts.modular_operations import divideP

from normalisation import r1cs_norm

constSignal = 0

def circuit_equivalence(S1: Circuit, S2: Circuit) -> Tuple[bool, List[Tuple[int, int]]]:
    """
    Currently assumes A*B + C = 0, where each A, B, C are equivalent up to renaming/factor
    """

    pass

    N = S1.nConstraints
    if N != S2.nConstraints:
        return (False, [])
    
    in_pair = [('S1', S1), ('S2', S2)]

    groups = {
        "S1":{},
        "S2":{}
    }
    # separate by constant/quadtratic term

    def constant_quadratic_split(C: Constraint) -> str:
        """
        returns 4 length string
            - first bit is has quad
            - 2-4th are the const factor of A.B C has a constant factor
        """
        has_quad  =  str(int(len(C.A) * len(C.B) != 0))
        const_pos = ','.join( [ str(D[0] if int(constSignal in D.keys()) else 0) for D in [C.A, C.B, C.C]] ) # maybe reduce hash len?

        return has_quad + ',' + const_pos          

    def length_split(C: Constraint) -> str:
        """
        returns 3 lengths of A, B, C
        """
        return ','.join([str(len(D)) for D in [C.A, C.B, C.C]])
    
    def norm_split(C: Constraint) -> str:
        """
        If there is a single choice - returns the normalised constraints in sorted order
        If there is not a single choice - returns bracketed list of choices
        """

        choices = r1cs_norm(C)

        if len(choices) == 1:
            vals = ([] if choices[0][0] == 0 else [choices[0][0]]) + list(C.C.values())
            res = [divideP(i, choices[0][1], C.p) for i in vals]
            res = str(sorted(res))
        
        else:
            res = f"n_options={len(choices)}"
        return res

    # python loops are really slow... ~22s for 818 simple const 10^4 times..
    for i in range(N):
        for name, circ in in_pair:
            hashes = [
                constant_quadratic_split(circ.constraints[i]),
                length_split(circ.constraints[i]),
                norm_split(circ.constraints[i])
            ]

            hash_ = '_'.join(hashes)

            try:
                groups[name][hash_].append(i)
            except KeyError:
                groups[name][hash_] = [i]

    # SAT

# short term testing
# TODO: update
if __name__ == '__main__':
    import r1cs_scripts.read_r1cs

    circ = Circuit()
    r1cs_scripts.read_r1cs.parse_r1cs("SudokuO1.r1cs", circ)

    import time
    print(circ.nConstraints)
    start = time.time()

    for _ in range(10**0):
        circuit_equivalence(circ, circ)

    print(time.time() - start)