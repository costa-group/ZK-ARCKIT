
from typing import List, Tuple, Dict, Set
from pysat.formula import CNF

from r1cs_scripts.circuit_representation import Circuit
from r1cs_scripts.constraint import Constraint
from utilities.assignment import Assignment

from utilities.utilities import _signal_data_from_cons_list, getvars

"""
Seems to provide literally the same info as iterated_adj_reclassing, makes sense since signals are the edges in the graph
"""

# Works as a cons preprocessing part of the function
def signal_constraint_fingerprinting(
        in_pair: List[Tuple[str, Circuit]],
        classes: Dict[str, Dict[str, List[int]]], 
        clusters: None, 
        mapp: Assignment, 
        ckmapp: Assignment, 
        assumptions: Set[int], 
        formula: CNF, 
        signal_info: Dict[str, Dict[int, Set[int]]] = None,
        debug: bool = False
    ) -> Tuple[Dict[str, Dict[str, List[int]]], Dict[str, Dict[int, Set[int]]]]:

    # First round of classes clustering done beforehand
    signal_to_coni = {
        name: _signal_data_from_cons_list(circ.constraints)
        for name, circ in in_pair
    }

    coni_to_hash = None
    signal_to_hash = None

    def signal_hash(sig: int, name: str, circ: Circuit) -> str:
        # assert (name, circ) in in_pair

        return str(sorted(map(
            lambda coni : coni_to_hash[name][coni], 
            signal_to_coni[name][sig])))

    def coni_signal_hash(coni: int, con: Constraint, name: str):
        
        return str(sorted(map(
            lambda sig : signal_to_hash[name][sig],
            getvars(con)
        )))

    i = 0
    while True:
        i += 1

        # compute coni_to_hash

        chashmapp = Assignment(assignees=1)

        coni_to_hash = {
            name: [None for _ in range(in_pair[0][1].nConstraints)]
            for name, _ in in_pair
        }

        for name, _ in in_pair:
            for key, class_ in classes[name].items():
                rehash = chashmapp.get_assignment(key)

                for coni in class_: coni_to_hash[name][coni] = rehash

        # compute signal_to_hash

        signal_to_hash = {
            name : [None] + [signal_hash(sig, name, circ) for sig in range(1, circ.nWires)]
            for name, circ in in_pair
        }
        
        # recompute classes

        renaming = Assignment(assignees=2)

        new_classes = {
            name: {}
            for name, _ in in_pair
        }

        for key in classes[in_pair[0][0]].keys():

            for name, circ in in_pair:

                if len(classes[name][key]) == 1:
                    hash_ = str(renaming.get_assignment(key, 0))
                    new_classes[name][hash_] = classes[name][key]
                    continue
                
                for coni in classes[name][key]:
                    hash_ = str(renaming.get_assignment(key, coni_signal_hash(coni, circ.constraints[coni], name)))
                    new_classes[name].setdefault(hash_, []).append(coni)

        # if same size break
        if len(new_classes[in_pair[0][0]]) == len(classes[in_pair[0][0]]):
            break

        classes = new_classes

        for key in set(classes[in_pair[0][0]].keys()).union(classes[in_pair[1][0]].keys()):
            for name, _ in in_pair:
                if key not in classes[name].keys():
                    raise AssertionError(f"Error it {i}: Group with fingerprint {key, renaming.get_inv_assignment(int(key))} not in circuit {name}")
            
            if len(classes[in_pair[0][0]][key]) != len(classes[in_pair[1][0]][key]):
                raise AssertionError(f"Error it {i}: Group with fingerprint {key} has size {len(classes['S1'][key])} in 'S1', and {len(classes['S2'][key])} in 'S2'")
    
    # input into signal_info
    signal_classes = {name: {} for name, _ in in_pair}
    for name, circ in in_pair:
        for sig in range(1, circ.nWires):
            signal_classes[name].setdefault(signal_to_hash[name][sig], []).append(sig)
    
    if signal_info is None:
        signal_info = {name: {} for name, _ in in_pair}

    for i, (name, _) in enumerate(in_pair):
        oname = in_pair[1-i][0]

        for key in signal_classes[name].keys():
            for sig in signal_classes[name][key]:

                to_map = signal_classes[oname][key]

                if sig in signal_info[name].keys():
                    to_map = set(map(lambda x : mapp.get_inv_assignment(x)[1-i], signal_info[name][sig])).intersection(to_map)

                signal_info[name][key] = list(map(lambda osig : mapp.get_assignment(*((sig, osig) if i == 0 else (osig, sig))), to_map))

    return classes, signal_info
