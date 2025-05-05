from typing import List, Tuple, Dict, Set, Callable
from functools import reduce
import itertools
import collections

from r1cs_scripts.circuit_representation import Circuit
from r1cs_scripts.constraint import Constraint
from normalisation import r1cs_norm
from utilities.assignment import Assignment


constSignal = 0

def sorted_list_handling(LList: List[Tuple], RList: List[Tuple], both_handle: Callable) -> Tuple[List[Tuple], List[Tuple]]:
    """
    Given two sorted list inputs it returns in_LR the sorted list of elements in both and in_LorR the sorted lsit of elements not in both
    """

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
        

def known_split(norms: List[Constraint], name: str, mapp: Assignment, signal_info: dict, unordered_AB: bool) -> str:
        """
        For any signal that has a forced pair (only 1 option in signal_info), in the constraint then for each norm
        assign the pair key the value in the constraint norm
        """
        if signal_info is None or mapp is None or name is None:
            return ""
        
        parts = []

        for norm in norms:

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
        nOutputs: int = None,
        nInputs: int = None
        ):
    """
    For an input constraint returns a string hash that keys information based on
        - in which parts the constraint has a constant signal term
        - in which parts the constraint has input/output signals in the circuit
        - known signals pairs between the two constraints
        - the normalised constraint
    """

    def constant_split(C: Constraint) -> str:
        """
        returns 3 bits
            - 1-3rd bits are 1 if A,B,C resp has const. factor
        """

        const_pos = [int(constSignal in part.keys()) for part in [C.A, C.B, C.C]]
        if unordered_AB: const_pos = [const_pos[0] & const_pos[1], const_pos[0] ^ const_pos[1], const_pos[2]]
        return ''.join(map(str,const_pos))

    def input_outputs_split(C: Constraint) -> str:
        """
        provides location info on number of inputs/outputs

        replaces distances split with label passing handling the same info
        """
        if nInputs is None or nOutputs is None: return ""

        num_per_part = [
            reduce(
                lambda acc, sig : (acc[0], acc[1] + 1) if 0 < sig <= nOutputs else ( (acc[0] + 1, acc[1]) if nOutputs < sig <= nOutputs + nInputs else acc),
                part.keys(),
                (0, 0)
            ) for part in [C.A, C.B, C.C]
        ]

        if unordered_AB:
            vals = list(zip(*num_per_part[:2]))

            num_per_part[0] = tuple(itertools.starmap(min, vals))
            num_per_part[1] = tuple(itertools.starmap(lambda l, r : abs(l - r), vals))

        return ";".join(map(str, num_per_part))
    
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
        map(input_outputs_split, norms),
        [known_split(norms, name, mapp, signal_info, unordered_AB)],
        [norm_split(norms)]
    )

    return ':'.join(hashes)


def constraint_classes(in_pair: List[ Tuple[str, Circuit] ], clusters: None, signal_info: None, mapp: None):
    "For each constraint, hash the constraint and group the constraints by the hash"
    assert len(in_pair) > 0, "empty comparisons"
    
    N = in_pair[0][1].nConstraints

    groups = {
        name:{}
        for name, _ in in_pair
    }
    # separate by constant/quadtratic term

    hashmapp = Assignment(assignees=1)

    collections.deque(maxlen = 0, iterable = itertools.starmap(
        lambda coni, circi : groups[in_pair[circi][0]].setdefault( 
            hashmapp.get_assignment(hash_constraint(in_pair[circi][1].constraints[coni], in_pair[circi][0], mapp, signal_info)), []).append(coni),
        itertools.product(range(N), range(2))
    ))

    return groups