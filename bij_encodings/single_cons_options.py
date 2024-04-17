from functools import reduce

from r1cs_scripts.constraint import Constraint

def signal_options(C1: Constraint, C2: Constraint) -> dict:
    ## Assume input constraints are in a comparable canonical form

    # iterator for dicts in a constraint
    dicts = [ 
        [d.A, d.B, d.C] for d in [C1, C2]
    ]


    allkeys = [
        set(d.A.keys()).union(d.B.keys()).union(d.C.keys()) 
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
                inv[i][j].setdefault(dict_[key], set([])).add(key)
                app[i].setdefault(key, []).append( j )

    options = {
        circ: {
            key: reduce(
                lambda x, y : x.intersection(y), 
                [ inv[1-i][j][dicts[i][j][key]] for j in app[i][key] ], 
                allkeys[1-i]
            ) if key != 0 else set([0]) ## ensures constant is always mapped to constant
            for key in allkeys[i] 
        }
        for circ, i in [('S1', 0), ('S2', 1)]
    }

    # FINAL: for each circ -- for each signal - potential signals could map to
    #           intersection of potential mappings seen in each part         
    return options