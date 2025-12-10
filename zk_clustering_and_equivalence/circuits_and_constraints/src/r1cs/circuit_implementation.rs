use num_bigint::{BigInt};
use std::collections::{HashMap, HashSet};
use std::hash::Hash;
use std::cmp::Eq;
use itertools::sorted;
use rand::seq::SliceRandom;
use rand::Rng;
use std::fmt::Debug;

use super::{R1CSConstraint, R1CSData, SignalList, HeaderData, ConstraintList};
use utils::assignment::{Assignment};
use crate::circuit::Circuit;
use crate::r1cs::r1cs_reader::read_r1cs;
use crate::utils::FingerprintIndex;

impl Circuit<R1CSConstraint> for R1CSData {
    
    fn new() -> Self {
        R1CSData {
            header_data: HeaderData {
                field: BigInt::from(0),
                field_size: 0,
                total_wires: 0,
                public_outputs: 0,
                public_inputs: 0,
                private_inputs: 0,
                number_of_labels: 0,
                number_of_constraints: 0,
            },
            custom_gates: false,
            constraints: ConstraintList::new(),
            signals: SignalList::new(),
            custom_gates_used_data: None,
            custom_gates_applied_data: None,
        }
    }

    fn prime(&self) -> &BigInt {&self.header_data.field}
    fn n_constraints(&self) -> usize {self.header_data.number_of_constraints}
    fn n_wires(&self) -> usize {self.header_data.total_wires}
    
    
    fn get_constraints(&self) -> &Vec<R1CSConstraint> {&self.constraints}
    fn get_mut_constraints(&mut self) -> &mut Vec<R1CSConstraint> {&mut self.constraints}

    fn normi_to_coni(&self) -> &Vec<usize> {unimplemented!("This function is not implemented yet")}
    fn n_inputs(&self) -> usize {self.header_data.public_inputs + self.header_data.private_inputs}
    fn n_outputs(&self) -> usize {self.header_data.public_outputs}
    fn signal_is_input(&self, signal: usize) -> bool {self.header_data.public_outputs < signal && signal <= self.header_data.public_inputs + self.header_data.private_inputs + self.header_data.public_outputs} 
    fn signal_is_output(&self, signal: usize) -> bool {0 < signal && signal <= self.header_data.public_outputs}
    fn get_signals(&self) -> impl Iterator<Item = usize> {1..self.header_data.total_wires}
    fn get_input_signals(&self) -> impl Iterator<Item = usize> {self.header_data.public_outputs+1..=self.header_data.public_inputs + self.header_data.private_inputs + self.header_data.public_outputs}
    fn get_output_signals(&self) -> impl Iterator<Item = usize> {1..=self.header_data.public_outputs}
    fn parse_file(&mut self, file: &str) -> () {
        let parsed_circuit = read_r1cs(file).unwrap();

        self.header_data = parsed_circuit.header_data;
        self.constraints = parsed_circuit.constraints;
        self.signals = parsed_circuit.signals;
        self.custom_gates = parsed_circuit.custom_gates;
        self.custom_gates_used_data = parsed_circuit.custom_gates_used_data;
        self.custom_gates_applied_data = parsed_circuit.custom_gates_applied_data;

    }
    fn write_file(&self, file: &str) -> () {unimplemented!("This function is not implemented yet")}
    
    type SignalFingerprint<'a, T: Hash + Eq + Default + Copy + Ord + Debug> = Vec<(FingerprintIndex<T>, ((Option<&'a BigInt>, Option<&'a BigInt>), Option<&'a BigInt>, Option<&'a BigInt>))>;

