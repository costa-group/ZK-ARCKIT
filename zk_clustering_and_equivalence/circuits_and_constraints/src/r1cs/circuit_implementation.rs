use num_bigint::{BigInt};
use std::collections::{HashMap, HashSet};
use std::hash::Hash;
use std::cmp::Eq;
use itertools::sorted;

use super::{R1CSConstraint, R1CSData};
use utils::assignment::{Assignment};
use crate::circuit::Circuit;

impl Circuit<R1CSConstraint> for R1CSData {
    
    fn prime(&self) -> &BigInt {&self.header_data.field}
    fn n_constraints(&self) -> usize {self.header_data.number_of_constraints}
    fn n_wires(&self) -> usize {self.header_data.total_wires}
    fn constraints(&self) -> &Vec<R1CSConstraint> {&self.constraints}
    fn get_normalised_constraints(&self) -> &Vec<R1CSConstraint> {unimplemented!("This function is not implemented yet")}
    fn normi_to_coni(&self) -> &Vec<usize> {unimplemented!("This function is not implemented yet")}
    fn n_inputs(&self) -> usize {self.header_data.public_inputs + self.header_data.private_inputs}
    fn n_outputs(&self) -> usize {self.header_data.public_outputs}
    fn signal_is_input(&self, signal: usize) -> bool {self.header_data.public_outputs < signal && signal <= self.header_data.public_inputs + self.header_data.private_inputs + self.header_data.public_outputs} 
    fn signal_is_output(&self, signal: usize) -> bool {0 < signal && signal <= self.header_data.public_outputs}
    fn get_signals(&self) -> impl Iterator<Item = usize> {1..self.header_data.total_wires}
    fn get_input_signals(&self) -> impl Iterator<Item = usize> {self.header_data.public_outputs+1..=self.header_data.public_inputs + self.header_data.private_inputs + self.header_data.public_outputs}
    fn get_output_signals(&self) -> impl Iterator<Item = usize> {1..=self.header_data.public_outputs}
    fn parse_file(&mut self, file: &str) -> () {
        let parsed_circuit = crate::r1cs::r1cs_reader::read_r1cs(file).unwrap();

        self.header_data = parsed_circuit.header_data;
        self.constraints = parsed_circuit.constraints;
        self.signals = parsed_circuit.signals;
        self.custom_gates = parsed_circuit.custom_gates;
        self.custom_gates_used_data = parsed_circuit.custom_gates_used_data;
        self.custom_gates_applied_data = parsed_circuit.custom_gates_applied_data;

    }
    fn write_file(&self, file: &str) -> () {unimplemented!("This function is not implemented yet")}
    
    type SignalFingerprint<T: Hash + Eq + Default + Copy + Ord> = Vec<(T, ((BigInt, BigInt), BigInt, BigInt))>;

    fn fingerprint_signal<T: Hash + Eq + Default + Copy + Ord>(
        &self, 
        signal: usize, 
        normalised_constraints: &Vec<R1CSConstraint>, 
        normalised_constraint_to_fingerprints: &HashMap<usize, T>, 
        _prev_signal_to_fingerprint: &HashMap<usize, T>, 
        signal_to_normi: &Vec<Vec<usize>>
    ) -> Self::SignalFingerprint<T> {
        
        let mut fingerprint = Vec::new();

        for normi in signal_to_normi[signal].iter() {

            let norm = &normalised_constraints[*normi];
            let is_ordered: bool = !(norm.0.len() > 0 && norm.1.len() > 0 && sorted(norm.0.values()).eq(sorted(norm.1.values())));
            // tuples don't play nice with iterables
            let (a_val, b_val, c_val) = (norm.0.get(&signal).cloned().unwrap_or_else(|| BigInt::default()), norm.1.get(&signal).cloned().unwrap_or_else(|| BigInt::default()), norm.2.get(&signal).cloned().unwrap_or_else(|| BigInt::default()));
            let big_zero = &BigInt::default();

            if is_ordered {
                fingerprint.push(
                    (*normalised_constraint_to_fingerprints.get(normi).unwrap(), ((a_val, BigInt::default()), b_val, c_val))
                );
            } else {
                let sort_pair_bigint = |left: BigInt, right: BigInt| if left <= right {(left, right)} else {(right, left)};
                let first_term: (BigInt, BigInt);
                let second_term: BigInt;

                if !a_val.eq(big_zero) && !b_val.eq(big_zero) {
                    first_term = sort_pair_bigint(a_val, b_val);
                    second_term = BigInt::default();
                } else {
                    first_term = (BigInt::default(), BigInt::default());
                    if !a_val.eq(big_zero) {
                        second_term = a_val;
                    } else {
                        second_term = b_val;
                    }  
                } 

                fingerprint.push(
                    (*normalised_constraint_to_fingerprints.get(normi).unwrap(), (first_term,second_term,c_val))
                );
            }
        }

        fingerprint
    }
    
    fn take_subcircuit(
        &self, 
        constraint_subset: &Vec<usize>, 
        input_signals: Option<&HashSet<usize>>, 
        output_signals: Option<&HashSet<usize>>, 
        signal_map: Option<&HashMap<usize,usize>>, 
        return_signal_mapping: Option<bool>
    ) -> R1CSData {
        unimplemented!("This function is not implemented yet");
        R1CSData::new()
    }
    
    fn singular_class_requires_additional_constraints() -> bool {false}

    fn encode_single_norm_pair(
        &self, // TODO: figure out if necessary
        norms: &Vec<R1CSConstraint>,
        is_ordered: bool,
        signal_pair_encoder: &Assignment<usize, 2>,
        signal_to_fingerprint: (HashMap<usize, usize>, HashMap<usize, usize>),
        fingerprint_to_signals: (HashMap<usize, Vec<usize>>, HashMap<usize, Vec<usize>>),
        is_singular_class: Option<bool>
    ) -> impl Hash + Eq {unimplemented!("This function is not implemented yet")}

    fn normalise_constraints(&self) -> () {unimplemented!("This function is not implemented yet")}

}