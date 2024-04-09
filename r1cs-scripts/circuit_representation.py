#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar 22 17:47:25 2021

@author: clara
"""
import constraint


class Circuit:
    def __init__(self):
        self.constraints = []
        self.signal2label = {}
        self.label2signal = {}
    
    
    def update_header(self, field_size, prime_number, nWires, nPubOut, nPubIn, nPrvIn, nLabels, nConstraints):
        self.field_size = field_size
        self.prime_number = prime_number
        self.nWires = nWires
        self.nPubOut = nPubOut
        self.nPubIn = nPubIn
        self.nPrvIn = nPrvIn
        self.nLabels = nLabels
        self.nConstraints = nConstraints
        
    
    def add_signal2label(self, signal, label):
        self.signal2label[signal] = label
    
    def add_label2signal(self, signal, label):
        self.label2signal[label] = signal
    
    def add_constraint(self, new_constraint):
        self.constraints.append(new_constraint)
        
    def print_header_terminal(self):
        print('Field size:', self.field_size)
        print('Prime number:', self.prime_number)
        print('Number of wires:', self.nWires)
        print('Number of Public Outputs:', self.nPubOut)
        print('Number of Public Inputs:', self.nPubIn)
        print('Number of Private Inputs:', self.nPrvIn)
        print('Number of Labels:', self.nLabels)
        print('Number of Constraints:', self.nConstraints)
        
    def print_header(self, out):
        print('Field size:', self.field_size, file = out)
        print('Prime number:', self.prime_number, file = out)
        print('Number of wires:', self.nWires, file = out)
        print('Number of Public Outputs:', self.nPubOut, file = out)
        print('Number of Public Inputs:', self.nPubIn, file = out)
        print('Number of Private Inputs:', self.nPrvIn, file = out)
        print('Number of Labels:', self.nLabels, file = out)
        print('Number of Constraints:', self.nConstraints, file = out)
    
    def print_constraints(self, out):
        for c in self.constraints:
            print('Showing constraint:', file = out)
            c.print_constraint(out)
    
            
    def print_constraints_terminal(self):
        for c in self.constraints:
            print('Showing constraint:')
            c.print_constraint_terminal()

    def print_constraints_translation(self):
        for c in self.constraints:
            print('-> Showing constraint:')
            c.print_constraint_translation(self.label2signal)
    
    def print_labels(self, out):
        for (s, l) in self.signal2label.items():
            print('Signal:', s, '->', l, file = out)
        
        
    def normalize_constraints(self):
        i = 0 
        j = 0
        hash_constraints = set()
        while i < len(self.constraints):
            self.constraints[i].normalize()
            if self.constraints[i].isEmpty():
                self.constraints.pop(i)
            elif self.constraints[i].get_hash() in hash_constraints:
                self.constraints.pop(i)
            else:
                hash_constraints.add(self.constraints[i].get_hash())
                i = i + 1
            j = j + 1
    
    def substitute_simplification(self, map_labels):
        for c in self.constraints:
            c.substitute_simplification(map_labels)
        
    def substitute_labels(self, map_labels):
        for c in self.constraints:
            c.substituteLabels(map_labels)
            
            
    def update_order(self, signals_to_order, order_to_signals):
        changed = True
        while changed:
            changed = False
            for c in self.constraints:
                changed |= c.update_order(signals_to_order, order_to_signals)
        


    def get_constraints_rep(self):
        new_constraints = []
        for c in self.constraints:
            new_constraints.append(c.get_new_rep(self.label2signal))
        return new_constraints
    
    def get_used_signals(self):
        signals = []
        for (s, name) in self.label2signal.items():
            if s != -1:
                signals.append(name)
        return signals
            