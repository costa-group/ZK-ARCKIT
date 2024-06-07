from typing import List, Tuple

from r1cs_scripts.circuit_representation import Circuit
from r1cs_scripts.constraint import Constraint
from normalisation import r1cs_norm

constSignal = 0

def hash_constraint(cons: Constraint):

    def constant_quadratic_split(C: Constraint) -> str:
        """
        returns 4 length string
            - first bit is has quad
            - 2-4th are the const factor of A.B C has a constant factor
        """
        has_quad  =  str(int(len(C.A) * len(C.B) != 0))
        const_pos = ''.join( [ str(1 if int(constSignal in D.keys()) else 0) for D in [C.A, C.B, C.C]] ) # maybe reduce hash len?

        return has_quad + const_pos          

    def length_split(C: Constraint) -> str:
        """
        returns 3 lengths of A, B, C
        """
        return '_'.join([str(len(D)) for D in [C.A, C.B, C.C]])
    
    def norm_split(C: Constraint) -> str:
        """
        returns a sorted list of the normalised constraints in sorted order
        """
        def to_string(cons):
            AB = f"{list(cons.A.values())}*{list(cons.B.values())}" if len(cons.A) * len(cons.B) > 0 else ""
            C = f"{list(cons.C.values())}"

            return f"{AB}+{C}"
        
        def return_sorted_coefs(cons):
            return list(cons.A.values()) + list(cons.B.values()) + list(cons.C.values())

        norms = r1cs_norm(C)
        if len(norms) > 1: norms = sorted(norms, key = return_sorted_coefs) ## need canonical order for returned normed constraints
        norms = list(map(
            to_string,
            norms
        ))

        # TODO: is there are significant performance dip for having long hashes?
        #   given that usually the list is not more than 4 this seems unlikely.. but something to think about
        return str(norms)
    
    hashes = [
        constant_quadratic_split(cons),
        length_split(cons),
        norm_split(cons)
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
            
            groups[name].setdefault(hash_constraint( circ.constraints[i] ), []).append(i)

    return groups