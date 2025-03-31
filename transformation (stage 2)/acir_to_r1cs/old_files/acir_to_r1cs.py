#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar 17 12:33:56 2025

@author: clara
"""


def generate_problem_r1cs_transformation(file, constraints, nsignals, naux):
    declare_aux(file, nsignals, naux)
    declare_coef(file, naux, len(constraints))
    declare_is_needed(file, naux)
    write_all_constraints(file, constraints, nsignals, naux)
    calculate_needed(file, nsignals, naux)
    
    file.write('(check-sat)')
    file.write('(get-model)')



def declare_aux(file, nsignals, naux):
    for k in range(naux): 
        for i in range(nsignals):
            coef_a_i = generate_aux_name(k, True, i)
            write_declare(file, coef_a_i, "Int")
            # WE ADD THESE LIMITS BECAUSE IF NOT IT TIMEOUTS EVEN IN SIMPLE CASES
            write_assert(file, binary_operation("<=", coef_a_i, "3"))
            write_assert(file, binary_operation(">=", coef_a_i, "0"))

            coef_b_i = generate_aux_name(k, False, i)
            write_declare(file, coef_b_i, "Int")
            # WE ADD THESE LIMITS BECAUSE IF NOT IT TIMEOUTS EVEN IN SIMPLE CASES
            write_assert(file, binary_operation("<=", coef_b_i, "3"))
            write_assert(file, binary_operation(">=", coef_b_i, "0"))
    
def declare_coef(file, naux, ncons):
    for k in range(naux): 
        for i in range(ncons):
            coef_cons_i = generate_coef_name(k, i)
            write_declare(file, coef_cons_i, "Int")   
            #write_assert(file, binary_operation("<=", coef_cons_i, "3"))
            #write_assert(file, binary_operation(">=", coef_cons_i, "0"))
    


def declare_is_needed(file, naux):
    for k in range(naux): 
        write_declare(file, "is_needed_" + str(k), "Int")   
    write_declare(file, "total_needed", "Int")


def write_all_constraints(file, constraints, nsignals, naux):
    index = 0
    for coefs in constraints:
        write_constraint_conditions(file, coefs, index, nsignals, naux)
        index += 1
    

def write_constraint_conditions(file, coefs, icons, nsignals, naux):
    for i in range(nsignals):
        for j in range (i, nsignals):
            if (i, j) in coefs:
                coef = coefs[(i, j)]
            else:
                coef = 0
            sum_aux = "0"
            for k in range(naux):
                # Indicate the values of the signal_i in the A and B part of the k aux variable
                coef_a_i = generate_aux_name(k, True, i)
                coef_b_j = generate_aux_name(k, False, j)
                mul = binary_operation("*", coef_a_i, coef_b_j)
                # coef k indicates the coef of the k aux variable in this constraint
                mul = binary_operation("*", mul, generate_coef_name(k, icons))
                sum_aux = binary_operation("+" , sum_aux, mul)
                if i != j:
                    coef_a_j = generate_aux_name(k, True, j)
                    coef_b_i = generate_aux_name(k, False, i)
                    mul = binary_operation("*", coef_a_j, coef_b_i)
                    mul = binary_operation("*", mul, generate_coef_name(k, icons))
                    sum_aux = binary_operation("+" , sum_aux, mul)
            eq_coef = binary_operation("=", sum_aux, str(coef))
            write_assert(file, eq_coef)



def calculate_needed(file, nsignals, naux):
    sum_needed = "0"
    for k in range(naux):
        isNeeded = "false"
        for i in range(nsignals):
            name = generate_aux_name(k, True, i)
            not_zero = "(not " + binary_operation("=", name, "0") + ")"
            isNeeded = binary_operation("or", isNeeded, not_zero)
        ite_needed = generate_ite(isNeeded, "1", "0")
        write_assert(file, binary_operation("=","is_needed_" + str(k), ite_needed))
        sum_needed = binary_operation("+", sum_needed, "is_needed_" + str(k))
    write_assert(file, binary_operation("=", "total_needed", sum_needed))
    file.write('(minimize total_needed) \n')



def generate_coef_name(iaux, icons):
    return "aux_" + str(iaux) + "_coef_" + str(icons) 

def generate_aux_name(iaux, isA, index):
    if isA:
        return "aux_" + str(iaux) + "_A_" + str(index)
    else:
        return "aux_" + str(iaux) + "_B_" + str(index)


def binary_operation(op, val_1, val_2):
    return('('+ op +' '+ val_1+ ' '+ val_2 + ')')
    
def generate_ite(con, val_1, val_2):
    return '(ite ' + con + ' '+ val_1 + ' ' + val_2 + ')'
        
    
def write_assert(file, value):
    file.write('(assert '+ value+ ')\n')
    
def write_declare(file, var, typevar):
    file.write('(declare-const '+ var+ ' '+ typevar+ ')\n') 
