"""

"""

import sys
import itertools
import functools
from typing import Dict

from r1cs_scripts.circuit_representation import Circuit
from r1cs_scripts.constraint import Constraint
from bij_encodings.assignment import Assignment
from bij_encodings.IU_II import intra_union_inter_intersection
from compare_circuits import get_classes, hash_constraint
from normalisation import r1cs_norm

def _classes_string(classes) -> str:

    splits = [1]
    norm_splits = [1]

    sum = 1
    norm_sum = 1
    for key in classes["S1"].keys():
        sum += len(classes["S1"][key])
        norm_sum += len(classes["S1"][key]) * (key.count("'") // 2) # ' around each potential norms

        splits.append(sum)
        norm_splits.append(norm_sum)
    return f"nNorms = {norm_sum - 1};\n\nclasses = {splits};\nnorm_classes = {norm_splits};\n\n"

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

def _constraint_info_string(circ: Circuit, circ2: Circuit, classes: Dict[str, Dict[str, int]]) -> str:
    res = []

    mapp = Assignment(assignees=1)

    def getvars(con: Constraint) -> set:
        return set(con.A.keys()).union(con.B.keys()).union(con.C.keys()).difference(set([0]))

    maxvars = max(map(lambda con : len(getvars(con)), circ.constraints))
    assert maxvars == max(map(lambda con : len(getvars(con)), circ2.constraints)), "Different maxvars hence not equivalent"

    res.append(f"maxvars = {maxvars};\n\n")

    c1cons = list(map(lambda x : r1cs_norm(circ.constraints[x])[0], itertools.chain.from_iterable([classes["S1"][key] for key in classes["S1"].keys()])))
    c2cons = map(lambda x : r1cs_norm(circ2.constraints[x]), itertools.chain.from_iterable([classes["S2"][key] for key in classes["S1"].keys()]))
    
    c2cons = list(itertools.chain.from_iterable(c2cons)) # flatten

    print(len(c1cons), len(c2cons))

    for i, cons in enumerate([c1cons, c2cons]):
        res.append(f"circuit{i+1} = array2d(1.." + ("nConstraints" if i == 0 else "nNorm") + ", 1..maxvars,\n    [\n")
        for j, con in enumerate(cons):
            vars = getvars(con)

            res.append(",".join(
                map(str,
                    [(sig, # TODO: clean
                    mapp.get_assignment(con.A[sig]) if sig in con.A.keys() else 0,
                    mapp.get_assignment(con.B[sig]) if sig in con.B.keys() else 0,
                    mapp.get_assignment(con.C[sig]) if sig in con.C.keys() else 0)
                    for sig in vars if sig != 0] + 
                    [(0, 0, 0, 0)] * (maxvars - len(vars))
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