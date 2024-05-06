
import numpy as np
from typing import List

from r1cs_scripts.circuit_representation import Circuit
import r1cs_scripts.read_r1cs
from compare_circuits import circuit_equivalence
from r1cs_scripts.modular_operations import multiplyP

def shuffle_signals(circ: Circuit, seed = None) -> None:
    # modifies circ shuffling the signal labels in the circuit

    RNG = np.random.default_rng(seed)
    mapping = list(range(1, circ.nWires))
    RNG.shuffle( mapping )
    mapping = [0] + mapping

    for cons in circ.constraints:
        cons.A = {mapping[key]: cons.A[key] for key in cons.A.keys()}
        cons.B = {mapping[key]: cons.B[key] for key in cons.B.keys()}
        cons.C = {mapping[key]: cons.C[key] for key in cons.C.keys()}
    
    return mapping

def rand_const_factor(circ: Circuit, high = 2**10 - 1, seed = None) -> None:
    RNG = np.random.default_rng(seed)
    coefs = RNG.integers(low=1, high = high, size=circ.nConstraints)

    for i, coef in enumerate(coefs):
        cons = circ.constraints[i]
        for dict in [cons.A, cons.C]:
            for key in dict.keys():
                dict[key] = multiplyP(dict[key], coef, circ.prime_number)

def get_circuits(file, seeds = [None, None]):
    circ, circ_shuffled = Circuit(), Circuit()

    r1cs_scripts.read_r1cs.parse_r1cs(file, circ)
    r1cs_scripts.read_r1cs.parse_r1cs(file, circ_shuffled)

    seed1, seed2 = seeds
    rand_const_factor(circ_shuffled, seed1)
    mapping = shuffle_signals(circ_shuffled, seed2)

    return circ, circ_shuffled, mapping

if __name__ == '__main__':

    circ, circ_shuffled, mapping = get_circuits("SudokuO1.r1cs", [42, 35566])

    # NOTE: seems can verify equivalence if there is no scalar overflow in multiplyP

    import time
    print(circ.nConstraints, circ.nWires)
    start = time.time()

    from bij_encodings.natural_encoding import NaturalEncoder
    from bij_encodings.red_natural_encoding import ReducedNaturalEncoder
    from bij_encodings.prop_encoding import PropagatorEncoder

    # takes forever...
    for _ in range(10**0):
        bool, mapp = circuit_equivalence(circ, circ_shuffled, ReducedNaturalEncoder, timing=True)
        print(bool)
        if bool: 
            print("Number of mapping disagreements: ", len( [map for map in mapp if map[1] != mapping[map[0]]]))
            print([( map, (map[0], mapping[map[0]])) for map in mapp if map[1] != mapping[map[0]]])
        else: print(mapp)

        # NOTE: correctly returns true fir circ, circ_shuffled but mappings don't agree
        #   TODO: check whether this is a mistake or if the returned mapping is also correct
    print(time.time() - start)