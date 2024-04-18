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

    # TODO: maybe refactor so we hash_ the long strings less
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
        
        #  if not 1 canonical form then every constraint has n canonical forms..
        #   need to compare between c1_c2 where c2 is multiplied is normalised n different ways (equivalent to c1 doing the same)
        #  Notably each C1 - nC2 is still the same bijection so the number of bij variables remains the same.

        #  What differs is now the RHS of \psi_{C1, C2} -> (CNF logic) is (\bigvee_n CNF_n logic) because at least 1 of the the
        #   logics for each n must be correct

        #  Additionally, the detect for empty variables options for non-viability is now over the whole set 

        left_normed = [
            r1cs_norm(in_pair[0][1].constraints[i])[0] for i in classes[in_pair[0][0]][class_]
        ]

        right_normed = [
            r1cs_norm(in_pair[1][1].constraints[i]) for i in classes[in_pair[1][0]][class_]
        ]

        comparison = product(
            range(len(classes[in_pair[0][0]][class_])), range(len(classes[in_pair[0][0]][class_]))
        )

        Options = [
            [signal_options(left_normed[i], right_normed[j][k]) for k in range(len(right_normed[j]))]
            for i, j in comparison
        ]

        def extend(formula, info):
            # We have CNF \or CNF \or ... \or CNF
            # Is every clause OR with each other... for |CNF|^n clauses -- hopefully n is low-ish (usually at most 4)

            i, opset = info

            name1, name2 = in_pair[0][0], in_pair[1][0]

            i_, j_ = i // len(classes[name1][class_]), i % len(classes[name1][class_])
            i, j = classes[name1][class_][i_], classes[name2][class_][j_]
            ij = cmapp.get_assignment(i, j)

            clauses = CNF()

            # Need to catch when a pairing isn't viable because a signal bijection has no options
            viable_options = [
                options for options in opset
                    if all(
                        [all(
                            [len(options[name][signal]) > 0 
                                for signal in options[name].keys()]) 
                        for name, _ in in_pair]
                    )
            ]

            if len(viable_options) == 0:
                nonviable.append(ij)
                return formula

            Product = {
                name: map(
                lambda options : options[name].items(),
                viable_options
            ) for name, _ in in_pair}

            for name, _ in in_pair:
                for llist in product(*Product[name]):

                    # generate clause
                    lits = reduce(
                        lambda acc, x : acc + [
                            mapp.get_assignment(x[0], j) if name == in_pair[0][0] else mapp.get_assignment(j, x[0])
                            for j in x[1]
                        ],
                        llist,
                        []
                    )

                    clauses.append(lits)

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
    for i in mapp.assignment.keys(): # <-- all S1 signals added to formula
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
    for j in flipped.keys(): # <-- all S2 signals added to formula
        formula.extend(
            CardEnc.atmost(
                lits = flipped[j],
                bound = 1,
                encoding=EncType.pairwise
            )
        )
    
    return (formula, nonviable) if not return_signal_mapping else (formula, nonviable, mapp)