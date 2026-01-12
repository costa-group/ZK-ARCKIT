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
    next_signal = circuit["next_id_signal"]
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
        map_C[s + 1] = coef_to_string(coef)

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
                cluster_to_constraints[cluster] = [({(s1, s2): index}, index)]
    
    return cluster_to_constraints
        


import argparse
import copy
parser = argparse.ArgumentParser()

parser.add_argument("filein", help=".json file including the ACIR constraints",
                    type=str)
parser.add_argument("structure", help="Structure to use for the clustering",
                    type=str)   
parser.add_argument("n", help="Maximum number of admited aux signals",
                    type=str)
parser.add_argument("fileout", help= "Output file with the R1CS constraints ",
                    type=str)


args=parser.parse_args()


# Opening JSON file
f = open(args.filein)
data = json.load(f)

f = open(args.structure)
structure = json.load(f)
##print(data)

verbose = False


prime = int(data["prime"])
number_of_functions = data["num_functions"]
if number_of_functions != 1:
    #print("The current version only supports circuits with one function")
    exit(1)
else:
    data = data["functions"][0]

# Parse the input file and generate the needed non linear coefficients

def parse_cluster(data,prime):
    print(data)
    next_signal = data["next_id_signal"]
    non_linear_part_constraints, linear_part_constraints, n_inputs, n_outputs, n_signals  = parse_circuit(data)
    #######              Hust for texting, get the number of different monomials that the naive approach would add
    #print("veamos",non_linear_part_constraints, linear_part_constraints, n_inputs, n_outputs, n_signals)
    naive_added_monomials = set()
    for monomials_cons in non_linear_part_constraints:
        isFirst = True
        for mon in monomials_cons.keys():
            if isFirst:
                isFirst = False
            else: 
                naive_added_monomials.add(mon)
    #print("Number of added monomials following the naive approach: "+ str(len(naive_added_monomials)))
    #print("Number of constraint: "+ str(len(non_linear_part_constraints)))




    #######              Phase 1 ---> Build the A and B expressions for each constraint minimizing the difference


    remaining_difs = []
    index = 0
    complete_signals_in_difs = set()

    choosen_AB = []

    number_solved = 0
    max_difs = 0


    for constraint in non_linear_part_constraints:
        signals = set()
        for (coef_i, coef_j) in constraint.keys():
            signals.add(coef_i)
            signals.add(coef_j)
            
        if verbose:
            print("For constraint ", constraint)
        expr_A, expr_B, difs = solver_acir_to_r1cs_phase1.complete_phase1_transformation(constraint, list(signals), verbose)
        if verbose:
            print("### Choosen A: ", expr_A)
            print("### Choosen B: ", expr_B)
        choosen_AB.append((expr_A, expr_B))
        if len(difs) != 0:
            if len(difs) > max_difs:
                max_difs = len(difs)
            
            if verbose:
                print("### REMAINING NON LINEAR (to solve later): ", difs) 
            remaining_difs.append((difs, index))
            
            for (s1, s2) in difs.keys():
                complete_signals_in_difs.add(s1)
                complete_signals_in_difs.add(s2)
        else: 
            if verbose:
                print("### CONSTRAINT SOLVED (no difs)")
            number_solved += 1
        index += 1

    #print("Number of completely solved constraints: " + str(number_solved))
    #print("Maximum number of missing monomials added by a constraint: " + str(max_difs))


    #print("#################### FINISHED PHASE 1 ####################")
        
    #######              Clustering of the difs obtained to reduce the problem considered in phase 2

    clusters = generate_clusters(complete_signals_in_difs, remaining_difs)
    maxSize = 0
    for (c, list_mons) in clusters.items():
        if len(list_mons) > maxSize:
            maxSize = len(list_mons)
    #print("Maximum size of the clusters of constraints that need to be solved: " + str(maxSize))
    #print("Number of clusters: "+ str(len(clusters)))

    #    #print(len(list_mons))
    #    #print(list_mons)
    #print("#################### FINISHED CLUSTERING ####################")

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
        signals.sort()
        naux, coefs, signals_aux = solver_acir_to_r1cs_phase2.complete_phase2_transformation(cons_sys, signals, int(args.n), verbose)
        if naux == -1:
            print("UNSAT: The number of auxiliar variables is not enough, try with more")
        else:
            if verbose:
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
            if not index in coefs_for_difs:
                coefs_for_difs[index] = {}
            
            for (s, coef) in coefs_index.items():    
                coefs_for_difs[index][s] = coef
        
        total_number_of_aux += naux

    #print("#################### FINISHED PHASE 2 ####################")
        

    
        
    #######               Rebuild the constraints
    constraints = build_constraints(choosen_AB, linear_part_constraints, auxiliar_signals, coefs_for_difs, n_signals)


    def apply_correspondence(constraint, renaming):
        new_A = {}
        new_B = {}
        new_C = {}
        
        for (s, coef) in constraint[0].items():
            if s not in renaming:
                new_s = s
            else:
                new_s = renaming[s]
            new_A[new_s] = coef
        for (s, coef) in constraint[1].items():
            if s not in renaming:
                new_s = s
            else:
                new_s = renaming[s]
            new_B[new_s] = coef
        for (s, coef) in constraint[2].items():
            if s not in renaming:
                new_s = s
            else:
                new_s = renaming[s]
            new_C[new_s] = coef
        
        return (new_A, new_B, new_C)


    def apply_renaming_signals(constraints, inputs, outputs, next_id_signal, signals):
        """
        Aplica un renombrado de señales:
        - outputs → primeras posiciones
        - inputs → siguientes posiciones
        - signals auxiliares → después
        """
        renaming = {}

        for s in signals:
            if s not in renaming:
                renaming[s] = next_id_signal
                next_id_signal += 1
        print("renaming:", renaming)
        for i, c in enumerate(constraints):
            constraints[i] = apply_correspondence(c, renaming)


    ##print("applying renaming: ", constraints, n_inputs, n_outputs, list(range(1, n_signals + len(auxiliar_signals)+1)))   
    
    #print(constraints)
    #print("Applying renaming of signals...")
    #print(n_inputs)
    #print(n_outputs)
    #print(n_signals)
    apply_renaming_signals(constraints, n_inputs, n_outputs, next_signal, list(range(n_signals + 1, n_signals + len(auxiliar_signals)+1)))
    print("renaming applied", constraints)
    map_result = {}
    map_result["prime"] = str(prime)
    map_result["constraints"] = constraints
    map_result["n_inputs"] = len(n_inputs)
    map_result["n_outputs"] = len(n_outputs)
    map_result["n_signals"] = n_signals + len(auxiliar_signals)
    map_result["num_auxiliars"] = len(auxiliar_signals)
    ##print(constraints)
    #print("Total number of auxiliar signals added: ", total_number_of_aux)
    #print("#################### FINISHED REBUILDING ####################")
    return map_result

