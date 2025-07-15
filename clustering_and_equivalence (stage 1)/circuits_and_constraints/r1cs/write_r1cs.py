"""
Functions to write a python Circuit object to a .r1cs file

@author: Alejandro
"""

from collections import deque
from typing import Dict, List

FIELD_SIZE = 32
INT_SIZE = 4
LONGLONG_SIZE = 2 * INT_SIZE
HEADER_SECTION = 1
CONSTRAINT_SECTION = 2
SIGNAL_SECTION = 3

def encode_int(x: int, size: int = INT_SIZE) -> bytes:
    return x.to_bytes(size, 'little', signed=True)

def write_r1cs(circ: "R1CSCircuit", outfile: str, sym: bool = False) -> None:

    # magic_value, version, n_section
    stream = [b"r1cs", encode_int(1), encode_int(3)]

    write_header(circ, stream)
    write_constraints(circ, stream)
    write_signals(circ, stream)

    file = open(outfile, "wb")
    deque(maxlen=0, iterable=map(file.write, stream))
    file.close()

    if sym:
        file = open(outfile[:outfile.index('.')] + ".sym", "w")
        deque(maxlen=0, iterable=map(lambda n : file.write(f"{n},{n},0,main.name{n}\n"), range(1,circ.nWires)))
        file.close()

def write_header(circ: "R1CSCircuit", stream: List[bytes]) -> None:
    section_type = encode_int(HEADER_SECTION)
    section_size = encode_int(6 * 4 + 1 * 8 + FIELD_SIZE, size=LONGLONG_SIZE)
    field_size = encode_int(FIELD_SIZE)
    prime = circ.prime_number.to_bytes(FIELD_SIZE, 'little') #unsigned

    stream.extend([section_type, section_size, field_size, prime])

    # sets nLabels = nWires as we lose this map in parsing
    for val, enctype in zip([circ.nWires, circ.nPubOut, circ.nPubIn, circ.nPrvIn, circ.nWires, circ.nConstraints], [LONGLONG_SIZE if i == 4 else INT_SIZE for i in range(6)]):
        stream.append(encode_int(val, size=enctype))

def write_constraints(circ: "R1CSCircuit", stream) -> None:
    section_type = encode_int(CONSTRAINT_SECTION)
    section_size = None

    ind = len(stream)
    stream.extend([section_type, section_size])
    for cons in circ.constraints:
        write_linear_expr(cons.A, stream)
        write_linear_expr(cons.B, stream)
        write_linear_expr(cons.C, stream)

    #section_size
    stream[ind + 1] = encode_int(sum(map(len, stream[ind+2:])), size=LONGLONG_SIZE)

def write_linear_expr(expr: Dict[int, int], stream: List[bytes]) -> None:
    stream.append(len(expr).to_bytes(INT_SIZE, 'little'))
    for key, val in expr.items():
        stream.append(encode_int(key))
        stream.append(val.to_bytes(FIELD_SIZE, 'little')) #unsigned

def write_signals(circ: "R1CSCircuit", stream: List[bytes]) -> None:
    stream.append(encode_int(SIGNAL_SECTION))
    stream.append(encode_int(circ.nWires * 8, size=LONGLONG_SIZE))
    stream.extend(map(lambda x : encode_int(x, size=LONGLONG_SIZE), range(circ.nWires)))