    fn fingerprint_signal<'a, T: Hash + Eq + Default + Copy + Ord + Debug>(
        &self, 
        signal: &usize,
        fingerprint: &mut Option<Self::SignalFingerprint<'a, T>>, 
        normalised_constraints: &'a Vec<R1CSConstraint>, 
        normalised_constraint_to_fingerprints: &HashMap<usize, T>, 
        _prev_signal_to_fingerprint: &HashMap<usize, T>, 
        signal_to_normi: &HashMap<usize, Vec<usize>>
    ) -> () where R1CSConstraint: 'a {

        if let Some(existing_fingerprint) = fingerprint.as_mut() {
            for item in existing_fingerprint.into_iter() {
                item.0.fingerprint = *normalised_constraint_to_fingerprints.get(&item.0.index).unwrap();
            }
            existing_fingerprint.sort();
        } else {

            
            let mut new_fingerprint = Vec::new();

            for normi in signal_to_normi.get(signal).unwrap().into_iter().copied() {

                let fi_index = FingerprintIndex { fingerprint: *normalised_constraint_to_fingerprints.get(&normi).unwrap(), index: normi };
                let norm = &normalised_constraints[normi];
                let is_ordered: bool = !(norm.0.len() > 0 && norm.1.len() > 0 && sorted(norm.0.values()).eq(sorted(norm.1.values())));
                // tuples don't play nice with iterables
                let (a_val, b_val, c_val): (Option<&'a BigInt>, Option<&'a BigInt>, Option<&'a BigInt>) = (norm.0.get(signal), norm.1.get(signal), norm.2.get(signal));

                if is_ordered {
                    new_fingerprint.push(
                        (fi_index, ((a_val, None), b_val, c_val))
                    );
                } else {
                    let sort_pair_bigint = |left: Option<&'a BigInt>, right: Option<&'a BigInt>| if left <= right {(left, right)} else {(right, left)};
                    let first_term: (Option<&'a BigInt>, Option<&'a BigInt>);
                    let second_term: Option<&'a BigInt>;

                    if a_val.is_some() && b_val.is_some() {
                        first_term = sort_pair_bigint(a_val, b_val);
                        second_term = None;
                    } else {
                        first_term = (None, None);
                        if a_val.is_some() {
                            second_term = a_val;
                        } else {
                            second_term = b_val;
                        }  
                    } 

                    new_fingerprint.push(
                        (fi_index, (first_term,second_term,c_val))
                    );
                }
            }

            new_fingerprint.sort();
            *fingerprint = Some(new_fingerprint);
        }
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

    fn shuffle_signals(self, rng: &mut impl Rng) -> Self {
        let mut outputs: Vec<usize> = self.get_output_signals().into_iter().collect();
        let mut inputs: Vec<usize> = self.get_input_signals().into_iter().collect();
        let mut remaining: Vec<usize> = (self.n_outputs() + self.n_inputs() + 1..self.n_wires()).into_iter().collect();
    
        outputs.shuffle(rng);
        inputs.shuffle(rng);
        remaining.shuffle(rng);
    
        let mapping: Vec<usize> = [0].into_iter().chain(outputs.into_iter()).chain(inputs.into_iter()).chain(remaining.into_iter()).collect();

        // constructing new constraint lists needs to consume the current one and for that we need to consume Self -- this avoids cloning a whole bunch of BigInts
        let Self {header_data, custom_gates, constraints, signals, custom_gates_used_data, custom_gates_applied_data} = self;

        let new_constraints = constraints.into_iter().map(|cons|
            (cons.0.into_iter().map(|(k, val)| (mapping[k], val)).collect::<HashMap<usize, BigInt>>(),
             cons.1.into_iter().map(|(k, val)| (mapping[k], val)).collect::<HashMap<usize, BigInt>>(),
             cons.2.into_iter().map(|(k, val)| (mapping[k], val)).collect::<HashMap<usize, BigInt>>())
        ).collect::<Vec<R1CSConstraint>>();

        Self {header_data: header_data, custom_gates: custom_gates, constraints: new_constraints, signals: signals, custom_gates_used_data: custom_gates_used_data, custom_gates_applied_data: custom_gates_applied_data}
    }
}