from typing import List, Tuple, Dict, Set

from r1cs_scripts.circuit_representation import Circuit
from r1cs_scripts.constraint import Constraint
from r1cs_scripts.modular_operations import divideP
from normalisation import r1cs_norm
from bij_encodings.assignment import Assignment
from utilities import count_ints

constSignal = 0

def known_split(norms: List[Constraint], name, mapp, signal_info) -> str:
        """
        """
        if signal_info is None or mapp is None or name is None:
            return ""
        
        parts = []

        for norm in norms:

            sects = []

            for dict_ in [norm.A, norm.B, norm.C]:

                curr = sorted(
                    map(
                        lambda tup : (list(signal_info[name][tup[0]])[0], tup[1]),
                        filter(
                            lambda tup : tup[0] in signal_info[name].keys() and len(signal_info[name][tup[0]]) == 1,
                            dict_.items()
                        )
                    )
                )

                sects.append(curr)
            
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
        const_pos = ''.join( [ str(1 if int(constSignal in D.keys()) else 0) for D in [C.A, C.B, C.C]] ) # maybe reduce hash len?

        return const_pos

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
    
        return str(distance_by_part[0]) + ":" + str(distance_by_part[1])
    
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
    
    hashes = [
        constant_split(cons),
        distances_split(cons),
        known_split(norms, name, mapp, signal_info),
        norm_split(norms,)
    ]

    return ':'.join(hashes)

def constraint_classes(in_pair: List[ Tuple[str, Circuit] ]):
    assert len(in_pair) > 0, "empty comparisons"
    
    N = in_pair[0][1].nConstraints
    K = in_pair[0][1].nWires

    groups = {
        name:{}
        for name, _ in in_pair
    }
    # separate by constant/quadtratic term
        

    # python loops are really slow... ~22s for 818 simple const 10^4 times..
    for i in range(N):
        for name, circ in in_pair:
            
            groups[name].setdefault( hash_constraint( circ.constraints[i] ), []).append(i)

    return groups