def apply_correspondence_r1cs(constraint, renaming):
    new_A = {}
    new_B = {}
    new_C = {}
    
    for (s, coef) in constraint[0].items():
        if s in renaming:
            new_s = renaming[s]
        else:
            new_s = len(renaming)
            renaming[s] = new_s
        new_A[new_s] = coef
    for (s, coef) in constraint[1].items():
        if s in renaming:
            new_s = renaming[s]
        else:
            new_s = len(renaming)
            renaming[s] = new_s
        new_B[new_s] = coef
    for (s, coef) in constraint[2].items():
        if s in renaming:
            new_s = renaming[s]
        else:
            new_s = len(renaming)
            renaming[s] = new_s
        new_C[new_s] = coef
    return (new_A, new_B, new_C)

def apply_renaming_r1cs(constraints, mapping):
        """
        Aplica un renombrado de señales:
        - outputs → primeras posiciones
        - inputs → siguientes posiciones
        - signals auxiliares → después
        """
        new_constraints = []
        for i, c in enumerate(constraints):
            ##print("Applying renaming to constraint ", i)
            ##print("Before: ", c)
            new_constraints.append(apply_correspondence_r1cs(c, mapping))
            ##print("After: ", constraints[i])
        return new_constraints, mapping
    
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
    
cont = 0
whole_circuit = {}
whole_circuit["prime"] = str(prime)
whole_circuit["constraints"] = []
whole_circuit["n_inputs"] = len(data["inputs"])
whole_circuit["n_outputs"] = len(data["outputs"])
whole_circuit["n_signals"] = data["number_of_signals"]
new_structure = copy.deepcopy(structure)
new_structure["nodes"] = []
num_constraints = 0
next_signal = (data["number_of_signals"]) + 2
print("Initial next signal:", next_signal)
#print("the whole circuit is: ", whole_circuit)
for cluster_id in structure["nodes"]:
    new_node = copy.deepcopy(cluster_id)
    new_node["constraints"] = []
    new_node["signals"] = []
    for i in new_node["input_signals"]:
      new_node["signals"].append(i)
    for i in new_node["output_signals"]:
      new_node["signals"].append(i)
    circuit = {}
    signals = set()
    circuit["constraints"] = []
    #print("Processing cluster ", cluster_id)
    for i in cluster_id["constraints"]:
        for l in data["constraints"][i]["linear"]:
            signals.add(l["witness"])
        for m in data["constraints"][i]["mul"]:
            signals.add(m["witness1"])
            signals.add(m["witness2"])
        circuit["constraints"].append(data["constraints"][i])
    circuit["inputs"] = cluster_id["input_signals"]
    circuit["outputs"] = cluster_id["output_signals"]
    circuit["number_of_signals"] = len(signals)
    circuit["next_id_signal"] = next_signal

    #print("mini Circuit:", circuit)
    cluster_result = parse_cluster(circuit, prime)
    next_signal += cluster_result["num_auxiliars"]
    print("Next signal after processing cluster:", next_signal)
    #print("Cluster result:", cluster_result)

    for i in range(len(cluster_result["constraints"])):
        new_node["constraints"].append(i + num_constraints)
    num_constraints += len(cluster_result["constraints"])
    mapping = {}
    num_outputs = 0
    #for m in data["outputs"]:
    #    mapping[m] = num_outputs
    #    num_outputs += 1
    #num_inputs = 0
    #for m in data["inputs"]:
    #    mapping[m] = num_outputs + num_inputs
    #    num_inputs += 1
    #print("inputs y outputs", mapping)
    new_node["signals"] = []
    for c in cluster_result["constraints"]:
        #print("----------------------------------")
        print("Constraint to process:", c)
        #print("----------------------------------")
        for (s, coef) in c[0].items():
             if s not in new_node["signals"]:
        #         mapping[s] = next_signal
                 new_node["signals"].append(s)
        #         next_signal += 1
        print("signals in the new node so far:", new_node["signals"])
        for (s, coef) in c[1].items():
             if s not in new_node["signals"]:
        #         mapping[s] = next_signal
                 new_node["signals"].append(s)
        #         next_signal += 1
        print("signals in the new node so far:", new_node["signals"])
        for (s, coef) in c[2].items():
             if s not in new_node["signals"]:
        #         mapping[s] = next_signal
                 new_node["signals"].append(s)
        #         next_signal += 1
        print("signals in the new node so far:", new_node["signals"])
        #print("Mapping so far:", mapping)
        #print("Number of signals so far:", next_signal-1)
        #print("signals in the cluster:", signals)
    ##print("before renaming:", cluster_result["constraints"])
    print("signals in the new node:", new_node["signals"])
    #print("after renaming:", cluster_result["constraints"])
    new_structure["nodes"].append(new_node)
    whole_circuit["constraints"].extend(cluster_result["constraints"])
    #print("cluster_result:", cluster_result)

