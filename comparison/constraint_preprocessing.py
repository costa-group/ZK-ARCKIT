from typing import List, Tuple, Dict, Set, Callable

from r1cs_scripts.circuit_representation import Circuit
from r1cs_scripts.constraint import Constraint
from r1cs_scripts.modular_operations import divideP
from normalisation import r1cs_norm
from bij_encodings.assignment import Assignment
from utilities import count_ints
from comparison.static_distance_preprocessing import _distances_to_signal_set
import itertools

constSignal = 0

def sorted_list_handling(LList: List[Tuple], RList: List[Tuple], both_handle: Callable) -> Tuple[List[Tuple], List[Tuple]]:

    in_LR, in_LorR = [], []
    i, j = 0, 0
    while 0 <= i < len(LList) and 0 <= j < len(RList):
        lkey, lval = LList[i]
        rkey, rval = RList[j]

        if lkey < rkey: 
            in_LorR.append(LList[i])
            i += 1
        elif rkey < lkey: 
            in_LorR.append(RList[j])
            j += 1
        else:
            both_val, single_val = both_handle(lval, rval)
            in_LR.append((lkey, both_val))
            if single_val is not None: in_LorR.append((lkey, single_val))
            i += 1
            j += 1
    
    # only actually doing 1, since at least 1 is finished
    in_LorR.extend(itertools.chain(LList[i:], RList[j:]))
    
    return in_LR, in_LorR
        

def known_split(norms: List[Constraint], name, mapp, signal_info) -> str:
        """
        """
        if signal_info is None or mapp is None or name is None:
            return ""
        
        parts = []

        for norm in norms:

            unordered_AB = len(norm.A) > 0 and list(norm.A.values()) == list(norm.B.values())

            sects = []

            for dict_ in [norm.A, norm.B, norm.C]:

                curr = sorted(
                    map(
                        lambda tup : (next(iter(signal_info[name][tup[0]])), tup[1]),
                        filter(
                            lambda tup : tup[0] in signal_info[name].keys() and len(signal_info[name][tup[0]]) == 1,
                            dict_.items()
                        )
                    )
                )

                sects.append(curr)
            
            if unordered_AB:

                sects[0], sects[1] = sorted_list_handling(
                    sects[0], sects[1],
                    lambda l, r : ((min(l,r),max(l,r)), None)
                )

            parts.append(f"{sects[0]}*{sects[1]}+{sects[2]}")

        return str(sorted(parts))

def hash_constraint(
        cons: Constraint, 
        name: str = None, 
        mapp: Assignment = None, 
        signal_info: Dict[str, Dict[int, Set[int]]] = None,
        distances: Dict[str, List[int]] = None):

    def constant_split(C: Constraint) -> str:
        """
        returns 3 bits
            - 1-3rd bits are 1 if A,B,C resp has const. factor
        """

        const_pos = [int(constSignal in part.keys()) for part in [C.A, C.B, C.C]]
        if unordered_AB: const_pos = [const_pos[0] & const_pos[1], const_pos[0] ^ const_pos[1], const_pos[2]]
        return ''.join(map(str,const_pos))

    def distances_split(C: Constraint) -> str:
        """
        List of lists containing sorted count for number of shortest distances to input signal in each part
        """
        if distances is None or name is None:
            return ""
        
        distance_by_part = [[
            count_ints(map(distances[name][source].__getitem__, filter(lambda x : x != 0, dict_.keys())))
            for dict_ in [C.A, C.B, C.C]
        ] for source in distances[name].keys()]

        if unordered_AB:
            for source in range(2):
                distance_by_part[source][0], distance_by_part[source][1] = sorted_list_handling(
                    distance_by_part[source][0], distance_by_part[source][1],
                    lambda l, r : (min(l,r), abs(l-r) if l != r else None)
                )
    
        return str(distance_by_part[0]) + "," + str(distance_by_part[1])
    
    def norm_split(norms: List[Constraint]) -> str:
        """
        returns a sorted list of the normalised constraints in sorted order
        """
        def to_string(cons):
            AB = f"{list(cons.A.values())}*{list(cons.B.values())}" if len(cons.A) * len(cons.B) > 0 else ""
            C = f"{list(cons.C.values())}"

            return f"{AB}+{C}"

        norms = list(map(
            to_string,
            norms
        ))

        # TODO: is there are significant performance dip for having long hashes?
        #   given that usually the list is not more than 4 this seems unlikely.. but something to think about
        return str(norms)
    
    def return_coefs(cons):
        return list(cons.A.values()) + [-1] + list(cons.B.values()) + [-1] + list(cons.C.values())

    norms = r1cs_norm(cons)
    if len(norms) > 1: norms = sorted(norms, key = return_coefs) ## need canonical order for returned normed constraints
    
    unordered_AB = any(map(lambda norm : list(norm.A.values()) == list(norm.B.values()) and len(norm.A) > 0, norms))

    hashes = itertools.chain(
        map(constant_split, norms),
        map(distances_split, norms),
        [known_split(norms, name, mapp, signal_info)],
        [norm_split(norms)]
    )

    return ':'.join(hashes)


def constraint_classes(in_pair: List[ Tuple[str, Circuit] ], clusters: None, signal_info: None, mapp: None):
    assert len(in_pair) > 0, "empty comparisons"
    
    N = in_pair[0][1].nConstraints
    K = in_pair[0][1].nWires

    groups = {
        name:{}
        for name, _ in in_pair
    }
    # separate by constant/quadtratic term
    
    signal_to_distance = {
        name: {
            sourcename: _distances_to_signal_set(circ.constraints, source)
            for sourcename, source in [("input", range(circ.nPubOut+1, circ.nPubOut + circ.nPrvIn + circ.nPubIn + 1)), ("output", range(1, circ.nPubOut+1))]
        }
        for name, circ in in_pair
    }

    hashmapp = Assignment(assignees=1)

    # iterator = itertools.starmap(
    #     lambda i, name, circ = groups[name].setdefault( 
    #         hashmapp.get_assignment(hash_constraint( circ.constraints[i], name, mapp, signal_info, signal_to_distance )), []).append(i),
    #     ...
    # )

    # python loops are really slow... ~22s for 818 simple const 10^4 times..
    for i in range(N):
        for name, circ in in_pair:  
            groups[name].setdefault( hashmapp.get_assignment(hash_constraint( circ.constraints[i], name, mapp, signal_info, signal_to_distance )), []).append(i)

    # group_id = 51

    # print(hashmapp.get_inv_assignment(group_id))

    # LHS = groups["S1"][group_id]
    # RHS = groups["S2"][group_id]
    # print(len(LHS), len(RHS))

    # coni = next(iter(LHS))
    # cons = in_pair[0][1].constraints[coni]
    # norms = r1cs_norm(cons)
    # print(norms[0].A.values(), norms[0].B.values(), norms[0].A.values() == norms[0].B.values(), list(norms[0].A.values()) == list(norms[0].B.values()))
    # print(coni)
    # cons.print_constraint_terminal()

    # raise ValueError

    return groups