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

import pysat
from pysat.card import EncType, CardEnc
from pysat.solvers import Solver
from itertools import product
from functools import reduce

import bij_encodings.natural_encoding
import bij_encodings.signal_encoding
from r1cs_scripts.circuit_representation import Circuit
from r1cs_scripts.constraint import Constraint
from r1cs_scripts.modular_operations import divideP

from normalisation import r1cs_norm_choices, r1cs_norm

constSignal = 0

def circuit_equivalence(S1: Circuit, S2: Circuit) -> Tuple[bool, List[Tuple[int, int]]]:
    """
    Currently assumes A*B + C = 0, where each A, B, C are equivalent up to renaming/factor
    """

    pass

    N = S1.nConstraints
    K = S1.nWires

    if K != S2.nWires:
        return (False, f"Number of signals differs: {S1.nWires, S2.nWires} ")

    if N != S2.nConstraints:
        return (False, f"Number of constraints differs: {S1.nConstraints, S2.nConstraints} ")
    
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
        const_pos = ''.join( [ str(1 if int(constSignal in D.keys()) else 0) for D in [C.A, C.B, C.C]] ) # maybe reduce hash len?

        return has_quad + ',' + const_pos          

    def length_split(C: Constraint) -> str:
        """
        returns 3 lengths of A, B, C
        """
        return ','.join([str(len(D)) for D in [C.A, C.B, C.C]])
    
    def norm_split(C: Constraint) -> str:
        """
        If there is a single choice - returns the normalised constraints in sorted order
        If there is not a single choice - returns num list of choices
        """

        norms = r1cs_norm(C)

        # would like to encode some more information but it's not possible given the factor a
        if len(norms) == 1:
            norm = norms[0]

            AB = f"{list(norm.A.values())}*{list(norm.B.values())}" if len(norm.A) * len(norm.B) > 0 else ""
            C = f"{list(norm.C.values())}"

            res = f"{AB}+{C}"
        
        else:
            # TODO: think of a better option here
            res = f"n_options={len(norms)}"
        return res

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

    # Early Exiting

    for key in list(groups['S1'].keys()) + list(groups['S2'].keys()):
        try:
            if len(groups['S1'][key]) != len(groups['S2'][key]):
                return (False, f"Size of class {key} differs: {len(groups['S1'][key]), len(groups['S2'])}") 
        except KeyError as e:
            return (False, f"Circuit missing class {key} :: " + e)
    

    # SAT
    """
    Want the SAT formula be satisfiable only if there exists a bijection between the variables in the two circuits.
    At this point the 'equivalent' circuits are in the same groups so any variables in the left, may be the same in the right 
        -- when normalised..

    ################################################################################################

    We have a bijection so for every signal in a constraint in S1
        - it is matched with exactly 1 signal in an 'equivalent' constraint in S2
        - and vice versa

    When a class has a canonical form this is easy.
    When a class has 2 canonical forms (i.e. a +/-)
        - need to convert to CNF by double propagating
    When a class has >2 canonical forms -- claim unlikely so break?

    #################################################################################################

    The above encoding (and hence) below implementation is wrong. Specifically it assumes that every constraint in a class is
        equal to each other when this is not the case. Instead there should be a bijection between the constraints, and the 
        constraint bijection implies the equals1 case.

    -------------------------------------------------------------------------------------------------

    Some options
        encode the bijection between constraints into the formula, and add a -k term to each clause where the k clause
            is the bijection from that constraint to the other. Will add ~79K variables and more clauses... (best option?)
        
        collect all options together within a class then do exactly 1 of these. << -- seems better
        
    Need to do some theoretical work to proove the correctness of an encoding I think

    --------------------------------------------------------------------------------------------------

    What do we actually need to encode into SAT. We want to be SATisfiable only if a bijection exists.

        if a bijection exists : 
            - within each class a signal is mapped to a signal in it's class <-- in both directions
            - each signal is mapped at most once across classes <-- how to encode? (again both directions)
        
        Inverse :
            - If the above two conditions are met, then each signal is mapped to exactly 1 signal in the other circuit
            - This defines a bijection -- if choices are ensured to be equivalent

    Implementation? 
        array of sets, scan over all classes
            within a class pickup options for mapping and intersect with previous (if not empty)
                ^^ maybe for classes with multiple options there are just more options here?
        
        then at the end add the equals 1 term for each of the sets.

    """

    # formula, _ = bij_encodings.signal_encoding.encode(
    #     groups, in_pair, True
    # )

    formula, mapp = bij_encodings.natural_encoding.encode(
        groups, in_pair, K**2, True
    )
    
    # solver choice aribtrary might be better options -- straight ver_formula ~120s to solve
    solver = Solver(name='g4', bootstrap_with=formula)
    equal = solver.solve()
    if not equal:
        return False, "SAT solver determined final formula unsatisfiable"
    else:
        assignment = solver.get_model()
        assignment = filter(lambda x : 0 < x < K ** 2, assignment) ## retains only the assignment choices
        assignment = map(
            lambda x : mapp.get_inv_assignment(x),
            assignment
        )
        # assignment = list(assignment)
        # f = open("assignment.txt", "w")
        # f.writelines(map(lambda x : str(x) + '\n', assignment))
        # f.close()

        # TODO: investigate whether mapping can be incorrect -- verifier was unsatisfiable

        return True, list(assignment)