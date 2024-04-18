## Seems to be the only viable encoding method.

from pysat.formula import CNF
from pysat.card import CardEnc, EncType
from typing import Tuple, Dict, List
from itertools import product
from functools import reduce

from normalisation import r1cs_norm
from r1cs_scripts.circuit_representation import Circuit
from bij_encodings.single_cons_options import signal_options
from bij_encodings.assignment import Assignment

def encode(
        classes:Dict[str, Dict[str, List[int]]],
        in_pair: List[Tuple[str, Circuit]],
        offset: int,
        return_signal_mapping: bool = False
    ) -> CNF:
    
    mapp = Assignment()
    cmapp = Assignment(offset)

    nonviable = []

    formula = CNF()

    for class_ in classes[in_pair[0][0]].keys():
        for (name, _) , (oname, _) in zip(in_pair, in_pair[::-1]):
            for i in classes[name][class_]:

                lits = [
                    cmapp.get_assignment(i, j) if name == in_pair[0][0] else cmapp.get_assignment(j, i)
                    for j in classes[oname][class_]
                ]

                formula.extend(
                    CardEnc.equals(
                        lits = lits,
                        bound = 1,
                        encoding = EncType.pairwise
                    )
                )

        if 'n' in class_:
            raise NotImplementedError
        else:
            
            comparisons = product(*[ 
                                    [r1cs_norm(circ.constraints[i])[0] for i in classes[name][class_]] 
                                    for name, circ in in_pair] 
            )

            Options = [
                signal_options(c1, c2)
                for c1, c2 in comparisons
            ]

            def extend(formula, info):
                i, options = info

                name1, name2 = in_pair[0][0], in_pair[1][0]


                i_, j_ = i // len(classes[name1][class_]), i % len(classes[name1][class_])
                i, j = classes[name1][class_][i_], classes[name2][class_][j_]
                ij = cmapp.get_assignment(i, j)

                clauses = CNF()

                for name, _ in in_pair:
                    for signal in options[name].keys():

                        if len(options[name][signal]) == 0:
                            ## means that signal has no viable mapping i.e. mapping is not viable
                            nonviable.append(ij)
                            return formula

                        lits = [
                            mapp.get_assignment(signal, pair) if (name == name1) else mapp.get_assignment(pair, signal)
                            for pair in options[name][signal]
                        ]

                        clauses.extend( CardEnc.atleast(
                            lits = lits,
                            bound = 1,
                            encoding = EncType.pairwise
                        ) )

                clauses = map(lambda x : x + [-ij], clauses.clauses)
                formula.extend(clauses)

                return formula

            formula = reduce(
                extend,
                zip(range(len(Options)), Options),
                formula
            )
    
    # At most 1 for S1
    flipped = {}
    for i in mapp.assignment.keys(): # <-- all S1 signals
        if i == 0:
            continue

        for j in mapp.assignment[i].keys():
            flipped.setdefault(j, []).append( mapp.get_assignment(i, j) )

        formula.extend(
            CardEnc.atmost(
                lits = mapp.assignment[i].values(),
                bound = 1,
                encoding = EncType.pairwise
            )
        )
    
    # at most 1 for S2
    for j in flipped.keys():
        formula.extend(
            CardEnc.atmost(
                lits = flipped[j],
                bound = 1,
                encoding=EncType.pairwise
            )
        )
    
    return (formula, nonviable) if not return_signal_mapping else (formula, nonviable, mapp)