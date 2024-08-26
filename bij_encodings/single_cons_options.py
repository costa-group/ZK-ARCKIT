from functools import reduce
from itertools import chain
from typing import Dict, List, Tuple

from r1cs_scripts.constraint import Constraint
from bij_encodings.assignment import Assignment
from utilities import getvars

def signal_options(in_pair: List[Tuple[str, Constraint]], mapp: Assignment,
                   signal_bijection: Dict[str, Dict[int, int]] = None) -> dict:
    ## TODO: this is the holdup now.
    # problems come from constraints with 257 different variables, basically all of them with 1.. this causes a lot of assignment calls


    ## Assume input constraints are in a comparable canonical form

    # iterator for dicts in a constraint
    dicts = [ 
        [d.A, d.B, d.C] for _, d in in_pair
    ]

    allkeys = [getvars(d) for _, d in in_pair]

    # inv[Ci][part][value] = set({keys in Ci with value in Ci.part})
    inv = [
        [
            {} 
            for _ in range(3)
        ] 
        for _ in range(2)
    ]

    # app[Ci][key] = [parts in Ci that key appears in]
    app = [
        {} 
        for _ in range(2)
    ]

    for i in range(2):
        for j, dict_ in enumerate(dicts[i]):
            for key in dict_.keys():
                if key == 0:
                    continue
                inv[i][j].setdefault(dict_[key], []).append(key)
                app[i].setdefault(key, []).append( j )
    
    for j in range(3):
        if len( set(inv[0][j].keys()).symmetric_difference(inv[1][j].keys()) ) != 0:
            # These are not equivalent constraints, hence the option is inviable

            return {
                name: {signal: set([]) for signal in allkeys[i]}
                for i, name in enumerate(["S1", "S2"])
            }

    options = {
        name: {}
        for name, _ in in_pair
    }

    for i, (name, _) in enumerate(in_pair):
        for key in allkeys[i]:
            oset = reduce(
                lambda x, y : x.intersection(y),
                [ inv[1-i][j][dicts[i][j][key]] for j in app[i][key] ], 
                allkeys[1-i]
            )

            oset = set(filter(
                lambda osig : signal_bijection is None or 
                    osig not in signal_bijection[in_pair[1-i][0]].keys() or 
                    key in map(lambda ass : mapp.get_inv_assignment(ass)[i], signal_bijection[in_pair[1-i][0]][osig]),
                oset
            ))

            if signal_bijection is not None and key in signal_bijection[name].keys():
                oset.intersection_update(map(lambda ass : mapp.get_inv_assignment(ass)[1-i], signal_bijection[name][key]))

            options[name][key] = set(map(
                lambda pair : mapp.get_assignment(*((key, pair) if i == 0 else (pair, key))),
                oset
            ))
   
    return options