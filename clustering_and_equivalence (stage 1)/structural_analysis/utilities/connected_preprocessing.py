"""

Fixes compiler bug where some circuits aren't a single connected component

"""
from typing import List, Tuple
import itertools
import json
from collections import deque

from circuits_and_constraints.abstract_circuit import Circuit
from circuits_and_constraints.abstract_constraint import Constraint

from utilities.utilities import _signal_data_from_cons_list, _distances_to_signal_set

DEBUG_PRINT_LEVEL = 2

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

    new_circ, remapp = circ.take_subcircuit(cons_subset, signal_map=remapp, return_signal_mapping=True)

    return new_circ if not return_mapping else (new_circ, remapp)

def componentwise_preprocessing(circ: Circuit, minimum_circuit_size: int = 100, output_automatic_clusters: bool = True, debug: False = False) -> Tuple[List[Circuit], List[Tuple[int,int] | None], List[Tuple[int,int] | None]]:
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

    if debug >= DEBUG_PRINT_LEVEL: print("------------------ preprocessing --------------------")

    signal_to_conis = _signal_data_from_cons_list(circ.constraints)
    signals = set(circ.get_signals())

    signals_by_component = []

    # TODO: sets? anything better?
    while len(signals) > 0:
        if debug: print(len(signals), "           ", end='\r')
        next_signal = next(iter(signals))

        dist_from_signal = _distances_to_signal_set(circ.constraints, [next_signal], signal_to_conis)
        signals_by_component.append(sorted(dist_from_signal.keys())) # sorted to maintain output/input relationships

        signals.difference_update(dist_from_signal.keys())

    circuits = []
    minimum_size_clusterings = []
    coni_inverse = []
    sig_inverse = []

    i = -1
    for signals in filter(lambda signals: any(map(lambda sig : circ.signal_is_input(sig) or circ.signal_is_output(sig), signals)), signals_by_component):
        if debug >= DEBUG_PRINT_LEVEL: print(f"processing component {i+1} of {len(signals_by_component)}", "           ", end='\r')
        
        constraints = list(set(itertools.chain.from_iterable(map(lambda sig : signal_to_conis.get(sig, []), signals))))
        if len(constraints) == 0: continue
        elif len(constraints) <= minimum_circuit_size: 
            if output_automatic_clusters: minimum_size_clusterings.append(constraints)
            continue
        i += 1

        next_circuit, signal_map = circ.take_subcircuit(constraints, signal_map={sig: cnt for cnt, sig in enumerate(signals)}, return_signal_mapping=True)
        
        sig_inverse.append({val : key for key, val in signal_map.items()})
        coni_inverse.append(constraints)
        circuits.append(next_circuit)

    if debug >= DEBUG_PRINT_LEVEL: print("------------------ end preprocessing --------------------")

    return circuits, minimum_size_clusterings, sig_inverse, coni_inverse
        
def preclustering(circ: Circuit, preclustering_file: str, minimum_circuit_size: int = 100, output_automatic_clusters: bool = True, debug: False = False):

    jsonfile = open(preclustering_file, 'r')
    clustering = json.load(jsonfile)
    jsonfile.close()

    minimum_size_clusterings = []
    circuits = []
    coni_inverse = []
    sig_inverse = []

    i = -1
    for node in clustering["nodes"]:

        if len(node["constraints"]) <= minimum_circuit_size:
            if output_automatic_clusters: minimum_size_clusterings.append(node["constraints"])
            continue

        if any(coni < 0 or circ.nConstraints <= coni for coni in node["constraints"]):
            print(circ.nConstraints)
            print(node["node_id"], node["constraints"])

        i += 1
        next_circuit, signal_map = circ.take_subcircuit(constraint_subset=node["constraints"], input_signals=node["input_signals"], output_signals=node["output_signals"], return_signal_mapping=True)
        sig_inverse.append({val : key for key, val in signal_map.items()})
        coni_inverse.append(node["constraints"])
        circuits.append(next_circuit)
    
    return circuits, minimum_size_clusterings, sig_inverse, coni_inverse

