"""
Idea is to use the simplest signal-only encoding (no constraint logic)
And use Lazy Clause Generation with propagators (pysat.engine) to build the constraint logic as nogoods
"""

from pysat.formula import CNF
from pysat.card import CardEnc, EncType
from pysat.solvers import Solver
from pysat.engines import Propagator
from typing import Tuple, Dict, List
from itertools import product, chain
from functools import reduce
from collections import defaultdict

from normalisation import r1cs_norm
from r1cs_scripts.circuit_representation import Circuit
from bij_encodings.single_cons_options import signal_options
from bij_encodings.assignment import Assignment
from bij_encodings.cons_propagator.singlebij_constraint import ConsBijConstraint
from bij_encodings.cons_propagator.constraint_engine import ConstraintEngine

def get_solver(
        classes:Dict[str, Dict[str, List[int]]],
        in_pair: List[Tuple[str, Circuit]],
        return_signal_mapping: bool = False,
        return_engine: bool = False,
        debug: bool = False
    ) -> Solver:

    mapp = Assignment()
    bijconstraints = []
    false_variables = set([])

    all_posibilities = {
        name: {}
        for name, _ in in_pair
    }

    for class_ in classes[in_pair[0][0]].keys():

        left_normed = [
            r1cs_norm(in_pair[0][1].constraints[i])[0] for i in classes[in_pair[0][0]][class_]
        ]

        right_normed = [
            r1cs_norm(in_pair[1][1].constraints[i]) for i in classes[in_pair[1][0]][class_]
        ]

        comparison = product(
            range(len(classes[in_pair[0][0]][class_])), range(len(classes[in_pair[0][0]][class_]))
        )   

        # no constraint logic so can flatten list
        Options = [
            [ signal_options(left_normed[i], right_norm, mapp) for right_norm in right_normed[j] ]
            for i, j in comparison
        ]

        bijconstraints += [ConsBijConstraint(options, mapp, in_pair) for options in Options]

        def extend_opset(opset_possibilities, opset):
            # take union of all options
            for name, _ in in_pair:
                for options in opset:
                    for signal in options[name].keys():
                        opset_possibilities[name][signal] = opset_possibilities[name].setdefault(signal, set([])
                                                                                    ).union(options[name][signal])
            
            return opset_possibilities
        # union within classes
        class_posibilities = reduce(
            extend_opset,
            Options,
            {
                name: {}
                for name, _ in in_pair
            }
        )

        # intersection accross classes
        for name, _ in in_pair:
            for signal in class_posibilities[name].keys():

                wrong_rvars = all_posibilities[name].setdefault(signal, class_posibilities[name][signal]
                                                        ).symmetric_difference(class_posibilities[name][signal])
                false_variables.update( wrong_rvars )
                all_posibilities[name][signal] = all_posibilities[name][signal].intersection(class_posibilities[name][signal])

    # internal consistency
    for (name, _), (oname, _) in zip(in_pair, in_pair[::-1]):
        for lsignal in all_posibilities[name].keys():
            i = name == in_pair[0][0]

            internally_inconsistent = [
                var for var in all_posibilities[name][lsignal]
                if var not in all_posibilities[oname][ mapp.get_inv_assignment(var)[i] ]
            ]

            false_variables.update( internally_inconsistent )
            all_posibilities[name][lsignal] = all_posibilities[name][lsignal].difference(internally_inconsistent)
    
    formula = CNF()

    for name, _ in in_pair:
        for signal in all_posibilities[name].keys():

            if len(all_posibilities[name][signal]) == 0:
                # TODO: implement passing false through encoding
                raise AssertionError("Found variable that cannot be mapped to") 

            formula.extend(
                CardEnc.equals(
                    all_posibilities[name][signal],
                    bound = 1,
                    encoding=EncType.pairwise
                )
            )  

    """
    Figured out the massive error

        the ConstraintEngine as written enforces every bijconstraint as in tries to ensure that every constraint is bijected
            with each other.

        TODO: fix this -- probably with entire new class
    
    """

    solver = Solver(name='cadical195', bootstrap_with=formula)
    engine = ConstraintEngine(bootstrap_with=bijconstraints)

    # TODO: Fix error causing formula to be UNSAT
    solver.connect_propagator(engine)
    engine.setup_observe(solver)

    res = [solver, [-var for var in false_variables]]

    if return_signal_mapping: res.append(mapp)
    if return_engine: res.append(engine)
    return res