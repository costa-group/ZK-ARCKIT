
import numpy as np
from typing import List

from r1cs_scripts.circuit_representation import Circuit
import r1cs_scripts.read_r1cs
from comparison.compare_circuits import circuit_equivalence
from r1cs_scripts.modular_operations import multiplyP

def shuffle_signals(circ: Circuit, seed = None) -> List[int]:
    # modifies circ shuffling the signal labels in the circuit

    RNG = np.random.default_rng(seed)

    outputs = list(range(1, circ.nPubOut+1))
    inputs = list(range(circ.nPubOut+1, circ.nPubOut + circ.nPrvIn + circ.nPubIn + 1))
    rest = list(range(circ.nPubOut + circ.nPrvIn + circ.nPubIn + 1, circ.nWires))

    RNG.shuffle( outputs )
    RNG.shuffle( inputs )
    RNG.shuffle( rest )
    mapping = [0] + outputs + inputs + rest

    for cons in circ.constraints:
        cons.A = {mapping[key]: cons.A[key] for key in cons.A.keys()}
        cons.B = {mapping[key]: cons.B[key] for key in cons.B.keys()}
        cons.C = {mapping[key]: cons.C[key] for key in cons.C.keys()}
    
    return mapping

def shuffle_constraints(circ: Circuit, seed = None) -> None:
    
    RNG = np.random.default_rng(seed)
    mapping = list(range(0,circ.nConstraints))
    RNG.shuffle( mapping )

    temp = [None] * circ.nConstraints
    for i, j in enumerate(mapping):
        temp[j] = circ.constraints[i]
    circ.constraints = temp

    return mapping

def rand_const_factor(circ: Circuit, high = 2**10 - 1, seed = None) -> None:
    RNG = np.random.default_rng(seed)
    coefs = RNG.integers(low=1, high = high, size=circ.nConstraints)
    coefs = list(map(int, coefs))

    for i, coef in enumerate(coefs):
        cons = circ.constraints[i]
        for dict in [cons.A, cons.C]:
            for key in dict.keys():
                dict[key] = multiplyP(dict[key], coef, circ.prime_number)

def shuffle_internals(circ: Circuit, seed: int = None) -> None:
    RNG = np.random.default_rng(seed)

    for con in circ.constraints:
        conA = list(con.A.items())
        RNG.shuffle(conA)
        con.A = dict(conA)

        conB = list(con.B.items())
        RNG.shuffle(conA)
        con.B = dict(conB)

        conC = list(con.C.items())
        RNG.shuffle(conA)
        con.C = dict(conC)

def get_circuits(file, seed = None, 
            return_mapping: bool = False,
            return_cmapping: bool = False,
            const_factor : bool = True, 
            shuffle_sig : bool = True, 
            shuffle_const: bool = True,
            shuffle_internal_const: bool = True
    ):
    circ, circ_shuffled = Circuit(), Circuit()

    r1cs_scripts.read_r1cs.parse_r1cs(file, circ)
    r1cs_scripts.read_r1cs.parse_r1cs(file, circ_shuffled)

    RNG = np.random.default_rng(seed = seed)
    seed1, seed2, seed3, seed4 = RNG.integers(0, 10**6, size = 4)
    if const_factor: rand_const_factor(circ_shuffled, seed = seed1)
    if shuffle_sig: mapping = shuffle_signals(circ_shuffled, seed = seed2)
    else: mapping = list(range(circ.nWires))
    if shuffle_const: cmapping = shuffle_constraints(circ_shuffled, seed = seed3)
    else: cmapping = list(range(circ.nConstraints))
    if shuffle_internal_const: shuffle_internals(circ_shuffled, seed = seed4)

    res = [circ, circ_shuffled]
    if return_mapping: res.append(mapping)
    if return_cmapping: res.append(cmapping)

    return res

if __name__ == '__main__':
    circ, circ_shuffled, mapping = get_circuits("r1cs_files/Reveal.r1cs", 42)

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