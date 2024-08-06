from r1cs_scripts.constraint import Constraint

def getvars(con: Constraint) -> set:
    return set(con.A.keys()).union(con.B.keys()).union(con.C.keys()).difference(set([0]))
    