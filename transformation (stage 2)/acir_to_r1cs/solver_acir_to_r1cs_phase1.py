#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar 17 18:00:58 2025

@author: clara
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar 17 12:33:56 2025

@author: clara
"""


from z3 import *
from z3 import Optimize

def compute_cluster(signal_to_cluster_rep, s1):
    c_s1 = signal_to_cluster_rep[s1]
    if c_s1 != s1:
        return compute_cluster(signal_to_cluster_rep, c_s1)
    else: 
        return s1

def compute_clusters_independent_monomials(constraint_coefficients, signals):
    signals_to_clusters = {}
    for s in signals:
        signals_to_clusters[s] = s
    for (s1, s2) in constraint_coefficients:
        rep_s1 = compute_cluster(signals_to_clusters, s1)
        rep_s2 = compute_cluster(signals_to_clusters, s2)
        if rep_s1 < rep_s2:
            signals_to_clusters[rep_s2] = rep_s1
            signals_to_clusters[s2] = rep_s1
        else:
            signals_to_clusters[rep_s1] = rep_s2
            signals_to_clusters[s1] = rep_s2

    clusters_to_monomials = {}
    clusters_to_signals = {}
    are_all_size_one = True

    for (s1, s2) in constraint_coefficients:
        rep_s1 = compute_cluster(signals_to_clusters, s1)
        if not rep_s1 in clusters_to_monomials:    
            clusters_to_monomials[rep_s1] = {}
            clusters_to_signals[rep_s1] = set()
        else: 
            are_all_size_one = False
        clusters_to_monomials[rep_s1][(s1, s2)] = constraint_coefficients[(s1, s2)]
        clusters_to_signals[rep_s1].add(s1)
        clusters_to_signals[rep_s1].add(s2)
    return clusters_to_monomials, clusters_to_signals, are_all_size_one
            


def solve_case_all_clusters_size_one(clusters_monomials):
    for cluster, monomials in clusters_monomials.items():
            # We take the monomial of the cluster
            for (s1, s2), coef in monomials.items():
                solution_A = {s1: coef}
                solution_B = {s2: 1}
                solution_difs = {}
                return solution_A, solution_B, solution_difs, cluster

def complete_phase1_transformation(constraint_coefficients, signals, verbose):
    
    # Case empty constraint coefficients, return A = {}, B = {}, difs = {}
    if len(constraint_coefficients) == 0:
        return {}, {}, {}
    
    total_number_monomials = len(constraint_coefficients)
    new_clusters_monomials, new_clusters_signals, are_all_size_one = compute_clusters_independent_monomials(constraint_coefficients, signals)
    best_solution = total_number_monomials
    
                
    
    solution_A = {}
    solution_B = {}
    solution_difs = {}    
    
    
    # Case all of the clusters have size 1 --> we can return any of them
    if are_all_size_one:
        # We solve the first cluster (with only one monomial)
        if verbose:
            print("##Case all clusters have size 1 -> considering first one")
        solution_A, solution_B, solution_difs, solution_cluster = solve_case_all_clusters_size_one(new_clusters_monomials)
    else:
        for cluster in new_clusters_monomials:
            monomials = new_clusters_monomials[cluster]
            signals = new_clusters_signals[cluster]
        
            # No need to consider the ones of size 1 -> we know that these cases are not better than solving a cluster of bigger size  
            # Case all 1 is previously studied, we know that al least one of them has size >1            
            if len(monomials) > 1:
                if verbose:
                    print("##Considering cluster: " + str(monomials))
                aux_A, aux_B, aux_difs = generate_problem_r1cs_transformation(monomials, list(signals))
                
                # Actual number  of difs generated: total number of monomials - monomials of the cluster (the ones that we have not solved) + the difs
                number_remaining_difs = total_number_monomials - len(monomials) + len(aux_difs)
                if verbose:
                    print("##Best solution: difs->" + str(aux_difs) + " total ->" + str(number_remaining_difs))
                      
                if number_remaining_difs < best_solution:
                    best_solution = number_remaining_difs
                    solution_A = aux_A
                    solution_B = aux_B
                    solution_difs = aux_difs
                    solution_cluster = cluster
    
    # Add the clusters that we have not solved in the difs
    for cluster in new_clusters_monomials:
        if cluster != solution_cluster:
            solution_difs.update(new_clusters_monomials[cluster])
    return solution_A, solution_B, solution_difs

        

def generate_problem_r1cs_transformation(constraint_coefficients, signals):
    s = Optimize()
    
    write_constraint(s, constraint_coefficients, signals)
    minimize_different(s, signals)
    
    # To rebuild the solution
    if(s.check() == sat): 
        #print(s.model())
        m = s.model()
        #print(m[z3.Int('needed_variables')])
        coefs_A = {}
        coefs_B = {}
        difs = {}
        
        
        for s in signals:
            in_A = m[Int(generate_coef_i(True, s))].as_long()
            if in_A != 0:
                coefs_A[s] = in_A
            in_B =  m[Int(generate_coef_i(False, s))].as_long()
            if in_B != 0:
                coefs_B[s] =  in_B
        index = 0
        for i in signals:
            for j in signals[index:]:
                dif = m[Int(generate_diff_ij(i, j))].as_long()
                if  dif != 0:
                    difs[i,j] = dif
            index += 1
        
            
        return coefs_A, coefs_B, difs
    else:
        return {}, {}, {}


def write_constraint(s, constraint_coefficients, signals):
   index = 0
   for i in signals:
       for j in signals[index:]:
           coef_to_get = 0
           if (i,j) in constraint_coefficients:
              coef_to_get = constraint_coefficients[(i,j)]
                      
           coef_A_i = Int(generate_coef_i(True, i))
           coef_B_j = Int(generate_coef_i(False, j))     
           actual_coef = coef_A_i * coef_B_j
           
           if i != j:
               coef_A_j = Int(generate_coef_i(True, j))
               coef_B_i = Int(generate_coef_i(False, i))     
               actual_coef += coef_A_j * coef_B_i
           
           dif = Int(generate_diff_ij(i, j))
           s.add(dif == coef_to_get - actual_coef)
       index += 1
   # To limit the A coefficients
   for i in signals:
       coef_A_i = Int(generate_coef_i(True, i))
       s.add(coef_A_i <= 1)
       s.add(coef_A_i >= -1)


        
       
       

def minimize_different(s, signals):
   index = 0
   for i in signals:
       for j in signals[index:]:
           dif = Int(generate_diff_ij(i, j))
           s.add_soft(dif == 0)
       index += 1    


def generate_diff_ij(sig1, sig2):
    return "diff_" + str(sig1) + "_" + str(sig2)  

def generate_coef_i(isA, index):
    if isA:
        return "coeff_A_" + str(index)
    else:
        return "coeff_B_" + str(index)

