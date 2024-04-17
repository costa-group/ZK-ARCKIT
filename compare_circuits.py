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
    class Assignment():
        def __init__(self, offset = 0):
            self.assignment = {}
            self.inv_assignment = [None]
            self.curr = 1 + offset
            self.offset = offset
        
        def get_assignment(self, i: int, j: int) -> int:
            ## assignment i, j is from S1 to S2
            try:
                return self.assignment[i][j]
            except KeyError:
                self.assignment.setdefault(i, {})
                self.assignment[i][j] = self.curr
                self.inv_assignment.append((i, j))
                self.curr += 1
                return self.assignment[i][j]
        
        def get_inv_assignment(self, i: int) -> Tuple[int, int]:
            return self.inv_assignment[i - self.offset]
        
    mapp = Assignment()

    #### TODO: Remove Verifier Stuff

    cmapp = Assignment(offset=K**2)
    ver_formula = pysat.formula.CNF()

    #### TODO: Remove Verifier Stuff

    total = sum([len(groups["S1"][key])**2 for key in groups["S1"].keys()])
    i = 0

    # TODO: ignore 0 signal
    potential = {
        name: {}
        for name in ["S1", "S2"]
    }

    for key in groups['S1'].keys():
        if 'n' in key:

            ## Not exactly 1 canonical form..
            raise NotImplementedError
    
        else:

            ## Collect 'additively' the options within a class
            class_potential = {
                name: {}
                for name in ["S1", "S2"]
            }

            comparisons = product(*[ 
                                    [r1cs_norm(circ.constraints[i])[0] for i in groups[name][key]] 
                                    for name, circ in in_pair] 
            )

            Options = [
                signal_options(c1, c2)
                for c1, c2 in comparisons
            ]

            ### TODO: Remove Verifier Stuff

            def extend(formula, info):
                i, options = info

                i_, j_ = i // len(groups["S1"][key]), i % len(groups["S1"][key])
                i, j = S1.constraints[ groups["S1"][key][i_] ], S2.constraints[ groups["S2"][key][j_] ]

                var = cmapp.get_assignment(i, j)

                clauses = pysat.formula.CNF()

                for name in ["S1", "S2"]:
                    for signal in options[name].keys():

                        if len(options[name][signal]) == 0:
                            continue

                        lits = [
                            mapp.get_assignment(signal, pair) if (name == "S1") else mapp.get_assignment(pair, signal)
                            for pair in options[name][signal]
                        ]

                        clauses.extend( CardEnc.equals(
                            lits = lits,
                            bound = 1,
                            encoding = EncType.pairwise
                        ) )

                clauses = map(lambda x : x + [-var], clauses.clauses)
                formula.extend(clauses)

                return formula

            ver_formula = reduce(
                extend,
                zip(range(len(Options)), Options),
                ver_formula
            )

            for name, circ in in_pair:
                oname = "S2" if name == "S1" else "S1"
                ocirc = S2 if name == "S1" else S1
                others = [ ocirc.constraints[j] for j in groups[oname][key] ]
                for i in groups[name][key]:
                    i_ = circ.constraints[i]


                    lits = [
                        cmapp.get_assignment(i_, j_) if name == "S1" else cmapp.get_assignment(j_, i_)
                        for j_ in others
                    ]

                    ver_formula.extend(
                        CardEnc.equals(
                            lits = lits,
                            bound = 1,
                            encoding = EncType.pairwise
                        )
                    )

            ### TODO: Remove Verifier Stuff

            def merge(class_potential, options):
                for name in ["S1", "S2"]:
                    for key in options[name].keys():
                        class_potential[name][key] = class_potential[name].setdefault(key, set([])).union(options[name][key])
                return class_potential
            
            class_potential = reduce(
                merge,
                Options,
                class_potential
            )
            
            ## Collect 'intersectionally' the options accross classes
            for name, circ in in_pair:
                for signal in class_potential[name].keys():
                    if len(class_potential[name][signal]) == 0:
                        continue
                    potential[name][signal] = potential[name].setdefault(
                                                                signal, class_potential[name][signal]
                                                         ).intersection(
                                                                class_potential[name][signal]
                                                         )
    # Internal consistency.
    for name, oname in [("S1", "S2"), ("S2", "S1")]:
        for signal in potential[name].keys():
            potential[name][signal] = [
                pair for pair in potential[name][signal]
                    if signal in potential[oname][pair]
            ]

    formula = pysat.formula.CNF()
    for name in ["S1", "S2"]:
        for key in potential[name].keys():
            
            lits = [
                mapp.get_assignment(key, pair) if (name == "S1") else mapp.get_assignment(pair, key)
                for pair in potential[name][key]
            ]

            if lits == []:
                ## Not possible for equivalent circuits -- TODO: check
                return (False, f"Signal {key} in circuit {name} has no potential mapping.")

            formula.extend(
                CardEnc.equals(
                    lits = lits,
                    bound = 1,
                    encoding = EncType.pairwise
                )
            )
    
    # solver choice aribtrary might be better options
    solver = Solver(name='g4', bootstrap_with=formula)
    equal = solver.solve()
    if not equal:
        return False, "SAT solver determined final formula unsatisfiable"
    else:
        assignment = solver.get_model()
        assignment = filter(lambda x : x > 0, assignment) ## retains only the assignment choices
        assignment = map(
            lambda x : mapp.get_inv_assignment(x),
            assignment
        )

        ## NOTE: Testing to Verify Correctness of Mapping Here
        #### TODO: Remove Verifier Stuff

        vsolver = Solver(name='g4', bootstrap_with=ver_formula)
        equal = vsolver.solve(assumptions=solver.get_model()) # very quick since it's almost just propagation

        print(f"Constraint mapping was able to find correct solution: {equal}")

        #### TODO: Remove Verifier Stuff

        # TODO: investigate whether mapping can be incorrect -- verifier was unsatisfiable

        return True, list(assignment)


def signal_options(C1: Constraint, C2: Constraint) -> dict:
    ## Assume input constraints are in a comparable canonical form

    # iterator for dicts in a constraint
    dicts = [ 
        [d.A, d.B, d.C] for d in [C1, C2]
    ]


    allkeys = [
        set(d.A.keys()).union(d.B.keys()).union(d.C.keys()) 
        for d in [C1, C2] 
    ]

    # inv[Ci][part][value] = set({keys in Ci with value in Ci.part})
    inv = [
        [
            {} 
            for _ in range(3)
        ] 
        for _ in range(2)
    ]

    # app[Ci][key] = [parts in Ci that key appears in]
    app = [
        {} 
        for _ in range(2)
    ]

    for i in range(2):
        for j, dict_ in enumerate(dicts[i]):
            for key in dict_.keys():
                inv[i][j].setdefault(dict_[key], set([])).add(key)
                app[i].setdefault(key, []).append( j )

    options = {
        circ: {
            key: reduce(
                lambda x, y : x.intersection(y), 
                [ inv[1-i][j][dicts[i][j][key]] for j in app[i][key] ], 
                allkeys[1-i]
            ) if key != 0 else set([0]) ## ensures constant is always mapped to constant
            for key in allkeys[i] 
        }
        for circ, i in [('S1', 0), ('S2', 1)]
    }

    # FINAL: for each circ -- for each signal - potential signals could map to
    #           intersection of potential mappings seen in each part         
    return options