## Seems to be the only viable encoding method.

from pysat.formula import CNF
from pysat.card import CardEnc, EncType
from typing import Tuple, Dict, List
from pysat.solvers import Solver
from itertools import product
from functools import reduce

from normalisation import r1cs_norm
from r1cs_scripts.circuit_representation import Circuit
from bij_encodings.single_cons_options import signal_options
from bij_encodings.assignment import Assignment

def get_solver(
        classes:Dict[str, Dict[str, List[int]]],
        in_pair: List[Tuple[str, Circuit]],
        offset: int,
        return_signal_mapping: bool = False,
        debug: bool = False
) -> Solver:
    
    formula, assumptions, mapp = encode(classes, in_pair, offset, return_signal_mapping, debug)

    solver = Solver(name = 'cadical195', bootstrap_with=formula)

    res = [solver, assumptions]
    if return_signal_mapping: res.append(mapp)

    return res

def encode(
        classes:Dict[str, Dict[str, List[int]]],
        in_pair: List[Tuple[str, Circuit]],
        offset: int,
        return_signal_mapping: bool = False,
        debug: bool = False
    ) -> CNF:
    
    mapp = Assignment()
    cmapp = Assignment(offset)

    nonviable = []

    formula = CNF()

    # TODO: maybe refactor so we hash_ the long strings less
    # TODO: investigate why this version is so much slower on Sudoku despite being mostly the same code
    class_counter = 1

    for class_ in classes[in_pair[0][0]].keys():

        if debug: print(f"Starting Class {class_counter} or {len(classes[in_pair[0][0]])}", end= '\r')
        class_counter += 1

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

    if debug: print("Done with Class Logic          ")

    i_counter = 0

    # At most 1 for S1
    flipped = {}
    for i in mapp.assignment.keys(): # <-- all S1 signals added to formula

        if debug: print(f"S1 {i_counter}: {i}, {len(mapp.assignment[i])}                  ", end='\r')
        i_counter += 1

        if i == 0:
            continue

        for j in mapp.assignment[i].keys():
            flipped.setdefault(j, []).append( mapp.get_assignment(i, j) )

        negatives = list(map(lambda x : -x, mapp.assignment[i].values()))

        formula.extend(
            product(negatives, negatives) # at most 1
        )

    # TODO: seems to break linux at a certain point -- memory? doesn't seem like it since taskmanager says it's not using the memory
    # Even in native windows it seems to take longer at arbitrary j -- I feel it must be a memory thing as the size of flipped is
    #    more or less equivalent but I can't think of why given we didn't have this problem for the exact same code before
    # TaskManager does show disk usage so I'm guessing that's the memory swaps happening and hence the time increase

    # at most 1 for S2
    j_counter = 0

    for j in flipped.keys(): # <-- all S2 signals added to formula
        if j == 0:
            continue

        if debug: print(f"S2 {j_counter}: {j}, {len(flipped[j])}                  ", end='\r')
        j_counter += 1

        negatives = list(map(lambda x : -x, flipped[j]))

        formula.extend(
            product(negatives, negatives) # at most 1
        )
    
    if debug: print('done encoding file')
    
    return (formula, nonviable) if not return_signal_mapping else (formula, nonviable, mapp)