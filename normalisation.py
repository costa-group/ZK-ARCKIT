"""
Methods for normalising coefficients in a constraint.

Here we define a constraint abstractly as an ordered list of coefficients, integers mod p.
    The goal is that for a norm function N, and two constraints X, Y that are the same up to
    a constant factor and reordering that N(X) = N(Y) up to reordering.

@author: Alejandro
"""
from modular_operations import divideP

import numpy as np
from typing import List

def nonZeroNorm(cons : List[int], p: int, select: bool = False) -> List[int]:
    """
    Chooses coefficient that minimises normalised sum.
        Deterministic and Factor-Agnostic when sum is not 0
    
    Time Complexity: O(|cons|)

    Originally defined by Clara.
    """

    s = sum(cons) % p

    assert(s != 0, "tried non-zero normalisation with constraint that sums to zero")

    values = [ divideP(s, cons[i], p) for i in range(len(cons)) ]
    choice = ( s * min(values) ) % p

    if select: return choice
    return [divideP(cons[i], choice, p) for i in range(len(cons))]