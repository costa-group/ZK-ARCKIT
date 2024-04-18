"""
Idea here is to use the variable options to draw relations between the constraint mappings and decide
which are mutually exclusive

DEPRECATED DUE TO LARGE THEORETICAL COST
"""

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
        return_constraint_mapping: bool = False
    ) -> CNF:

    mapp = Assignment()
    formula = CNF()

    class_comparisons = []

    for class_ in classes[in_pair[0][0]].keys():
        if 'n' in class_:

            ## Not exactly 1 canonical form..

            ## How will this work specifically in this case? seems difficult..
            raise NotImplementedError
    
        else:

            norm_constraints = [ 
                [r1cs_norm(circ.constraints[i])[0] for i in classes[name][class_]] 
                for name, circ in in_pair
            ] 

            comparisons = product(classes[in_pair[0][0]][class_], 
                                  classes[in_pair[1][0]][class_])
         
            Options = [
                (mapp.get_assignment(i, j), signal_options(norm_constraints[0][i], norm_constraints[1][j]))
                for i, j in comparisons
            ]

            class_comparisons.append(Options)

            formula.extend(
                CardEnc.equals(
                    lits = [
                        options[0] for options in Options
                    ],
                    bound = 1,
                    encoding=EncType.pairwise
                )
            )
    
    # Encode mutual exclusion here (i.e. when at most 1 for each pair)

    ## is one-to-one compairosn logic enough here 
    #       -- can there be cases where a two mappings make something else impossible but not one... (I think so...)
    #           for instance if 3 mapping have
    #                x : {1, 2}, y: {1, 3}
    #                x : {1, 2}, y: {1, 4}
    #                x : {1, 5}, y: {1, 3}
    #       -- Note that any two of the above work with different x, y. But the three don't work together

    # Thus mutual exclusion is not enough.

    def is_mutually_exclusive(oleft, oright):
        # happens when a variable is set 
        raise NotImplementedError

    # A lot of comparisons with just two...
    for i in range(len(class_comparisons)):
        for pair, options in class_comparisons[i]:
            for j in range( i+1, len(class_comparisons) ):
                for other, ooptions in class_comparisons[j]:
                    if is_mutually_exclusive(options, ooptions):
                        formula.extend([-pair, -other])

