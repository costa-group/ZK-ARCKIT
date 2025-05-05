#!/usr/bin/env python3
# -*- coding: utf-8 -*-


from z3 import *

def extract_plonk_constraints(oconstraints):
    pcons = []
    constraints = []
    for c in oconstraints:
        #print(c)
        n = len(c)
        if -1 in c:
            n -= 1
        if n <= 3:
            pcons.append(c)
        else:
            constraints.append(c)
    return pcons, constraints

def generate_problem_plonk_transformation(oconstraints, nsignals, naux,maxmul):
    pcons, constraints = extract_plonk_constraints(oconstraints)
    #s = Optimize()
    #s = Solver()
    s = SolverFor("QF_LIA")
    #ba,bc,bm,cm = create_matrix(s,len(constraints),nsignals, naux)
    #print(nvar)
    ba, bc, cm , const = create_matrix(s,len(constraints),nsignals, naux)
    write_all_constraints(s, pcons, constraints, nsignals, naux,bc,cm,const,maxmul)
    nvar = get_times(constraints)
    limit_times(s,cm,nvar)
    #minimize_needed(s, bc)

    #print(s.to_smt2())
    #exit(0)
    #s.constraints().print()
    
    # To rebuild the solution
    best_bound = -1
    best_solution = []
    left = 0
    right = naux
    while left <= right:
        i = (right + left +1) // 2
        print("Trying with:", left, i, right)
        if i < naux:
            s.push()
            s.add(Not(bc[len(constraints)+i]))
            s.add(Not(ba[i]))
        res = s.check()
        if res == sat:
            #print(s.model())
            #c = 0
            #for b in ba:
                #print(c+1,s.model().eval(b))
                #c += 1
            bound_i= 0
            solution_i = []
            for b in bc:
                #print(best_bound+1,s.model().eval(b))
                if not s.model().eval(b):
                    break
                else:
                    isolution = []
                    for i in range(nsignals+naux):
                        if not s.model().eval(cm[bound_i][i]) == 0:
                            isolution.append((i,s.model().eval(cm[bound_i][i])))
                    if not s.model().eval(const[bound_i]) == 0:
                            isolution.append((-1,s.model().eval(const[bound_i])))                        
                    solution_i.append(isolution)
                    bound_i += 1
            #print("solution:",solution_i)
            #print(pcons)
            best_bound = bound_i
            best_solution = solution_i
            #print("Solution found:", best_bound)
            #if i < right:
            #    s.pop()
            assert(best_bound >= len(constraints))
            right = best_bound - len(constraints) - 1
        elif res == unsat:
            if i < right:
                s.pop()
            left = i + 1
        else:
            right -= 1
    pcons_solution = []
    for c in pcons:
        pc = []
        for x, v in c.items():
            pc.append((x,int(v)))
        pcons_solution.append(pc)
    best_solution = pcons_solution + best_solution
    return best_bound-len(constraints), best_solution
        
def used_aux(i):
    return "used_aux_"+str(i)
def used_cons(i):
    return "used_cons_"+str(i)
def used_coef(i,j):
    return "used_coef_"+str(i)+"_"+str(j)
def value_coef(i,j):
    return "value_coef_"+str(i)+"_"+str(j)
def multiplier(i,j):
    return "multiplier_"+str(i)+"_"+str(j)
def pmultiplier(i,j):
    return "pmultiplier_"+str(i)+"_"+str(j)
def constant(i):
        return "const_"+str(i)

def addsum(a):
    if len(a) == 0:
        return 0
    else:
        asum = a[0]
        for i in range(1,len(a)):
            asum = asum + a[i]
        return asum
def addall(a):
    if len(a) == 0:
        return False
    else:
        aand = a[0]
        for i in range(1,len(a)):
            aand = And(asum,a[i])
        return aand
def addexists(a):
    if len(a) == 0:
        return True
    else:
        aor = a[0]
        for i in range(1,len(a)):
            aor = Or(asum,a[i])
        return aor

def get_times(cons):
    times = {}
    for c in cons:
        for v in c:
            if v >= 0:
                if v not in times:
                    times[v] = 1
                else:
                    times[v] += 1
    return times
        
