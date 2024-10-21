"""

Fixes compiler bug where some circuits aren't a single connected component

"""
from typing import List, Tuple
from utilities import getvars
import itertools

from r1cs_scripts.circuit_representation import Circuit
from r1cs_scripts.constraint import Constraint

from comparison.static_distance_preprocessing import _distances_to_signal_set
from utilities import _signal_data_from_cons_list

def connected_preprocessing(circ: Circuit, return_mapping: bool = False) -> Circuit | Tuple[Circuit, List[int | None]]:
    """
    Given an input circuit removes all constraints not connected to any inputs
    """

    outputs = range(1, 1+circ.nPubOut)
    inputs = range(circ.nPubOut+1, circ.nPubOut + circ.nPrvIn + circ.nPubIn + 1)

    sig_to_coni = _signal_data_from_cons_list(circ.constraints)

    dist_from_inputs = _distances_to_signal_set(circ.constraints, inputs, sig_to_coni)
    dist_from_outputs = _distances_to_signal_set(circ.constraints, outputs, sig_to_coni)

    remapp = [None for _ in range(circ.nWires)]
    remapp[0] = 0

    curr = 1
    for sig in sorted(set(dist_from_inputs.keys()).intersection(dist_from_outputs.keys())):
        
        remapp[sig] = curr
        curr += 1

    new_circ = Circuit()

    for coni in range(circ.nConstraints):

        # equivalent to any due to how distances are calculated
        if all(map(lambda sig : remapp[sig] == None, getvars(circ.constraints[coni]))):          
            continue

        new_circ.constraints.append(Constraint(
            *[{remapp[sig]:value for sig, value in dict_.items()} for dict_ in 
              [circ.constraints[coni].A, circ.constraints[coni].B, circ.constraints[coni].C]],
            circ.constraints[coni].p))
    
    
    pubInts = range(1+circ.nPubOut, 1+circ.nPubOut+circ.nPubIn)
    prvInts = range(1+circ.nPubOut+circ.nPubIn, 1+circ.nPubOut+circ.nPubIn+circ.nPrvIn)

    in_next_circuit = lambda sig : remapp[sig] is not None

    new_circ.update_header(
        circ.field_size, circ.prime_number, curr,
        nPubOut=len(list(filter(in_next_circuit, outputs))),
        nPubIn=len(list(filter(in_next_circuit, pubInts))),
        nPrvIn=len(list(filter(in_next_circuit, prvInts))),
        nLabels=None, # ??
        nConstraints=len(new_circ.constraints)
        )

    return new_circ if not return_mapping else (new_circ, remapp)

def componentwise_preprocessing(circ: Circuit) -> Tuple[List[Circuit], List[Tuple[int,int] | None], List[Tuple[int,int] | None]]:
    """
    Like connected_preprocessing but additionally splits circuit up into different circuits connected components
    Does not modify input circuit

    Returns 
        a list of new circuits,
        a list of where each signal was mapped to (form (i,j): circuit i, new signal j) -- 0 is listed as (0,0) but is a constant
        a list of where each constraint was mapped to (form (i,j): circuit i, new constraint j)
    """

    signal_to_conis = _signal_data_from_cons_list(circ.constraints)
    inputs = set(range(circ.nPubOut+1, circ.nPubOut + circ.nPrvIn + circ.nPubIn + 1))

    signals_by_component = []

    # TODO: sets? anything better?
    while len(inputs) > 0:
        next_input = next(iter(inputs))

        dist_from_inputs = _distances_to_signal_set(circ.constraints, [next_input], signal_to_conis)
        signals_by_component.append(sorted(dist_from_inputs.keys())) # sorted to maintain output/input relationships

        inputs.difference_update(dist_from_inputs.keys())

    circuits = []
    conmapp = [None for _ in range(circ.nConstraints)]
    sigmapp = [None for _ in range(circ.nWires)]
    sigmapp[0] = (0, 0) # signal 0 is special case

    pubOuts = range(1, 1+circ.nPubOut)
    pubInts = range(1+circ.nPubOut, 1+circ.nPubOut+circ.nPubIn)
    prvInts = range(1+circ.nPubOut+circ.nPubIn, 1+circ.nPubOut+circ.nPubIn+circ.nPrvIn)

    for i, signals in enumerate(signals_by_component):

        next_circuit = Circuit()

        for cnt, sig in enumerate(signals): sigmapp[sig] = (i, cnt + 1)

        constraints = set(itertools.chain(*map(signal_to_conis.__getitem__, signals)))

        for coni in constraints:
            conmapp[coni] = (i, len(next_circuit.constraints))
            next_circuit.constraints.append(Constraint(
                *[
                    { sigmapp[key][1] : val for key, val in dic.items()}
                    for dic in [ circ.constraints[coni].A, circ.constraints[coni].B, circ.constraints[coni].C ]
                ],
                circ.prime_number
            ))

        in_next_circuit = lambda sig : sigmapp[sig] is not None and sigmapp[sig][0] == i

        next_circuit.update_header( circ.field_size, circ.prime_number, len(signals) + 1,
            nPubOut=len(list(filter(in_next_circuit, pubOuts))),
            nPubIn=len(list(filter(in_next_circuit, pubInts))),
            nPrvIn=len(list(filter(in_next_circuit, prvInts))),
            nLabels=None, # ??
            nConstraints=len(next_circuit.constraints)
        )
        circuits.append(next_circuit)

    return circuits, sigmapp, conmapp
        


