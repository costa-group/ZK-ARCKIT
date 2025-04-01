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

import solver_linear_to_plonk_matrix_inc_old
import solver_linear_to_plonk_matrix_inc
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
    


def build_linear_constraint_aux(naux, used_signals):
    constraint = {}
    
    constraint["s_a"] = used_signals[0]
    constraint["coef_a"] = 1
    constraint["s_b"] = used_signals[1]
    constraint["coef_b"] = 1

    constraint["s_c"] = naux
    constraint["coef_c"] = -1
    
    return constraint
    
    

def build_linear_previous_constraint(coefficients):
    found_a = False
    found_b = False

    constraint = {}
    for (s, coef) in coefficients:
        if s == -1:
            constraint["coef_cte"] = coef
        elif not found_a:
            constraint["s_a"] = s
            constraint["coef_a"] = coef
            found_a = True
        elif not found_b:
            constraint["s_b"] = s
            constraint["coef_b"] = coef
            found_b = True
        else: 
            constraint["s_c"] = s
            constraint["coef_c"] = coef
            
    return constraint
    
    

def build_linear_constraints(signals_aux, new_constraints, nsignals):
    constraints = []
    
    index_aux = 0
    # Build the new auxiliar constraints
    for used in signals_aux:
        constraints.append(build_linear_constraint_aux(nsignals + index_aux, used))
        index_aux += 1
    
    # Transform the previous constraints
    for linear in new_constraints:    
        constraints.append(build_linear_previous_constraint(linear))
    
    return constraints



import argparse
parser = argparse.ArgumentParser()

parser.add_argument("filein", help=".json file including the ACIR constraints",
                    type=str)
parser.add_argument("n", help="Maximum number of admited aux signals for the linear transformation",
                    type=str)
parser.add_argument("max", help="Maximum multiplier for linear expressions",
                    type=str)
#parser.add_argument("fileout", help= "Output file with the PLONK constraints ")


args=parser.parse_args()


# Opening JSON file
f = open(args.filein)
data = json.load(f)

#print(data)

# Parse the input file and generate the needed non linear coefficients
non_linear_part_constraints, linear_part_constraints, n_signals = parse_circuit(data)

for c in linear_part_constraints:
    print(c)

# Generate the Z3 problem and solve it
#naux,sol = solver_linear_to_plonk_matrix.generate_problem_plonk_transformation(linear_part_constraints, n_signals, int(args.n),int(args.max))
naux,sol = solver_linear_to_plonk_matrix_inc.generate_problem_plonk_transformation(linear_part_constraints, n_signals, int(args.n),int(args.max))
#naux,sol = solver_linear_to_plonk_matrix_inc_old.generate_problem_plonk_transformation(linear_part_constraints, n_signals, int(args.n),int(args.max))


# Rebuild the constraints
if naux == -1:
    print("UNSAT: The number of auxiliar variables is not enough, try with more")
else:
    print("SAT: Found solution using " + str(naux) + " auxiliar variables and " +str(len(sol)) + " constraints")
    for i in sol:
        print(i)
     
    #constraints = build_linear_constraints(signals_aux, new_constraints, n_signals)
    #map_result = {}
    #map_result["constraints"] = constraints
    #json_object = json.dumps(map_result, indent = 4, sort_keys=True) 
    #file = open(args.fileout, "w")
    #file.write(json_object)

    
    
    
    
    



