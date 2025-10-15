"""

Fixes compiler bug where some circuits aren't a single connected component

"""
from typing import List, Tuple
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

    next_int = itertools.count().__next__
    remapp = {k : next_int() for k in sorted(set(dist_from_inputs.keys()).union(dist_from_outputs.keys()))}
    cons_subset = list(filter(lambda coni : all(map(lambda sig : remapp.get(sig, None) != None, circ.constraints[coni].signals())), range(circ.nConstraints)))

    new_circ = circ.take_subcircuit(cons_subset, signal_map=remapp)

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
    signals = set(circ.get_signals())

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

    i = -1
    for signals in signals_by_component:

        if all(map(lambda sig : not circ.signal_is_input(sig) and not circ.signal_is_output(sig), signals)):
            continue
        
        constraints = list(set(itertools.chain.from_iterable(map(lambda sig : signal_to_conis.get(sig, []), signals))))
        if len(constraints) == 0: continue
        i += 1
        for cnt, sig in enumerate(signals): sigmapp[sig] = (i, cnt)
        for cnt, coni in enumerate(constraints): conmapp[coni] = (i, cnt)

        next_circuit = circ.take_subcircuit(constraints, signal_map={sig: sigmapp[sig][1] for sig in signals})
        circuits.append(next_circuit)

    return circuits, sigmapp, conmapp
        


