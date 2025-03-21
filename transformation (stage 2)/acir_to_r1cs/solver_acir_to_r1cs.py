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

def generate_problem_r1cs_transformation(constraints, nsignals, naux):
    s = Optimize()
    
    write_all_constraints(s, constraints, nsignals, naux)
    calculate_needed(s, nsignals, naux)
    
    # To rebuild the solution
    
    if(s.check() == sat): 
#        print(s.model())
        m = s.model()
        #print(m[z3.Int('needed_variables')])
        coefs = [] # One coef for each variable and constraint
        used_signals = []
        total_aux = m[z3.Int("total_needed")]
        
        
        for s in range(naux):
            if m[z3.Int('is_needed_' + str(s))] == 1:
            
                # We use the signal, study the coef and signals that appear in A and B
                # Study the coefs for each one of the constraints
                coefs_cons = []
                for cindex in range(len(constraints)):
                    name_coef = generate_coef_name(s, cindex)
                    coef = m[z3.Int(name_coef)].as_long()
                    coefs_cons.append(coef)
                coefs.append(coefs_cons)
                                
                # Study the signals that are in A
                signals_A = []
                for i in range(nsignals):
                    name_aux = generate_aux_name(s, True, i)
                    aux = m[z3.Bool(name_aux)]
                    if aux: 
                        signals_A.append(i)
                
                # Study the signals that are in B
                signals_B = []
                for i in range(nsignals):
                    name_aux = generate_aux_name(s, False, i)
                    aux = m[z3.Bool(name_aux)]
                    if aux: 
                        signals_B.append(i)
                
                used_signals.append((signals_A, signals_B))
                 
        return total_aux, coefs, used_signals
    else:
        return -1, [], []



# =============================================================================
# def declare_aux(file, nsignals, naux):
#     for k in range(naux): 
#         for i in range(nsignals):
#             coef_a_i = generate_aux_name(k, True, i)
#             write_declare(file, coef_a_i, "Bool")
# 
#             coef_b_i = generate_aux_name(k, False, i)
#             write_declare(file, coef_b_i, "Bool")
# 
#     
# def declare_coef(file, naux, ncons):
#     for k in range(naux): 
#         for i in range(ncons):
#             coef_cons_i = generate_coef_name(k, i)
#             write_declare(file, coef_cons_i, "Int")   
#             #write_assert(file, binary_operation("<=", coef_cons_i, "3"))
#             #write_assert(file, binary_operation(">=", coef_cons_i, "0"))
#     
# 
# 
# def declare_is_needed(file, naux):
#     for k in range(naux): 
#         write_declare(file, "is_needed_" + str(k), "Int")   
#     write_declare(file, "total_needed", "Int")
# 
# =============================================================================

def write_all_constraints(solver, constraints, nsignals, naux):
    index = 0
    for coefs in constraints:
        write_constraint_conditions(solver, coefs, index, nsignals, naux)
        index += 1
    

def write_constraint_conditions(solver, coefs, icons, nsignals, naux):
    for i in range(nsignals):
        for j in range (i, nsignals):
            if (i, j) in coefs:
                coef = coefs[(i, j)]
            else:
                coef = 0
            sum_aux = 0
            for k in range(naux):
                # Indicate the values of the signal_i in the A and B part of the k aux variable
                coef_a_i = Bool(generate_aux_name(k, True, i))
                coef_b_j = Bool(generate_aux_name(k, False, j))
                and_a_b = And(coef_a_i, coef_b_j)
                # coef k indicates the coef of the k aux variable in this constraint
                mul = If(and_a_b, Int(generate_coef_name(k, icons)), 0)
                sum_aux = sum_aux + mul
                if i != j:
                    coef_a_j = Bool(generate_aux_name(k, True, j))
                    coef_b_i = Bool(generate_aux_name(k, False, i))
                    and_a_b = And(coef_a_j, coef_b_i)
                    # coef k indicates the coef of the k aux variable in this constraint
                    mul = If(and_a_b, Int(generate_coef_name(k, icons)), 0)
                    sum_aux = sum_aux + mul
            eq_coef = sum_aux == coef
            solver.add(eq_coef)



def calculate_needed(solver, nsignals, naux):
    sum_needed = 0
    for k in range(naux):
        isNeeded = False
        for i in range(nsignals):
            name = Bool(generate_aux_name(k, True, i))
            isNeeded = Or(isNeeded, name)
        ite_needed = If(isNeeded, 1, 0)
        solver.add(Int("is_needed_" + str(k)) == ite_needed)
        sum_needed = sum_needed + Int("is_needed_" + str(k))
    solver.add(Int("total_needed") == sum_needed)
    solver.minimize(Int('total_needed'))


def calculate_needed_2(solver, nsignals, naux):
    sum_needed = 0
    for k in range(naux):
        isNeeded = False
        for i in range(nsignals):
            name = Bool(generate_aux_name(k, True, i))
            isNeeded = Or(isNeeded, name)
        solver.add(Bool("is_needed_" + str(k)), isNeeded)
        ite_needed = If(Bool("is_needed_" + str(k)), 1, 0)
        sum_needed = sum_needed + ite_needed
        # To reduce the number of symmetries?
        #if k > 0:
        	#write_assert(file, "(=> (not is_needed_" + str(k-1) + ") (not is_needed_" + str(k) + "))")
    solver.add(Int("total_needed") == sum_needed)
    solver.minimize(Int('total_needed'))


def generate_coef_name(iaux, icons):
    return "aux_" + str(iaux) + "_coef_" + str(icons) 

def generate_aux_name(iaux, isA, index):
    if isA:
        return "aux_" + str(iaux) + "_A_" + str(index)
    else:
        return "aux_" + str(iaux) + "_B_" + str(index)

