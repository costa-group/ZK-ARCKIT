from functools import reduce
from itertools import chain
from typing import Dict

from r1cs_scripts.constraint import Constraint
from bij_encodings.assignment import Assignment

def signal_options(C1: Constraint, C2: Constraint, mapp: Assignment, 
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

    options = {
        name: {
            # mapping later to avoid adding variables being avaible to SAT solver
            #   -- don't see how it was seeing these variables as they weren't in any constraint...
            key: set(
                map(
                    lambda pair : mapp.get_assignment(*( (key, pair) if name == "S1" else (pair, key) )),
                    reduce(
                        lambda x, y : x.intersection(y),
                        [ inv[1-i][j][dicts[i][j][key]] for j in app[i][key] ], 
                        allkeys[1-i]
                    ) 
                )
            )
            
            for key in allkeys[i]
        }
        for name, i in [('S1', 0), ('S2', 1)]
    }

    if signal_bijection is not None:
        for name in ['S1', 'S2']:
            for key in options[name].keys():
                if key in signal_bijection[name].keys():
                    
                    options[name][key] = options[name][key].intersection([signal_bijection[name][key]])

    # FINAL: for each circ -- for each signal - potential signals could map to
    #           intersection of potential mappings seen in each part         
    return options