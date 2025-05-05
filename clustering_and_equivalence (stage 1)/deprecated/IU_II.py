from typing import Dict, List, Tuple
from itertools import product
from functools import reduce

from r1cs_scripts.circuit_representation import Circuit
from utilities.single_cons_options import signal_options
from utilities.assignment import Assignment
from normalisation import r1cs_norm

def intra_union_inter_intersection(
        classes: Dict[str, Dict[str, List[int]]],
        in_pair: List[Tuple[str, Circuit]],
        return_mapping: bool = False
    ):
    all_posibilities = {
        name: {}
        for name, _ in in_pair
    }
    
    mapp = Assignment()

    for class_ in classes[in_pair[0][0]].keys():

        size = len(classes[in_pair[0][0]][class_])


        left_normed = [
            r1cs_norm(in_pair[0][1].constraints[i])[0] for i in classes[in_pair[0][0]][class_]
        ]

        right_normed = [
            r1cs_norm(in_pair[1][1].constraints[i]) for i in classes[in_pair[1][0]][class_]
        ]

        Options = [
            signal_options(left_normed[i], right_norm, mapp) 
            for i, j in product(range(size), range(size)) for right_norm in right_normed[j]
        ]
    
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
                all_posibilities[name][signal] = all_posibilities[name][signal].intersection(class_posibilities[name][signal])

    # internal consistency
    for (name, _), (oname, _) in zip(in_pair, in_pair[::-1]):
        for lsignal in all_posibilities[name].keys():
            i = name == in_pair[0][0]

            internally_inconsistent = [
                var for var in all_posibilities[name][lsignal]
                if var not in all_posibilities[oname][ mapp.get_inv_assignment(var)[i] ]
            ]

            all_posibilities[name][lsignal] = all_posibilities[name][lsignal].difference(internally_inconsistent)
    
    res = [all_posibilities]
    if return_mapping: res.append(mapp)

    return res