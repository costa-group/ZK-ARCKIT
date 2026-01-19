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

import solver_acir_to_r1cs_phase1
import solver_acir_to_r1cs_phase2

import json


prime = 21888242871839275222246405745257275088548364400416034343698204186575808495617

def normalize_coef(coef):
    coef = int(coef)
    if coef > prime / 2:
        return coef - prime
    else:
        return coef
def parse_air_constraint(constraint, signals):
    coefs_mul = {}
    coefs_linear = {}
    
    for m in constraint["mul"]:
        i = m["witness1"]
        j = m["witness2"]
        coef = m["coeff"]
        ordered_pair = (i, j) if i < j else (j, i)
        coefs_mul[ordered_pair] = normalize_coef(coef)
        signals.add(i)
        signals.add(j)
    
    for m in constraint["linear"]:
        i = m["witness"]
        coef = m["coeff"]
        coefs_linear[i]  = normalize_coef(coef)
        signals.add(i)
    
    if constraint["constant"] != 0 and constraint["constant"] != "0": 
        coefs_linear[-1]  = normalize_coef(constraint["constant"])
    
    return coefs_mul, coefs_linear
        


def parse_circuit(circuit):
    parsed_mul_coefficients = []
    parsed_linear_coefficients = []
    signals = set()
    for c in circuit["constraints"]:
        mul, linear = parse_air_constraint(c, signals)
        parsed_mul_coefficients.append(mul)
        parsed_linear_coefficients.append(linear)
    n_inputs = circuit["inputs"]
    n_outputs = circuit["outputs"]
    n_signals = circuit["number_of_signals"] 
    return parsed_mul_coefficients, parsed_linear_coefficients, (n_inputs), (n_outputs), (n_signals)
    


def build_constraint_aux(signals_A, signals_B, n_aux):
    map_A = {}
    map_B = {}
    map_C = {}
    for i in signals_A:
        map_A[i + 1] = "1"
    for i in signals_B:
        map_B[i + 1] = "1"
    map_C[n_aux + 1] = coef_to_string(-1)
    return (map_A, map_B, map_C)
    

def coef_to_string(coef):
    if coef >= 0:
        return str(coef)
    else:
        return str(coef+ prime)

def build_previous_constraint(A, B, linear, extra_coefs):
    map_A = {}
    map_B = {}
    map_C = {}
    
    for s in A:
        map_A[s + 1] = "1"
    for s in B:
        map_B[s + 1] = "1"
        
    for (s, coef) in linear.items():
        map_C[s + 1] = coef_to_string(coef)
    
    for (s, coef) in extra_coefs.items():
        if coef != 0:
            map_C[s + 1] = coef_to_string(coef)

    return (map_A, map_B, map_C)


def build_constraints(choosen_AB, linear_part_constraints, auxiliar_signals, coefs_for_difs, n_signals):
    constraints = []
    
    index_aux = 0
    
    # Build the new auxiliar constraints
    for (signals_A, signals_B) in auxiliar_signals:
        aux = build_constraint_aux(signals_A, signals_B, n_signals + index_aux)
        constraints.append(aux)
        index_aux += 1
    # Transform the previous constraints
    index_cons = 0
    for linear in linear_part_constraints:    
        (choosen_A, choosen_B) = choosen_AB[index_cons]
        extra_coefs = {}
        if index_cons in coefs_for_difs: 
            extra_coefs = coefs_for_difs[index_cons]
        constraints.append(build_previous_constraint(choosen_A, choosen_B, linear, extra_coefs))
        index_cons += 1
    
    return constraints


def compute_cluster(signal_to_cluster_rep, s1):
    c_s1 = signal_to_cluster_rep[s1]
    if c_s1 != s1:
        return compute_cluster(signal_to_cluster_rep, c_s1)
    else: 
        return s1


