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

def generate_problem_r1cs_transformation(constraint_coefficients, signals):
    s = Optimize()
    
    write_constraint(s, constraint_coefficients, signals)
    minimize_different(s, signals)
    
    # To rebuild the solution
    print(s)
    if(s.check() == sat): 
        #print(s.model())
        print("aqui")
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

