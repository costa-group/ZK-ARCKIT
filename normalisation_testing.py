import numpy as np
from normalisation import divisionNorm
from itertools import chain

def gcd(a, b):
    
    while b != 0:
        a, b = b, a % b
    
    return a


def fast_modular_exponentiation(a, b, p):
    if p == 1:
        return 0
    
    res = 1

    while b > 0:
        # print(len(str(b)), end='\r')
        if b % 2 == 1:
            res = (res * a) % p
        b = b >> 1
        a = a**2 % p

    return res

def get_nth_roots_mod_p(n, p, seed = None):

    if (p - 1) % n != 0:
        raise AssertionError("No primitive root, I think") 

    # get a primitive root of p

    # TODO: change so no list of size N is made
    RNG = np.random.default_rng(seed = None)
    start = RNG.integers(low=1, high=p-1, dtype=int, size = 1)[0]
    stack = chain(range(start, p), chain(1, start))

    for g in stack:
        r = fast_modular_exponentiation(g, (p-1) // n, p)

        if r != 1:
            break
    if r == 1:
        raise AssertionError("No primitive root")

    roots = sorted([fast_modular_exponentiation(r, d, p) for d in range(n)])

    return roots


if __name__ == '__main__':

    p = 727
    n = 3

    from r1cs_scripts.modular_operations import multiplyP

    def times_x(Iter, x):
        return list(map(lambda y : multiplyP(x, y, p), Iter))

    roots3 = get_nth_roots_mod_p(3, p, seed=952)
    roots11 = get_nth_roots_mod_p(11, p, seed=952)
    roots = times_x(roots3, 2) + times_x(roots11, 50)
    print(roots)
    print(divisionNorm(roots, p, select=True))


    # empirical data suggest conjecture about requiring exactly the unique set being the roots of unity being true.