from typing import List, Tuple, Dict, Set
from collections import deque
from functools import reduce

from r1cs_scripts.circuit_representation import Circuit
from r1cs_scripts.constraint import Constraint
from utilities.assignment import Assignment
from utilities.utilities import _signal_data_from_cons_list, getvars, _distance_to_signal_set

def distances_to_static_preprocessing(
        in_pair: List[Tuple[str, Circuit]], 
        mapp: Assignment = Assignment(),
        known_signal_info: Dict[str, Dict[int, Set[int]]] = None,
    ):
    """
    Signal preprocessing step, signals are grouped by the distance to inputs and outputs and then grouping signals by this key.
    
    For most circuits this process is quite slow because the quanitity of signals that have the same keys are quite large meaning that
    the memory required to store this information is tool large this function is largely not useful. 
    """

    # default known_signal_mapping
    if known_signal_info is None:

        known_signal_info = {
            name: {}
            for name, _ in in_pair
        }

    assert in_pair[0][1].nPubOut == in_pair[1][1].nPubOut and in_pair[0][1].nPubIn == in_pair[1][1].nPubIn and in_pair[0][1].nPrvIn == in_pair[1][1].nPrvIn, "different input/output numbers"

    circ = in_pair[0][1]
    outputs = range(1, circ.nPubOut+1)
    inputs = range(circ.nPubOut+1, circ.nPubOut + circ.nPrvIn + circ.nPubIn + 1)

    for start in [inputs, outputs]:

        log = {}
    
        for name, circ in in_pair:
            log[name] = _distances_to_signal_set(circ.constraints, start)

        assert set(log[in_pair[0][0]].keys()).symmetric_difference(log[in_pair[1][0]].keys()) == set([]), "different distances found"

        for distance in log[in_pair[0][0]].keys():

            assert len( log[in_pair[0][0]][distance] ) == len( log[in_pair[1][0]][distance] ), "distance has different num of signals"

            for ind in range(2):
                name = in_pair[ind][0]
                oname = in_pair[1-ind][0]

                # TODO: test heuristic -- this stops a memory problem -- maybe think of other fixes
                if len(log[name][distance]) > in_pair[ind][1].nWires * 0.01: continue

                for signal in log[name][distance]:
                    mapped_values = set(map(lambda x : mapp.get_assignment(signal, x) if name == in_pair[0][0] else
                                                       mapp.get_assignment(x, signal), log[oname][distance]))

                    known_signal_info[name][signal] = known_signal_info[name].setdefault(
                        signal, mapped_values).intersection(mapped_values)
        
    return known_signal_info

