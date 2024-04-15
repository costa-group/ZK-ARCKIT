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

            try:
                groups[name][hash_].append(i)
            except KeyError:
                groups[name][hash_] = [i]

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

    """
    
    formula = pysat.formula.CNF()
    
    class Assignment():
        def __init__(self):
            self.assignment = [ [None for _ in range(K)] for _ in range(K) ]
            self.inv_assignment = [None]
            self.curr = 1
        
        def get_assignment(self, i: int, j: int) -> int:
            ## assignment i, j is from S1 to S2

            if self.assignment[i][j] != None:
                return self.assignment[i][j]
            else:
                self.assignment[i][j] = self.curr
                self.inv_assignment.append((i, j))
                self.curr += 1
                return self.assignment[i][j]
        
        def get_inv_assignment(self, i: int) -> Tuple[int, int]:
            return self.inv_assignment[i]
        
    mapp = Assignment()

    total = sum([len(groups["S1"][key])**2 for key in groups["S1"].keys()])
    i = 0

    for key in groups['S1'].keys():
        if 'n' in key:

            ## Not exactly 1 canonical form..
            raise NotImplementedError
    
        else:

            comparisons = product(*[ 
                                    [r1cs_norm(circ.constraints[i])[0] for i in groups[name][key]] 
                                    for name, circ in in_pair] 
            )
            Options = [
                signal_options(c1, c2)
                for c1, c2 in comparisons
            ]

            for options in Options:
                i += 1
                # print(i, total, "       ", end = '\r')
                for name in ["S1", "S2"]:
                    swap = name == "S2"

                    for part in options[name].keys():
                        for lsignal in options[name][part].keys():

                            lits = [
                                mapp.get_assignment(lsignal, rsignal) if not swap else mapp.get_assignment(rsignal, lsignal)
                                for rsignal in options[name][part][lsignal]
                            ]
                        
                            formula.extend(
                                CardEnc.equals(lits = lits,
                                            bound= 1,
                                            encoding = EncType.pairwise )
                            )
    
    solver = Solver(name='g4', bootstrap_with=formula)

    # TODO: fix bug in formula creation

    print('began solving')
    equal = solver.solve()
    if not equal:
        print(solver.get_core())
        return equal, "SAT solver determined final formula unsatisfiable"
    else:
        assignment = solver.get_model()
        assignment = filter(lambda x : x > 0, assignment)
        assignment = map(
            lambda x : mapp.inv_assignment(x),
            assignment
        )
        return (True, list(assignment))


def signal_options(C1: Constraint, C2: Constraint) -> dict:
    ## Assume input constraints are in a comparable canonical form

    dicts = [ [('A', d.A), ('B', d.B), ('C', d.C)] for d in [C1, C2]]

    # Generated inverse array i.e. value: [keys] dict

    inv = [
        {
            part: {} 
            for part, _ in dicts[0]
        } 
        for _ in range(2)
    ]

    for i in range(2):
        for part, dict_ in dicts[i]:
            for key in dict_.keys():
                inv[1-i][part].setdefault(dict_[key], []).append(key)
    
    options = {
        circ:{
            part: {
                key: inv[0 if circ == 'S2' else 1][part][pdic[key]] for key in pdic.keys()
            } 
            for part, pdic in dicts[0]
        }
        for circ in ['S1', 'S2']
    }
    return options

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
        print( circuit_equivalence(circ, circ) )

    print(time.time() - start)