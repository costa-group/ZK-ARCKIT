from typing import List, Tuple, Dict, Set
from collections import deque

from r1cs_scripts.circuit_representation import Circuit
from r1cs_scripts.constraint import Constraint
from bij_encodings.assignment import Assignment
from structural_analysis.graph_clustering.degree_clustering import _signal_data_from_cons_list

def getvars(con: Constraint) -> set:
    return set(con.A.keys()).union(con.B.keys()).union(con.C.keys()).difference(set([0]))

def distances_to_static_preprocessing(
        in_pair: List[Tuple[str, Circuit]], 
        assumptions: Set[int] = set([]),
        mapp: Assignment = Assignment(),
        known_signal_info: Dict[str, Dict[int, Set[int]]] = None,
    ):

    # default known_signal_mapping
    if known_signal_info is None:

        known_signal_info = {
            name: {}
            for name, _ in in_pair
        }

        for bij in filter( lambda x : 0 < x < len(mapp.assignment), assumptions ):
            l, r = mapp.get_inv_assignment(bij)
            known_signal_info[in_pair[0][0]].setdefault(l, set([])).add(bij)
            known_signal_info[in_pair[1][0]].setdefault(r, set([])).add(bij)

    assert in_pair[0][1].nPubOut == in_pair[1][1].nPubOut and in_pair[0][1].nPubIn == in_pair[1][1].nPubIn and in_pair[0][1].nPrvIn == in_pair[1][1].nPrvIn, "different input/output numbers"

    circ = in_pair[0][1]
    outputs = range(1, circ.nPubOut+1)
    inputs = range(circ.nPubOut+1, circ.nPubOut + circ.nPrvIn + circ.nPubIn + 1)

    for start in [inputs, outputs]:

        log = {}
    
        for name, circ in in_pair:
            # just BFS

            _, signal_to_conis = _signal_data_from_cons_list(circ.constraints)

            checked = {v: True for v in start}
            log[name] = {}

            curr = 0
            queue = deque(list(start) + ["increment"])
            
            while len(queue) > 1:
                next = queue.popleft()

                # technically less efficient to have least occuring first but easier to read
                if next == "increment":
                    curr += 1
                    queue.append("increment")
                else:
                    # default case
                    log[name].setdefault(curr, []).append(next)

                    neighbourhood = set([])
                    for coni in signal_to_conis[next]:
                        neighbourhood.update(getvars(circ.constraints[coni]))

                    neighbourhood = list(filter(lambda signal : checked.setdefault(signal, False) is False, neighbourhood))
                    for v in neighbourhood: checked[v] = True

                    queue.extend(neighbourhood)

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
    
    # TODO: make this redudant by having a standard check elsewhere (maybe once before adding assumptions in?)
    for name, _ in in_pair:
        for signal in known_signal_info[name].keys():
            if len(known_signal_info[name][signal]) == 1:
                assumptions.add(list(known_signal_info[name][signal])[0])
        
    return known_signal_info

