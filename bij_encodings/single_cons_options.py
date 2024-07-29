from functools import reduce
from itertools import chain
from typing import Dict, Set

from r1cs_scripts.constraint import Constraint
from bij_encodings.assignment import Assignment

def signal_options(C1: Constraint, C2: Constraint, mapp: Assignment, 
                   assumptions: Set[int] = None,
                   signal_bijection: Dict[str, Dict[int, int]] = None) -> dict:
    ## Assume input constraints are in a comparable canonical form

    # iterator for dicts in a constraint
    dicts = [ 
        [d.A, d.B, d.C] for d in [C1, C2]
    ]


    allkeys = [
        set(filter( lambda key : key != 0, chain(d.A.keys(), d.B.keys(), d.C.keys()))) # not looking to map constants
        for d in [C1, C2] 
    ]

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
                inv[i][j].setdefault(dict_[key], set([])).add(key)
                app[i].setdefault(key, []).append( j )
    
    for j in range(3):
        if len( set(inv[0][j].keys()).symmetric_difference(inv[1][j].keys()) ) != 0:
            # These are not equivalent constraints, hence the option is inviable

            return {
                name: {signal: set([]) for signal in allkeys[i]}
                for i, name in enumerate(["S1", "S2"])
            }

    # TODO: update so it's not in two steps
    def get_options_set(name, i, key, update):
        return set(map(
                    lambda pair : mapp.get_assignment(*( (key, pair) if name == "S1" else (pair, key) ), update = update),
                    reduce(
                        lambda x, y : x.intersection(y),
                        [ inv[1-i][j][dicts[i][j][key]] for j in app[i][key] ], 
                        allkeys[1-i]
                    ) 
                ))

    options = {
        name: {
            key: 
                get_options_set(name, i, key, update = True)
                if signal_bijection is None or key not in signal_bijection[name].keys() else
                signal_bijection[name][key].intersection(
                    get_options_set(name, i, key, update = False)
                )
            
            for key in allkeys[i]
        }
        for name, i in [('S1', 0), ('S2', 1)]
    }
   
    return options