mapping = {}
mapping[0] = 0
print(data["outputs"])
print(data["inputs"])
for s in data["outputs"]:
    mapping[s+1] = len(mapping)
for s in data["inputs"]:
    mapping[s+1] = len(mapping)
print("mapping after inputs and outputs:", mapping)
print("BEFORE RENAMING WHOLE CIRCUIT:", whole_circuit["constraints"])
whole_circuit["constraints"], mapping = apply_renaming_r1cs(whole_circuit["constraints"], mapping)
print("MAPPING OF INPUTS AND OUTPUTS:", mapping)
print("AFTER RENAMING WHOLE CIRCUIT:", whole_circuit["constraints"])
whole_circuit["n_signals"] = next_signal-1

json_object = json.dumps(whole_circuit, indent=4, sort_keys=True)   
#print("Total number of constraints before clustering: ", len(data["constraints"]))
#print("Total number of constraints after clustering: ", len(whole_circuit["constraints"]))
file = open(f"acir_r1cs.json", "w")
file.write(json_object)
file.close()

def apply_renaming_structure(structure, mapping):
    new_structure = copy.deepcopy(structure)
    for node in new_structure["nodes"]:
        new_signals = []
        for s in node["input_signals"]:
            s = s + 1
            if s in mapping:
                new_s = mapping[s]
            else:
                new_s = s 
            new_signals.append(new_s)
        node["input_signals"] = new_signals
        new_signals = []
        for s in node["output_signals"]:
            s = s + 1
            if s in mapping:
                new_s = mapping[s]
            else:
                new_s = s + 1
            new_signals.append(new_s)
        node["output_signals"] = new_signals
        new_signals = []
        print("renaming signals for node:", node["signals"])
        print("using mapping:", mapping)
        for s in node["signals"]:
            print("signal to rename:", s)
            if s in mapping:
                new_s = mapping[s]
            else:
                new_s = s
            new_signals.append(new_s)
        node["signals"] = new_signals
        print("renamed signals:", node["signals"])
    return new_structure
print("before:", new_structure)
new_structure = apply_renaming_structure(new_structure, mapping)
print("after:", new_structure)
json_object = json.dumps(new_structure, indent=4, sort_keys=True)   
#print("Total number of constraints before clustering: ", len(data["constraints"]))
#print("Total number of constraints after clustering: ", len(whole_circuit["constraints"]))
file = open(f"new_structure.json", "w")
file.write(json_object)
file.close()
    

