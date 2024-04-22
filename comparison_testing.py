
import numpy as np
from typing import List

from r1cs_scripts.circuit_representation import Circuit
import r1cs_scripts.read_r1cs
from compare_circuits import circuit_equivalence
from r1cs_scripts.modular_operations import multiplyP

def shuffle_signals(circ: Circuit, seed = None) -> None:
    # modifies circ shuffling the signal labels in the circuit

    np.random.seed(seed)
    mapping = list(range(1, circ_shuffled.nWires))
    np.random.shuffle( mapping )
    mapping = [0] + mapping

    for cons in circ.constraints:
        cons.A = {mapping[key]: cons.A[key] for key in cons.A.keys()}
        cons.B = {mapping[key]: cons.B[key] for key in cons.B.keys()}
        cons.C = {mapping[key]: cons.C[key] for key in cons.C.keys()}
    
    return mapping

def rand_const_factor(circ: Circuit, high = 2**10 - 1, seed = None) -> None:
    np.random.seed(seed)
    coefs = np.random.randint(low=1, high = high, size=circ.nConstraints)

    for i, coef in enumerate(coefs):
        cons = circ.constraints[i]
        for dict in [cons.A, cons.C]:
            for key in dict.keys():
                dict[key] = multiplyP(dict[key], coef, circ.prime_number)


if __name__ == '__main__':

    circ, circ_shuffled = Circuit(), Circuit()
    r1cs_scripts.read_r1cs.parse_r1cs("SudokuO1.r1cs", circ)
    r1cs_scripts.read_r1cs.parse_r1cs("SudokuO1.r1cs", circ_shuffled)

    ## Multiply by a value

    rand_const_factor(circ_shuffled, 42)
    mapping = shuffle_signals(circ_shuffled, 35565)

    # NOTE: seems can verify equivalence if there is no scalar overflow in multiplyP

    import time
    print(circ.nConstraints, circ.nWires)
    start = time.time()

    # ~30 seconds for this comparison.
    for _ in range(10**0):
        bool, mapp = circuit_equivalence(circ, circ_shuffled, timing=True)
        print(bool)
        print("Number of mapping disagreements: ", len( [map for map in mapp if map[1] != mapping[map[0]]]))

        # NOTE: correctly returns true fir circ, circ_shuffled but mappings don't agree
        #   TODO: check whether this is a mistake or if the returned mapping is also correct
    print(time.time() - start)