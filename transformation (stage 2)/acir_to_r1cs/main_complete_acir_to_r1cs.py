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
    


def build_previous_constraint(A, B, linear, extra_coefs):
    map_A = {}
    map_B = {}
    map_C = {}
    
    for s in A:
        map_A[s + 1] = 1
    for s in B:
        map_B[s + 1] = 1
        
    for (s, coef) in linear.items():
        map_C[s + 1] = coef
    
    for (s, coef) in extra_coefs.items():
        map_C[s + 1] = coef
    
    return (map_A, map_B, map_C)


def build_constraints(choosen_AB, linear_part_constraints, auxiliar_signals, coefs_for_difs, n_signals):
    constraints = []
    
    index_aux = 0
    
    # Build the new auxiliar constraints
    for (signals_A, signals_B) in auxiliar_signals:
        constraints.append(build_constraint_aux(signals_A, signals_B, n_signals + index_aux))
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

def add_constraint_to_clusters(signal_to_cluster_rep, c, maxSignal):
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
        for (s1, s2) in c.keys():
            cluster = compute_cluster(signal_to_cluster, s1)
            break
        if cluster in cluster_to_constraints: 
            cluster_to_constraints[cluster].append((c, index))
        else:
            cluster_to_constraints[cluster] = [(c, index)]
    
    return cluster_to_constraints
        


import argparse
parser = argparse.ArgumentParser()

parser.add_argument("filein", help=".json file including the ACIR constraints",
                    type=str)
parser.add_argument("n", help="Maximum number of admited aux signals",
                    type=str)
parser.add_argument("fileout", help= "Output file with the R1CS constraints ")


args=parser.parse_args()


# Opening JSON file
f = open(args.filein)
data = json.load(f)

#print(data)






# Parse the input file and generate the needed non linear coefficients
non_linear_part_constraints, linear_part_constraints, n_signals = parse_circuit(data)




#######              Phase 1 ---> Build the A and B expressions for each constraint minimizing the difference


remaining_difs = []
index = 0
complete_signals_in_difs = set()

choosen_AB = []


for constraint in non_linear_part_constraints:
    signals = set()
    for (coef_i, coef_j) in constraint.keys():
        signals.add(coef_i)
        signals.add(coef_j)
        
    print("For constraint ", constraint)
    expr_A, expr_B, difs = solver_acir_to_r1cs_phase1.generate_problem_r1cs_transformation(constraint, list(signals))
    print("### Choosen A: ", expr_A)
    print("### Choosen B: ", expr_B)
    choosen_AB.append((expr_A, expr_B))
    if len(difs) != 0:
        print("### REMAINING NON LINEAR (to solve later): ", difs) 
        remaining_difs.append((difs, index))
        
        for (s1, s2) in difs.keys():
            complete_signals_in_difs.add(s1)
            complete_signals_in_difs.add(s2)
    else: 
        print("### CONSTRAINT SOLVED (no difs)")
    index += 1

print("#################### FINISHED PHASE 1 ####################")
    
#######              Clustering of the difs obtained to reduce the problem considered in phase 2

clusters = generate_clusters(complete_signals_in_difs, remaining_difs)
print("Clusters of constraints that need to be solved: ", clusters)
print("#################### FINISHED CLUSTERING ####################")

#######              Phase 2 ----> Build auxiliar signals to eliminate the difs

total_number_of_aux = 0
auxiliar_signals = []
coefs_for_difs = {}
      
for (n_clus, constraints) in clusters.items():    
    signals = set()
    cons_sys = []
    indexes = []
    # Build the set of signals and the constraint system:
    for (c, index) in constraints:
        for (s1, s2) in c:
            signals.add(s1)
            signals.add(s2)
        cons_sys.append(c)
        indexes.append(index)
    
    
    # Generate the Z3 problem and solve it
    
    ### TODO: instead of using args.n compute a pesimistic bound for the number of signals
    signals = list(signals)
    naux, coefs, signals_aux = solver_acir_to_r1cs_phase2.generate_problem_r1cs_transformation(cons_sys, signals, int(args.n))
    if naux == -1:
        print("UNSAT: The number of auxiliar variables is not enough, try with more")
    else:
        print("SAT: Found solution for the cluster using " +str(naux) + " variables")
    
    # Update the info of the complete circuit    
    auxiliar_signals.extend(signals_aux)
    for index in indexes:
        s = 0
        coefs_index = {}
        for coefs_s in coefs:
            real_s = total_number_of_aux + n_signals + s
            if coefs_s[s] != 0:
                coefs_index[real_s] = coefs_s[s]
            s += 1
        coefs_for_difs[index] = coefs_index
    
    total_number_of_aux += naux

print("#################### FINISHED PHASE 2 ####################")
      
      
      
#######               Rebuild the constraints

constraints = build_constraints(choosen_AB, linear_part_constraints, auxiliar_signals, coefs_for_difs, n_signals)
map_result = {}
map_result["constraints"] = constraints
json_object = json.dumps(map_result, indent = 4, sort_keys=True) 
file = open(args.fileout, "w")
file.write(json_object)


print(constraints)
print("Total number of auxiliar signals added: ", total_number_of_aux)
print("#################### FINISHED REBUILDING ####################")

    
    



