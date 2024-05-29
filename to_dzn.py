"""

"""

import sys
import itertools
import functools

from r1cs_scripts.circuit_representation import Circuit
from r1cs_scripts.constraint import Constraint
from bij_encodings.assignment import Assignment
from bij_encodings.IU_II import intra_union_inter_intersection
from compare_circuits import get_classes
from normalisation import r1cs_norm

def _classes_string(classes) -> str:

    splits = [1]
    sum = 1
    for key in classes["S1"].keys():
        sum += len(classes["S1"][key])
        splits.append(sum)
    return f"classes = {splits};\n\n"

def _signal_info_string(classes, in_pair) -> str:

    all_possibilities, mapp = intra_union_inter_intersection(classes, in_pair, True)

    res = ["signal_restrictions = [\n"]

    for i in range(1, in_pair[0][1].nWires):
        res.append(
            "{" + ",".join(map(str,
            [mapp.get_inv_assignment(x)[1] for x in all_possibilities[in_pair[0][0]][i]]
            )) + "}" +
            (i != in_pair[0][1].nWires-1) * "," + "\n"
        )
    res.append("];\n\n")

    return "".join(res)

def _constraint_info_string(circ: Constraint, circ2: Constraint, classes) -> str:
    res = []

    num_map = Assignment(assignees = 1) # fixes problems with extreme ints too large for minzinc

    c1cons = list(map(lambda x : r1cs_norm(circ.constraints[x])[0], itertools.chain.from_iterable([ classes["S1"][key] for key in classes["S1"].keys() ])))
    c2cons = list(map(lambda x : r1cs_norm(circ2.constraints[x])[0], itertools.chain.from_iterable([ classes["S2"][key] for key in classes["S1"].keys() ])))

    def getvars(con: Constraint) -> set:
        return set(con.A.keys()).union(con.B.keys()).union(con.C.keys()).difference(set([0]))
    
    maxvars = max(map(len, map(getvars, c1cons)))
    res.append(f"maxvars = {maxvars};\n\n")

    for i, cons in enumerate([c1cons, c2cons]):

        res.append(f"circuit{i+1} = array2d(1..nConstraints, 1..maxvars,\n")
        res.append("   [\n")
        for j, con in enumerate(cons):
            vars_ = getvars(con)

            res.append(",".join(
                map(str,
                    [(sig, # TODO: clean
                    num_map.get_assignment(con.A[sig]) if sig in con.A.keys() else 0,
                    num_map.get_assignment(con.B[sig]) if sig in con.B.keys() else 0,
                    num_map.get_assignment(con.C[sig]) if sig in con.C.keys() else 0)
                    for sig in vars_ if sig != 0] + 
                    [(0, 0, 0, 0)] * (maxvars - len(vars_))
                )
            ) +  (j != len(cons)-1) * "," + "\n")
        res.append("]);\n\n")
    
    return "".join(res)


def to_dzn(filename: str, circ: Circuit, circ2: Circuit):
    assert circ.nWires == circ2.nWires
    assert circ.nConstraints == circ2.nConstraints

    f = open(filename, 'w')

    f.write(f"nSignals = {circ.nWires};\n")
    f.write(f"nConstraints = {circ.nConstraints};\n\n")

    in_pair = (["S1", circ], ["S2", circ2])
    classes = get_classes(circ, circ2, in_pair)

    f.write(_classes_string(classes))
    f.write(_signal_info_string(classes, in_pair))
    f.write(_constraint_info_string(circ, circ2, classes))

    f.close()


from comparison_testing import get_circuits

if __name__ == '__main__':
    _, r1cs, outfile = sys.argv

    import time
    
    start = time.time()

    circ, circs, mapping, cmapping = get_circuits(r1cs, 1000, return_mapping=True, return_cmapping=True)

    to_dzn(outfile, circ, circs)

    print(time.time() - start)