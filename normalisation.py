"""
Methods for normalising coefficients in a constraint.

Here we define a constraint abstractly as an ordered list of coefficients, integers mod p.
    The goal is that for a norm function N, and two constraints X, Y that are the same up to
    a constant factor and reordering that N(X) = N(Y) up to reordering.

@author: Alejandro
"""
from r1cs_scripts.modular_operations import divideP
from r1cs_scripts.constraint import Constraint

import numpy as np
from typing import List, Tuple
from itertools import product

def nonZeroNorm(cons : List[int], p: int, select: bool = False) -> List[int]:
    """
    TODO: vectorise

    Chooses coefficient that minimises normalised sum.
        Deterministic and Factor-Agnostic when sum is not 0

    options:
        select: returns chosen norm coefficient instead of normalised constraint
            - NOTE: not factor agnostic
    
    Time Complexity: O(|cons|)

    Originally defined by Clara.
    """

    s = sum(cons) % p

    assert s != 0, "tried non-zero normalisation with constraint that sums to zero"

    values = [ divideP(s, cons[i], p) for i in range(len(cons)) ]
    choice = ( s * min(values) ) % p

    if select: return [choice]
    return [divideP(cons[i], choice, p) for i in range(len(cons))]

def divisionNorm(cons : List[int], p: int,
                early_exit: bool = True, select: bool = False) -> List[int]:
    """
    TODO: vectorise?

    Chooses coefficient by repeated global division and selection.
        Method chooses final coefficient set of size n
            Set is always the n-th roots of unity up to constant factor multiple
        Function is deterministic and factor agnostic up to choice of coefficient in n
    
    options:
        early_exit: enables detection of nonzero sum to use nonZeroNorm
        select: returns chosen norm coefficient set instead of normalised constraint
            - NOTE: not factor agnostic

    Time Complexity: O(|cons|^3)

    Originally defined by Alejandro
    """

    if early_exit and sum(cons) % p != 0:
        return nonZeroNorm(cons, p, select)
    
    # restrict to distinct choices for cons
    ucons = list(set(cons))

    if early_exit and sum(ucons) % p != 0:
        choice = nonZeroNorm(ucons, p, select=True)
        if select: return choice
        return [divideP(cons[i], choice, p) for i in range(len(cons))]
    
    def find_next_indexset(I: List[int]):
        # TODO: optimise this function
        #   Thoeretical improvement by more complicated python loop
        #   may be slower due to list-comprehension speed
        #   needs testing

        A = np.array( [
            (i, j, divideP(ucons[i], ucons[j], p)) for i, j in product(I, I)
        ] )
        
        K, lenA_k = np.unique( A[:, 2], return_counts = True)
        
        k_ = min(zip(lenA_k, K))[1]

        return [i for (i, _, k) in A if k == k_]
    
    I = range(len(ucons))
    I_ = find_next_indexset(I)

    while len(I) != len(I_):
        I = I_
        I_ = find_next_indexset(I)

    coef_set = [ucons[i] for i in I]

    if select: return coef_set

    choice = max(coef_set) # NOTE: choice isn't factor agnostic
    return  [divideP(cons[i], choice, p) for i in range(len(cons))]

def r1cs_norm_choices(C: Constraint) -> List[Tuple[int, int]]:
    """
    returns options for normalisation of the r1cs constraint.

    currently returns A.B option multipled together -- maybe change
    """

    choices_AB = []
    # first normalise the quadratic term if there is one

    if len(C.A) * len(C.B) > 0:
        if 0 in C.A.keys():
            choices_A = [C.A[0]]
        else:
            choices_A = divisionNorm(list(C.A.values()), C.p, early_exit=True, select=True)

        if 0 in C.B.keys():
            choices_B = [C.B[0]]
        else:
            choices_B = divisionNorm(list(C.B.values()), C.p, early_exit=True, select=True)

        choices_AB = list(product(choices_A, choices_B))

    ## What to do now if len( choices_AB ) > 1 ?

    # current idea, do norm for each?
    if 0 in C.C.keys():
        choices_C = [C.C[0]]
        choices = list(product(choices_AB if choices_AB != [] else [(0, 0)], choices_C))
    else:
        choices = []

        if choices_AB == []:
            choices += list(product([(0, 0)], divisionNorm(list(C.C.values()), C.p, early_exit = True, select = True)))
        else:
            # normalise by quadratic term if no constant factor
            choices += list(zip(choices_AB, [a * b for a, b in choices_AB]))
    
    return choices
    
def r1cs_norm(C: Constraint) -> List[Constraint]:
    """
    Returns 'normalised' constraints
    """

    choices = r1cs_norm_choices(C)

    def normalise_with_choices(a, b, c) -> Constraint:
        res = Constraint(
            A = {key: divideP(C.A[key], a, C.p) for key in C.A.keys()},
            B = {key: divideP(C.B[key], b, C.p) for key in C.B.keys()},
            C = {key: divideP(C.C[key], c, C.p) for key in C.C.keys()},
            p = C.p
        )
        ## sorting
        for dict_ in [res.A, res.B, res.C]:
            dict_ = {key: dict_[key] for key in sorted(dict_.keys(), key = lambda x : dict_[x])}
        
        return res

    return [
        normalise_with_choices(a, b, c) for (a, b), c in choices
    ]




    # then normalise the remaining terms