def add_constraint_to_clusters_old(signal_to_cluster_rep, c, maxSignal):
    minRep = maxSignal
    for (s1, s2) in c.keys():
        c_s1 = compute_cluster(signal_to_cluster_rep, s1)
        if c_s1 < minRep:
            minRep = c_s1
        c_s2 = compute_cluster(signal_to_cluster_rep, s2)
        if c_s2 < minRep:
            minRep = c_s2
    for (s1, s2) in c.keys():
        c_s1 = compute_cluster(signal_to_cluster_rep, s1)
        signal_to_cluster_rep[c_s1] = minRep
        signal_to_cluster_rep[s1] = minRep

        c_s2 = compute_cluster(signal_to_cluster_rep, s2)
        signal_to_cluster_rep[c_s2] = minRep
        signal_to_cluster_rep[s2] = minRep
        
        

def add_constraint_to_clusters(signal_to_cluster_rep, c, maxSignal):
    # Instead of adding all the signals in the same cluster, this is not needede: divide just considering the signals 
    # (Same constraint in multiple  clusters)
    
    for (s1, s2) in c.keys():
        c_s1 = compute_cluster(signal_to_cluster_rep, s1)
        c_s2 = compute_cluster(signal_to_cluster_rep, s2)
        if c_s1 < c_s2:
            signal_to_cluster_rep[s2] = c_s1
            signal_to_cluster_rep[c_s2] = c_s1
        else:
            signal_to_cluster_rep[s1] = c_s2
            signal_to_cluster_rep[c_s1] = c_s2
    

    

def generate_clusters_old(signals, difs):
    signal_to_cluster = {}
    maxSignal = 0
    for s in signals:
        signal_to_cluster[s] = s
        if s > maxSignal: 
            maxSignal = s
    
    for (c, index) in difs:
        add_constraint_to_clusters_old(signal_to_cluster, c, maxSignal)
    
    cluster_to_constraints = {}
    for (c, index) in difs:
        cluster = 0
        for ((s1, s2), coef) in c.items():
            cluster = compute_cluster(signal_to_cluster, s1)
            break
        if cluster in cluster_to_constraints: 
            cluster_to_constraints[cluster].append((c, index))
        else:
            cluster_to_constraints[cluster] = [(c, index)]
    
    return cluster_to_constraints

def generate_clusters(signals, difs):
    signal_to_cluster = {}
    maxSignal = 0
    for s in signals:
        signal_to_cluster[s] = s
        if s > maxSignal: 
            maxSignal = s
    
    for (c, index) in difs:
        add_constraint_to_clusters(signal_to_cluster, c, maxSignal)
    
    cluster_to_constraints = {}
    for (c, index) in difs:
        cluster = 0
        for ((s1, s2), coef) in c.items():
            cluster = compute_cluster(signal_to_cluster, s1)
            if cluster in cluster_to_constraints: 
                cluster_to_constraints[cluster].append(({(s1, s2): coef}, index))
            else:
                cluster_to_constraints[cluster] = [({(s1, s2): coef}, index)]
    
    return cluster_to_constraints
        


import argparse
parser = argparse.ArgumentParser()

parser.add_argument("filein", help=".json file including the ACIR constraints",
                    type=str)
parser.add_argument("fileout", help= "Output file with the R1CS constraints ")


args=parser.parse_args()


# Opening JSON file
f = open(args.filein)
data = json.load(f)

#print(data)

verbose = True


prime = int(data["prime"])
number_of_functions = data["num_functions"]
if number_of_functions != 1:
    print("The current version only supports circuits with one function")
    exit(1)
else:
    data = data["functions"][0]

# Parse the input file and generate the needed non linear coefficients
non_linear_part_constraints, linear_part_constraints, n_inputs, n_outputs, n_signals = parse_circuit(data)
prime = int(prime)
#######              Hust for texting, get the number of different monomials that the naive approach would add

