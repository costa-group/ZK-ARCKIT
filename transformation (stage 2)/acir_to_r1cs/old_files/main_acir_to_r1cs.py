#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar 17 15:07:28 2025

@author: clara
"""

import acir_to_r1cs_v2
import json


def parse_air_constraint(constraint, signals):
    coefs = {}
    for m in constraint["mul"]:
        i = m["witness1"]
        j = m["witness2"]
        coef = m["coeff"]
        ordered_pair = (i, j) if i < j else (j, i)
        coefs[ordered_pair] = coef
        signals.add(i)
        signals.add(j)
    return coefs
        


def parse_circuit(circuit):
    parsed_coefficients = []
    signals = set()
    for c in circuit["constraints"]:
        parsed_coefficients.append(parse_air_constraint(c, signals))
    return parsed_coefficients, len(signals)
    



import argparse
parser = argparse.ArgumentParser()

parser.add_argument("filein", help=".json file including the constraints",
                    type=str)
parser.add_argument("n", help="Maximum number of admited aux signals",
                    type=str)
parser.add_argument("fileout", help= "Output file with the Z3 problem")


args=parser.parse_args()


# Opening JSON file
f = open(args.filein)
data = json.load(f)

print(data)

# Parse the input file and generate the needed non linear coefficients
constraints, n_signals = parse_circuit(data)

print(constraints)

# Generate the Z3 problem
file = open(args.fileout, "w")
acir_to_r1cs_v2.generate_problem_r1cs_transformation(file, constraints, n_signals, int(args.n))


