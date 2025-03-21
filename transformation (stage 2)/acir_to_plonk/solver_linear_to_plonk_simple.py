#!/usr/bin/env python3
# -*- coding: utf-8 -*-


from z3 import *

def generate_problem_plonk_transformation(constraints, nsignals, naux):
    s = Optimize()
    
    restrict_number_additions_aux(s, nsignals, naux)
    restrict_size_coefs(s, len(constraints), nsignals, naux)
    write_all_constraints(s, constraints, nsignals, naux)
    minimize_needed(s, nsignals, naux)
    
    #s.constraints().print()
    
    # To rebuild the solution
    
    if(s.check() == sat): 
        #print(s.model())
        m = s.model()
        #print(m[z3.Int('needed_variables')])
        
        coefs_constraints = [] # One coef for each variable and constraint
        used_signals = []
        total_aux = m[z3.Int("total_needed")]
        
        new_signals_coefs = {}
        index = nsignals
        for s in range(naux):
            if (m[z3.Bool("is_needed_" + str(s))]):
                new_signals_coefs[s] = index
                index += 1
                
        for s in range(naux):
            if (m[z3.Bool("is_needed_" + str(s))]):
                print("Signal aux_"+ str(s) + "is defined as:")
                involved = ""
                signal_def = []
                for s1 in range(nsignals):
                    if (m[z3.Bool(generate_aux_name(s, s1, False))]):
                        involved += " + s_"+str(s1)
                        signal_def.append(s1)
                #for s1 in range(naux):
                #    if (m[z3.Bool(generate_aux_name(s, s1, True))]):
                #       involved += " + aux_"+str(s1)
                #       signal_def.append(new_signals_coefs[s1])
                used_signals.append(signal_def)

                print(involved)
        
        for c in range(len(constraints)):
            coefs = ""
            coefs_c = []
            for s in range(nsignals):
                if m[z3.Int(generate_coef_name(c, s, False))] == 0:
                    pass
                else:
                    coefs += " + " + str(m[z3.Int(generate_coef_name(c, s, False))]) + "* s_" + str(s) 
                    coefs_c.append((s, m[z3.Int(generate_coef_name(c, s, False))].as_long()))
            for s in range(naux):
                if m[z3.Int(generate_coef_name(c, s, True))] == 0:
                    pass 
                else:
                    coefs += " + " + str(m[z3.Int(generate_coef_name(c, s, True))]) + "* aux_" + str(s)  
                    s_index = new_signals_coefs[s]
                    coefs_c.append((s_index, m[z3.Int(generate_coef_name(c, s, True))].as_long()))
            
            if -1 in constraints[c]:
                coefs += "+ " + constraints[c][-1]
                coefs_c.append((-1, constraints[c][-1]))
            
            coefs_constraints.append(coefs_c)

            print("Constraint " + str(c) + ":")
            print(coefs)
        return total_aux, used_signals, coefs_constraints
    else: 
        return -1, [], []
        


def restrict_size_coefs(solver, nconstraints, nsignals, naux):
    for c in range(nconstraints):
        for s in range(nsignals):
            name = Int(generate_coef_name(c, s, False))
            solver.add(name >= -1)
            solver.add(name <= 1)
        for s in range(naux):
            name = Int(generate_coef_name(c, s, True))
            solver.add(name >= -1)
            solver.add(name <= 1)

def restrict_number_additions_aux(solver, nsignals, naux):
    for i in range(naux):
        # If we can only use the signals
        sum_needed = 0
        for j in range(nsignals):
    	    var = Bool(generate_aux_name(i, j, False))
    	    sum_needed = sum_needed + If(var, 1, 0)
    	# If we can use the signals and the previous aux
        #for j in range(i):
        #    var = Bool(generate_aux_name(i, j, True))
        #    sum_needed = sum_needed + If(var, 1, 0)
    	
        condition_only_two = sum_needed <= 2
        solver.add(condition_only_two)


def minimize_needed(solver, nsignals, naux):
    total_needed = 0
    for i in range(naux):
    	# If we can only use the signals
        is_needed = False
        for j in range(nsignals):
            var = Bool(generate_aux_name(i, j, False))
            is_needed = Or(is_needed, var)
    	# If we can use the signals and the previous aux
        #for j in range(i):
    	#    var = Bool(generate_aux_name(i, j, True))
    	#    is_needed = Or(is_needed, var)
    	
        solver.add(Bool("is_needed_" + str(i)) == is_needed)
        total_needed = total_needed + If(Bool("is_needed_" + str(i)), 1, 0)
    
    solver.add(Int("total_needed") == total_needed)
    solver.minimize(Int("total_needed"))

    	
    	    
def write_all_constraints(solver, constraints, nsignals, naux):
    index = 0
    for coefs in constraints:
        write_constraint_conditions(solver, coefs, index, nsignals, naux)
        index += 1
    

def write_constraint_conditions(solver, coefs, icons, nsignals, naux):
    
    # Check that the sum is the total
    for i in range(nsignals):
        
        if i in coefs:
            coef = coefs[i]
        else:
            coef = 0
        
        # We need sum_aux to be equal to the coef
        sum_aux = 0
            
        # We add the signal if we want to use it
        coef_signal = Int(generate_coef_name(icons, i, False))
        sum_aux = sum_aux + coef_signal        
        
        # We add the aux signals    
        for k in range(naux):
            
            # Compute the coef that they add
            coef_signal = Int(generate_coef_name(icons, k, True))
            
            # Check hot many times it adds the signal
            n_adds = compute_nadds_signal(k, i) 
            sum_aux = sum_aux + coef_signal* n_adds
    
        # The sum of the signal is the total
        solver.add(sum_aux == coef)
    
    
    ncoefs = 0
    # Check that the number of coefs is less eq than 3
    for i in range(nsignals):
        coef_signal = Int(generate_coef_name(icons, i, False))
        ncoefs = ncoefs + If(coef_signal == 0, 0, 1)
    for i in range(naux):
        coef_signal = Int(generate_coef_name(icons, i, True))
        ncoefs = ncoefs + If(coef_signal == 0, 0, 1)
    # The number of coefs is at most 3
    solver.add(ncoefs <= 3)




def compute_nadds_signal(index_aux, index_signal):
    
    nadds = 0
    
    name_aux_signal = Bool(generate_aux_name(index_aux, index_signal, False))
    nadds = nadds + If(name_aux_signal, 1, 0)
    
    # If we can use the previous aux when generating an aux signal
    #for i in range(index_aux):
    #    name_aux_i = Bool(generate_aux_name(index_aux, i, True))
    #    nadds_i = compute_nadds_signal(i, index_signal)
    #    nadds = nadds +  If(name_aux_i, nadds_i, 0)
    
    return nadds





def generate_aux_name(i, j, is_new):
    if is_new:
    	return "aux_" + str(i) + "_aux_" + str(j)  
    else:
        return "aux_" + str(i) + "_signal_" + str(j)  

def generate_coef_name(i, j, is_new):
    if is_new:
    	return "cons_" + str(i) + "_coef_aux_" + str(j)  
    else:
        return "cons_" + str(i) + "_coef_signal_" + str(j) 
    
    