naive_added_monomials = {}
n_signal_aux = n_signals
for monomials_cons in non_linear_part_constraints:
    isFirst = True
    for mon in monomials_cons.keys():
        if isFirst:
            isFirst = False
        else: 
            if not mon in naive_added_monomials:
                naive_added_monomials[mon] = n_signal_aux
                n_signal_aux += 1
print("Number of added monomials following the naive approach: "+ str(len(naive_added_monomials)))
print("Number of constraint: "+ str(len(non_linear_part_constraints)))



print(naive_added_monomials)

constraints = []

for (mon, n_signal) in naive_added_monomials.items():
    map_A = {mon[0] + 1: "1"}
    map_B = {mon[1] + 1: "1"}
    map_C = {n_signal + 1: coef_to_string(-1)}
    constraints.append((map_A, map_B, map_C))


for i in range(len(non_linear_part_constraints)):
    map_A = {}
    map_B = {}
    map_C = {}
    non_lin = non_linear_part_constraints[i]
    for (mon, coef) in non_lin.items():
        if mon in naive_added_monomials:
            s_aux = naive_added_monomials[mon]
            map_C[s_aux + 1] = coef_to_string(coef)
        else:
            map_A[mon[0] + 1] = coef_to_string(coef)
            map_B[mon[1] + 1] = "1"
    lin = linear_part_constraints[i]
    for (sig, coef) in lin.items():
        map_C[sig + 1] = coef_to_string(coef)
    
    constraints.append((map_A, map_B, map_C))
    
        
            
            

  
      
#######               Rebuild the constraints

if verbose:
    print("# Solution before renaming: ")
    for c in constraints:
        print("### " + str(c))
def apply_correspondence(constraint, renaming):
    new_A = {}
    new_B = {}
    new_C = {}
    
    for (s, coef) in constraint[0].items():
        new_s = renaming[s]
        new_A[new_s] = coef
    for (s, coef) in constraint[1].items():
        new_s = renaming[s]
        new_B[new_s] = coef
    for (s, coef) in constraint[2].items():
        new_s = renaming[s]
        new_C[new_s] = coef
    
    return (new_A, new_B, new_C)

def apply_renaming_signals(constraints, inputs, outputs, signals):
    """
    Aplica un renombrado de señales:
    - outputs → primeras posiciones
    - inputs → siguientes posiciones
    - signals auxiliares → después
    """
    # renaming: diccionario de señal original -> nueva posición
    renaming = {}
    renaming[0] = 0  # La señal 0 siempre mapea a 0
    #print(renaming)
    #print("Outputs: ", outputs)
    #print("Inputs: ", inputs)
    for s in outputs:
        renaming[s+1] = len(renaming)
    for s in inputs:
        renaming[s+1] = len(renaming)
    for s in signals:
        if s not in renaming:
            renaming[s] = len(renaming)
    #print(renaming)
    # Aplicar el renombrado a cada restricción
    for i, c in enumerate(constraints):
        #print("Applying renaming to constraint ", i)
        #print("Before: ", c)
        constraints[i] = apply_correspondence(c, renaming)
        #print("After: ", constraints[i])

apply_renaming_signals(constraints, n_inputs, n_outputs, list(range(1, n_signals + len(naive_added_monomials)+1)))

print("#################### FINISHED RENAMING ####################")


map_result = {}
map_result["prime"] = str(prime)
map_result["constraints"] = constraints
map_result["n_inputs"] = len(n_inputs)
map_result["n_outputs"] = len(n_outputs)
map_result["n_signals"] = n_signals + len(naive_added_monomials) + 1
json_object = json.dumps(map_result, indent = 4, sort_keys=True) 
file = open(args.fileout, "w")
file.write(json_object)


if verbose:
    print("# Solution after renaming: ")
    for c in constraints:
        print("### " + str(c))
print("Total number of auxiliar signals added: ", len(naive_added_monomials))
print("#################### FINISHED REBUILDING ####################")

    
    