def create_matrix(s,nconstraints,nsignals, naux):
    bcons = []
    #bcoef = []
    vcoef = []
    constants = []
    for i in range(nconstraints+naux):
        bcons.append(Bool(used_cons(i)))
    for i in range(nconstraints+naux):
        constants.append(Int(constant(i)))
        #bcoefi = []
        vcoefi = []
        for j in range(nsignals+naux):
            #bcoefi.append(Bool(used_coef(i,j)))
            vcoefi.append(Int(value_coef(i,j)))
            #s.add(vcoefi[j] >= -(nconstraints+naux))
            #s.add(vcoefi[j] <= nconstraints+naux)
            #s.add(vcoefi[j] >= -naux)
            #s.add(vcoefi[j] <= naux)
        #bcoef.append(bcoefi)
        vcoef.append(vcoefi)
    for i in range(nconstraints+naux-1):
        s.add(Or(bcons[i],Not(bcons[i+1])))
    for i in range(nconstraints+naux):
        s.add(Or(bcons[i],constants[i] == 0))
        exact3 = []
        for j in range(nsignals+naux):
            s.add(Or(bcons[i],vcoef[i][j] == 0))
            #s.add(Or(bcoef[i][j],vcoef[i][j] == 0))            
            #s.add(Or(Not(bcoef[i][j]),Not(vcoef[i][j] == 0)))            
            exact3.append(If(Not(vcoef[i][j] == 0),1,0))
        s.add(Or(Not(bcons[i]),addsum(exact3) == 3))
        atleast1 = []
        for j in range(nsignals,nsignals+naux):
            atleast1.append(If(Not(vcoef[i][j] == 0),1,0))
        s.add(Or(Not(bcons[i]),addsum(atleast1) >= 1))
    baux = []
    for i in range(naux):
        baux.append(Bool(used_aux(i)))
        for  j in range(i):
            s.add(vcoef[j][nsignals+i] == 0)
        for  j in range(i+1,len(vcoef)):
            s.add(vcoef[j][nsignals+i] >= 0)
            s.add(Or(baux[i],vcoef[j][nsignals+i] == 0))
        s.add(Or(Not(baux[i]),And(vcoef[i][nsignals+i]==-1,constants[i] == 0)))
    for i in range(len(baux)-1):
        s.add(Or(baux[i],Not(baux[i+1])))
    l = list(range(nsignals,nsignals+naux))+list(range(nsignals))
    for i in range(len(bcons)-1):
        o = Not(bcons[i])
        for j in range(nsignals,nsignals+naux):
            o = Or(o,vcoef[i][j] == -1)
        g = ordered_i(0,l,vcoef[i],vcoef[i+1])
        s.add(Or(o,g))
    return baux,bcons,vcoef, constants

def ordered_i(i,l,vcoeff,vcoeff1):
    if i == len(l)-1:
        return Or(And(Not(vcoeff[l[i]] == 0),vcoeff1[l[i]] == 0),vcoeff[l[i]] > vcoeff1[l[i]])
    else:
        gr = ordered_i(i+1,l,vcoeff,vcoeff1)
        return Or(And(Not(vcoeff[l[i]] == 0),vcoeff1[l[i]] == 0),vcoeff[l[i]] > vcoeff1[l[i]],And(vcoeff[l[i]] == vcoeff1[l[i]],gr))

def limit_times(s,coefs,times):
    for v in times:
        svc = []
        for c in coefs:
            svc.append(If(c[v] == 0, 0, 1))
        s.add(addsum(svc) <= times[v]+1)
           
def minimize_needed(solver, bc):
    for b in bc:
        solver.add_soft(Not(b))    	
    	    
def write_all_constraints(solver, pcons, constraints, nsignals, naux,bc,cm,const,maxmul):
    index = 0
    for coefs in constraints:
        write_constraint_conditions(solver, pcons, coefs, index, nsignals, naux,bc,cm,const,maxmul)
        index += 1

def write_constraint_conditions(solver, pcons, coefs, icons, nsignals, naux,bc,cm,const,maxmul):
    
    # Check that the sum is the total
    multipliers = []
    for i in range(len(bc)):
        multipliers.append(Int(multiplier(icons,i)))
        solver.add(0 <= multipliers[i])
        solver.add(multipliers[i] <= maxmul)
        solver.add(Or(bc[i],multipliers[i] == 0))

    multiplied_const = []
    multiplied_coefs = []
    for i in range(len(bc)):
        cres = 0
        for v in range(1,maxmul+1):
            cres = If(multipliers[i] == v,v*const[i],cres)
        multiplied_const.append(cres)
        multiplied_coefs_i = []
        for j in range(nsignals+naux):
            res = 0
            for v in range(1,maxmul+1):
                res = If(multipliers[i] == v,v*cm[i][j],res)
            multiplied_coefs_i.append(res)
        multiplied_coefs.append( multiplied_coefs_i)

    pmultipliers = []
    for j in range(len(pcons)):
        pmultipliers.append(Int(pmultiplier(icons,j)))
        
    for i in range(nsignals):
        if i in coefs:
            coef = coefs[i]
        else:
            coef = 0

        lsum = []
        for j in range(len(bc)):
            lsum.append(multiplied_coefs[j][i])
        # The sum of the signal is the total
        for j in range(len(pcons)):
            if i in pcons[j]:
                lsum.append(pmultipliers[j]*pcons[j][i])            
        solver.add(addsum(lsum) == coef)

    if -1 in coefs:
        #print("Has constant",coefs[-1])
        lsum = []
        for j in range(len(bc)):
            lsum.append(multiplied_const[j])
        # The sum of the signal is the total
        for j in range(len(pcons)):
            if -1 in pcons[j]:
                lsum.append(pmultipliers[j]*pcons[j][-1])
        solver.add(addsum(lsum) == coefs[-1])
        
    
    for i in range(naux):
        lsum = []
        for j in range(len(bc)):
            lsum.append(multiplied_coefs[j][nsignals+i])
        # The sum of the signal is the total
        solver.add(addsum(lsum) == 0)
