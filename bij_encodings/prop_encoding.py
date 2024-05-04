"""
Idea is to use the simplest signal-only encoding (no constraint logic)
And use Lazy Clause Generation with propagators (pysat.engine) to build the constraint logic as nogoods

Builds the encoding f = IU-II \land CNF[ \bigwedge_{C \in S_1}( has_at_least_1_mapping(C) )]
    this is a correct encoding -- see proof in pdf

"""

from pysat.formula import CNF
from pysat.card import CardEnc, EncType
from pysat.solvers import Solver
from typing import Tuple, Dict, List
from functools import reduce

from normalisation import r1cs_norm
from r1cs_scripts.circuit_representation import Circuit
from bij_encodings.single_cons_options import signal_options
from bij_encodings.assignment import Assignment
from bij_encodings.cons_propagator.singlebij_constraint import ConsBijConstraint
from bij_encodings.cons_propagator.constraint_engine import ConstraintEngine
from bij_encodings.encoder import Encoder

class PropagatorEncoder(Encoder):

    def get_solver(
            self,
            classes:Dict[str, Dict[str, List[int]]],
            in_pair: List[Tuple[str, Circuit]],
            offset: int,
            return_signal_mapping: bool = False,
            return_constraint_mapping: bool = False,
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

            size = len(classes[in_pair[0][0]][class_])

            left_normed = [
                r1cs_norm(in_pair[0][1].constraints[i])[0] for i in classes[in_pair[0][0]][class_]
            ]

            right_normed = [
                r1cs_norm(in_pair[1][1].constraints[i]) for i in classes[in_pair[1][0]][class_]
            ]

            # no constraint logic so can flatten list
            Options = [
                [ signal_options(left_normed[i], right_norm, mapp) for j in range(size) for right_norm in right_normed[j] ]
                for i in range(size)
            ]

            bijconstraints += [ConsBijConstraint(options, mapp, in_pair) for options in Options]

            Options = reduce(lambda acc, x : acc + x, Options, []) # flatten

            def extend_options(opset_possibilities, options):
                # take union of all options
                for name, _ in in_pair:
                        for signal in options[name].keys():
                            opset_possibilities[name][signal] = opset_possibilities[name].setdefault(signal, set([])
                                                                                        ).union(options[name][signal])
                
                return opset_possibilities
            
            # union within classes
            class_posibilities = reduce(
                extend_options,
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

        solver = Solver(name='cadical195', bootstrap_with=formula)
        engine = ConstraintEngine(bootstrap_with=bijconstraints)

        # TODO: Fix error causing formula to be UNSAT
        solver.connect_propagator(engine)
        engine.setup_observe(solver)

        res = [solver, [-var for var in false_variables]]

        if return_signal_mapping: res.append(mapp)
        if return_constraint_mapping: res.append(Assignment()) ## no constraint mapping
        if return_engine: res.append(engine)
        return res

    def get_solver(
        self,
        classes: Dict[str, Dict[str, List[int]]],
        in_pair: List[Tuple[str, Circuit]],
        offset: int,
        return_signal_mapping: bool = False,
        return_constraint_mapping: bool = False,
        debug: bool = False
    ) -> Solver:
            raise NotImplementedError