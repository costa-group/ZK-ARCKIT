"""

Fixes compiler bug where some circuits aren't a single connected component

"""
from utilities import getvars

from bij_encodings.assignment import Assignment

from r1cs_scripts.circuit_representation import Circuit

from comparison.static_distance_preprocessing import _distances_to_signal_set
from structural_analysis.graph_clustering.degree_clustering import _signal_data_from_cons_list



def connected_preporcessing(circ: Circuit) -> Circuit:
    """
    modifies input circ, and constraints contained

    Doesn't modify nLabels, since am unsure what this is
    """

    _, signal_to_conis = _signal_data_from_cons_list(circ.constraints)

    inputs = range(circ.nPubOut+1, circ.nPubOut + circ.nPrvIn + circ.nPubIn + 1)
    outputs = range(1, circ.nPubOut+1)

    starting = set([next(iter(inputs))])

    dist_from_inputs = _distances_to_signal_set(circ.constraints, starting, signal_to_conis)

    # Theoreticall all inputs/outputs should be in the same connected component

    if set(inputs).difference(dist_from_inputs.keys()) != set([]):
        raise AssertionError(f"Inputs {set(inputs).difference(dist_from_inputs.keys())} not connected to starting input {starting}")

    if set(outputs).difference(dist_from_inputs.keys()) != set([]):
        raise AssertionError(f"Output {set(outputs).difference(dist_from_inputs.keys())} not connected to starting input {starting}")
    
    ## If this is true, we remap

    remapp = [None for _ in range(circ.nWires)]
    remapp[0] = 0

    curr = 1
    for sig in sorted(dist_from_inputs.keys()):
        
        remapp[sig] = curr
        curr += 1

    new_constraints = []

    for coni in range(circ.nConstraints):
        if all(map(lambda sig : remapp[sig] == None, getvars(circ.constraints[coni]))):          
            continue

        cons = circ.constraints[coni]

        cons.A = {remapp[sig]:value for sig, value in cons.A.items()}
        cons.B = {remapp[sig]:value for sig, value in cons.B.items()}
        cons.C = {remapp[sig]:value for sig, value in cons.C.items()}

        # theoretically not possible
        # if any(map(lambda sig : sig is None, getvars(cons))):
        #     raise AssertionError("partially unreachable constraint")

        new_constraints.append(cons)
    
    circ.constraints = new_constraints
    circ.nConstraints = len(new_constraints)
    circ.nWires = curr

    return circ
