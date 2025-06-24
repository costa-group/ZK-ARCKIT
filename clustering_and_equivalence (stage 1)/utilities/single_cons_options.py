"""

Functions for comparing two normalised constraints

"""

from itertools import product
from typing import Dict, List, Tuple

def _compare_norms_with_unordered_parts(dicts: List[List[Dict[int, int]]], allkeys: List[List[int]]) -> Tuple[List[List[Dict[int, List[int]]]], List[Dict[int, List[int]]]]:
    """
    Subordinate function of `single_cons_options` for building appears and inverse lists for constraints with unordered parts.

    A normalised constraint will rarely have a part A and part B that normalise to the same values. In these cases we can no longer ensure
    that the left A and right A are the same part instead that A,B in the left (assuming equivalence) are A,B in the right. Thus the 
    appears and inverse lists are slightly different. Instead of a part index being 0, 1, 2 representing part A, B, C respectively, we
    have index 0 being 'in both A and B', 1 being 'in exactly 1 of A/B' and 2 being C.

    Parameters
    ----------
        dicts: List[List[Dict[int, int]]]
            The two constraint parts in list form dict[0] is the left constraint, dict[1] is the right constraint
        allkeys: List[List[int]]
            For each constraint (indexed by 0/1) the list of signals accross all parts
    
    Returns
    ---------
    (app, inv)
        app: List[Dict[int, List[int]]]

            For each constraint Ci, for each signal sig,  app[Ci][sig] = [I for key appearance in Ci] with I following rules above

        inv: List[List[Dict[int, Set[int]]]]

            For constraint Ci, index I (as above), value val, inv[Ci][I][val] = set([signals in Ci, in part I, with value val])
    """
    
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
    """
    Subordinate function of `single_cons_options` for building appears and inverse lists for constraints with ordered parts.

    Typically parts A and B of a constraint will normalise differently and thus can be ordered. From this we can define an index system
    where the index 0, 1, 2 line up with parts A, B, C. Thus we can define an appears and inverse lists that are defined strictly for
    the input parts.

    Parameters
    ----------
        dicts: List[List[Dict[int, int]]]
            The two constraint parts in list form dict[0] is the left constraint, dict[1] is the right constraint
        _ : None
            Dummy parameter used to ensure has same number of parameters as `_compare_norms_with_unordered_parts`

    Returns
    ---------
    (app, inv)
        app: List[Dict[int, List[int]]]

            For each constraint Ci, for each signal sig,  app[Ci][sig] = [I for key appearance in Ci] with I following rules above

        inv: List[List[Dict[int, Set[int]]]]

            For constraint Ci, index I (as above), value val, inv[Ci][I][val] = set([signals in Ci, in part I, with value val])
    """

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