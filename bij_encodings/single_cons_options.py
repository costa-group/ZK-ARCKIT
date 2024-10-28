from functools import reduce
from itertools import chain, starmap, product
from typing import Dict, List, Tuple, Set

from r1cs_scripts.constraint import Constraint
from bij_encodings.assignment import Assignment
from utilities import getvars

def _compare_norms_with_unordered_parts(dicts: List[List[Dict[int, int]]], allkeys: List[List[int]]) -> Tuple[List[List[Dict[int, List[int]]]], List[Dict[int, List[int]]]]:

    # inv[Ci][I][value] = set({keys in Ci with value I})
    #   if I == 0, key in both A, B, if I == 1, key in A xor B, if I == 2, key in C
    inv = list(map(lambda _ : list(map(lambda _ : dict(), range(3))), range(2)))
    
    # app[Ci][key] = [I for key appearance in Ci]
    #   if I == 0, key in both A, B, if I == 1, key in A xor B, if I == 2, key in C  
    app = list(map(lambda _ : dict(), range(2)))

    for i in range(2):
        for key in allkeys[i]:

            val = sum(map(lambda j : (j+1) * (key in dicts[i][j].keys()), range(2)))
            inC = key in dicts[i][2].keys()

            # fills in app
            if val != 0: app[i].setdefault(key, []).append(0 if val == 3 else 1)
            if inC: app[i].setdefault(key, []).append(2)

            # fills in inv
            match val:
                case 0: pass
                case 3:
                    # two values, need to agree on both but not necessarily order
                    inv[i][0].setdefault(tuple(sorted(map(lambda j : dicts[i][j][key], range(2)))), []).append(key)
                case _:
                    inv[i][1].setdefault(dicts[i][val-1][key], []).append(key)

            if inC: inv[i][2].setdefault(dicts[i][2][key], []).append(key)

    return app, inv
        

def _compare_norms_with_ordered_parts(dicts: List[List[Dict[int, int]]], _) -> Tuple[List[List[Dict[int, List[int]]]], List[Dict[int, List[int]]]]:

    # inv[Ci][part][value] = set({keys in Ci with value in Ci.part})
    inv = list(map(lambda _ : list(map(lambda _ : dict(), range(3))), range(2)))
    
    # app[Ci][key] = [parts in Ci that key appears in]
    app = list(map(lambda _ : dict(), range(2)))

    for i, j in product(range(2), range(3)):
        part = dicts[i][j]
        for key in part.keys():
            if key == 0: continue
            inv[i][j].setdefault(part[key], []).append(key)
            app[i].setdefault(key, []).append(j)

    return app, inv


def signal_options(in_pair: List[Tuple[str, Constraint]], mapp: Assignment,
                   unordered_parts: bool, signal_bijection: Dict[str, Dict[int, int]] = None) -> dict:
    ## Assume input constraints are in a comparable canonical form
    #   canonical form is normalised w.t. to normalisation.py
    #   thus we cannot assume that A*B are the same, specifically if A, B have the same ordered parts they are different
 
    # iterator for dicts in a constraint
    norms = list(starmap(lambda _, norm : norm, in_pair))

    dicts = list(map(lambda norm : [norm.A, norm.B, norm.C], norms))
    allkeys = list(map(getvars, norms))

    app, inv = (_compare_norms_with_ordered_parts if not unordered_parts else _compare_norms_with_unordered_parts)(dicts, allkeys)

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

    def _get_values_for_key(i, j, key) -> int | Tuple[int, int]:
        if not unordered_parts or j == 2: return dicts[i][j][key]
        if j == 0: return tuple(sorted(map(lambda j : dicts[i][j][key], range(2))))
        return next(iter([dicts[i][j][key] for j in range(2) if key in dicts[i][j].keys()]))

    for i, (name, _) in enumerate(in_pair):
        for key in allkeys[i]:

            oset = reduce(
                lambda x, y : x.intersection(y),
                [ inv[1-i][j][_get_values_for_key(i, j, key)] for j in app[i][key] ], 
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