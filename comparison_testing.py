
import numpy as np

from r1cs_scripts.circuit_representation import Circuit
import r1cs_scripts.read_r1cs
from compare_circuits import circuit_equivalence
from r1cs_scripts.modular_operations import multiplyP


circ, circ_shuffled = Circuit(), Circuit()
r1cs_scripts.read_r1cs.parse_r1cs("SudokuO1.r1cs", circ)
r1cs_scripts.read_r1cs.parse_r1cs("SudokuO1.r1cs", circ_shuffled)

## Multiply by a value

np.random.seed(42)
coefs = np.random.randint(low=1, high = 2**10-1, size=circ_shuffled.nConstraints)

for i, coef in enumerate(coefs):
    cons = circ_shuffled.constraints[i]
    for dict in [cons.A, cons.C]:
        for key in dict.keys():
            dict[key] = multiplyP(dict[key], coef, circ_shuffled.prime_number)

## Shuffle signal labels

mapping = list(range(1, circ_shuffled.nWires))
np.random.shuffle( mapping )
mapping = [0] + mapping

for cons in circ_shuffled.constraints:
    cons.A = {mapping[key]: cons.A[key] for key in cons.A.keys()}
    cons.B = {mapping[key]: cons.B[key] for key in cons.B.keys()}
    cons.C = {mapping[key]: cons.C[key] for key in cons.C.keys()}

# NOTE: seems can verify equivalence if there is no scalar overflow in multiplyP

import time
print(circ.nConstraints)
start = time.time()

for _ in range(10**0):
    bool, mapp = circuit_equivalence(circ, circ_shuffled)
    print(bool)
    print("Number of mapping disagreements: ", len( [map for map in mapp if map[1] != mapping[map[0]]]))

    # NOTE: correctly returns true fir circ, circ_shuffled but mappings don't agree
    #   TODO: check whether this is a mistake or if the returned mapping is also correct

print(time.time() - start)