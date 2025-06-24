"""

Fixes compiler bug where some circuits aren't a single connected component

"""
from typing import List, Tuple
from utilities.utilities import getvars
import itertools

from circuits_and_constraints.abstract_circuit import Circuit
from circuits_and_constraints.abstract_constraint import Constraint

from utilities.utilities import _signal_data_from_cons_list, _distances_to_signal_set

def connected_preprocessing(circ: Circuit, return_mapping: bool = False) -> Circuit | Tuple[Circuit, List[int | None]]:
    """
    Given an input circuit removes all constraints not connected to any inputs

    Parameters
    ----------
        circ: Circuit
            The input circuit
        return_mapping: Bool
            flag that determines whether to return the signal mapping
    
    Returns
    ----------
    Circuit | (Circuit, List[int | None])
        Always returns the new circuit that contains only connected components with inputs
    """
    sig_to_coni = _signal_data_from_cons_list(circ.constraints)

    dist_from_inputs = _distances_to_signal_set(circ.constraints, circ.get_input_signals(), sig_to_coni)
    dist_from_outputs = _distances_to_signal_set(circ.constraints, circ.get_output_signals(), sig_to_coni)

    remapp = [None for _ in range(circ.nWires)]
    remapp[0] = 0

    curr = 1
    for sig in sorted(set(dist_from_inputs.keys()).union(dist_from_outputs.keys())):
        
        remapp[sig] = curr
        curr += 1

    cons_subset = list(filter(lambda coni : all(map(lambda sig : remapp[sig] != None, circ.constraints[coni].signals())), range(circ.nConstraints)))

    new_circ = circ.take_subcircuit(constraint_subset=cons_subset, signal_map=remapp)

    return new_circ if not return_mapping else (new_circ, remapp)

def componentwise_preprocessing(circ: Circuit) -> Tuple[List[Circuit], List[Tuple[int,int] | None], List[Tuple[int,int] | None]]:
    """
    Like connected_preprocessing but additionally splits circuit up into different circuits connected components
    Does not modify input circuit

    Parameters
    ----------
        circ: Circuit
            the input circuit

    Returns 
    ----------
    (circuits, sig_mapp, conmapp)
        - circuits: List[Circuit]

            a list of new circuits,
        - sig_mapp: List[Tuple[int,int] | None]

            a list of where each signal was mapped to (form (i,j): circuit i, new signal j) -- 0 is listed as (0,0) but is a constant
        - conmapp: List[Tuple[int,int] | None]
        
            a list of where each constraint was mapped to (form (i,j): circuit i, new constraint j)
    """

    signal_to_conis = _signal_data_from_cons_list(circ.constraints)
    signals = set(range(1,circ.nWires))

    signals_by_component = []

    # TODO: sets? anything better?
    while len(signals) > 0:
        next_signal = next(iter(signals))

        dist_from_signal = _distances_to_signal_set(circ.constraints, [next_signal], signal_to_conis)
        signals_by_component.append(sorted(dist_from_signal.keys())) # sorted to maintain output/input relationships

        signals.difference_update(dist_from_signal.keys())

    circuits = []
    conmapp = [None for _ in range(circ.nConstraints)]
    sigmapp = [None for _ in range(circ.nWires)]
    sigmapp[0] = (0, 0) # signal 0 is special case

    pubOuts = range(1, 1+circ.nPubOut)
    pubInts = range(1+circ.nPubOut, 1+circ.nPubOut+circ.nPubIn)
    prvInts = range(1+circ.nPubOut+circ.nPubIn, 1+circ.nPubOut+circ.nPubIn+circ.nPrvIn)

    for i, signals in enumerate(signals_by_component):

        if all(map(lambda sig : sig > circ.nPubOut + circ.nPubIn + circ.nPrvIn , signals)):
            continue
        
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
        


