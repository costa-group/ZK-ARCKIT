#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar 17 18:45:27 2025

@author: clara
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar 17 15:07:28 2025

@author: clara
"""

import solver_linear_to_plonk
import json


# TODO: only consider as signals the ones that appear at the non-linear part -> renaming between how studied when minimizing the non linear part 

def parse_air_constraint(constraint, signals):
    coefs_mul = {}
    coefs_linear = {}
    
    for m in constraint["mul"]:
        i = m["witness1"]
        j = m["witness2"]
        coef = m["coeff"]
        ordered_pair = (i, j) if i < j else (j, i)
        coefs_mul[ordered_pair] = coef
        signals.add(i)
        signals.add(j)
    
    for m in constraint["linear"]:
        i = m["witness"]
        coef = m["coeff"]
        coefs_linear[i] = coef
        signals.add(i)
    
    if constraint["constant"] != 0 and constraint["constant"] != "0": 
        coefs_linear[-1] =  constraint["constant"]
    
    return coefs_mul, coefs_linear
        


def parse_circuit(circuit):
    parsed_mul_coefficients = []
    parsed_linear_coefficients = []
    signals = set()
    for c in circuit["constraints"]:
        mul, linear = parse_air_constraint(c, signals)
        parsed_mul_coefficients.append(mul)
        parsed_linear_coefficients.append(linear)
    return parsed_mul_coefficients, parsed_linear_coefficients, len(signals)
    


def build_constraint_aux(signals_A, signals_B, n_aux):
    map_A = {}
    map_B = {}
    map_C = {}
    for i in signals_A:
        map_A[i + 1] = 1
    for i in signals_B:
        map_B[i + 1] = 1
    map_C[n_aux + 1] = -1
    return (map_A, map_B, map_C)
    


def build_previous_constraint(coefs, constraint_index, linear_coefficients, n_signals):
    map_A = {}
    map_B = {}
    map_C = {}
        
    for (s, coef) in linear_coefficients.items():
        map_C[s + 1] = coef
    
    index = 0
    for coefs_signal in coefs:
        coef = coefs_signal[constraint_index]
        if coef != 0:
            map_C[n_signals + index + 1] = coef
        index += 1
    
    return (map_A, map_B, map_C)


def build_constraints(coefs, signals_aux, linear_part_constraints, n_signals):
    constraints = []
    
    index_aux = 0
    # Build the new auxiliar constraints
    for (signals_A, signals_B) in signals_aux:
        constraints.append(build_constraint_aux(signals_A, signals_B, index_aux))
        index_aux += 1
    
    # Transform the previous constraints
    index_cons = 0
    for linear in linear_part_constraints:    
        constraints.append(build_previous_constraint(coefs, index_cons, linear, n_signals))
        index_cons += 1
    
    return constraints



import argparse
parser = argparse.ArgumentParser()

parser.add_argument("filein", help=".json file including the ACIR constraints",
                    type=str)
parser.add_argument("n", help="Maximum number of admited aux signals for the linear transformation",
                    type=str)
parser.add_argument("fileout", help= "Output file with the PLONK constraints ")


args=parser.parse_args()


# Opening JSON file
f = open(args.filein)
data = json.load(f)

print(data)

# Parse the input file and generate the needed non linear coefficients
non_linear_part_constraints, linear_part_constraints, n_signals = parse_circuit(data)

#print(constraints)

# Generate the Z3 problem and solve it
solver_linear_to_plonk.generate_problem_plonk_transformation(linear_part_constraints, n_signals, int(args.n))


# Rebuild the constraints
# =============================================================================
# if naux == -1:
#     print("UNSAT: The number of auxiliar variables is not enough, try with more")
# else:
#     print("SAT: Found solution using " +str(naux) + " variables")
#     
#     constraints = build_constraints(coefs, signals_aux, linear_part_constraints, n_signals)
#     map_result = {}
#     map_result["constraints"] = constraints
#     json_object = json.dumps(map_result, indent = 4, sort_keys=True) 
#     file = open(args.fileout, "w")
#     file.write(json_object)
# =============================================================================

    
    
    
    
    



