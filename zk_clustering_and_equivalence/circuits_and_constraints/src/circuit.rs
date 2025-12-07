use num_bigint::{BigInt};
use std::collections::{HashMap, HashSet};
use std::hash::{Hash};
use std::cmp::{Eq};

use crate::constraint::{Constraint};
use utils::assignment::Assignment;

pub trait Circuit<C: Constraint> {

    type SignalFingerprint<T: Hash + Eq + Default + Copy + Ord>: Hash + Eq + Clone;

    fn prime(&self) -> &BigInt;
    fn n_constraints(&self) -> usize;
    fn n_wires(&self) -> usize;
    fn constraints(&self) -> &Vec<C>;
    fn get_normalised_constraints(&self) -> &Vec<C>;
    fn normi_to_coni(&self) -> &Vec<usize>;
    fn n_inputs(&self) -> usize;
    fn n_outputs(&self) -> usize;
    fn signal_is_input(&self, signal: usize) -> bool;
    fn signal_is_output(&self, signal: usize) -> bool;
    fn get_signals(&self) -> impl Iterator<Item = usize>;
    fn get_input_signals(&self) -> impl Iterator<Item = usize>;
    fn get_output_signals(&self) -> impl Iterator<Item = usize>;
    fn parse_file(&mut self, file: &str) -> ();
    fn write_file(&self, file: &str) -> ();
    
    fn fingerprint_signal<T: Hash + Eq + Default + Copy + Ord>(
        &self, 
        signal: usize, 
        normalised_constraints: &Vec<C>, 
        normalised_constraint_to_fingerprints: &HashMap<usize, T>, 
        prev_signal_to_fingerprint: &Vec<T>, 
        signal_to_normi: &Vec<Vec<usize>>
    ) -> Self::SignalFingerprint<T>;
    
    fn take_subcircuit(
        &self, 
        constraint_subset: &Vec<usize>, 
        input_signals: Option<&HashSet<usize>>, 
        output_signals: Option<&HashSet<usize>>, 
        signal_map: Option<&HashMap<usize,usize>>, 
        return_signal_mapping: Option<bool>
    ) -> Self;
    
    fn singular_class_requires_additional_constraints() -> bool;

    fn encode_single_norm_pair(
        &self, // TODO: figure out if necessary
        norms: &Vec<C>,
        is_ordered: bool,
        signal_pair_encoder: &Assignment<usize, 2>,
        signal_to_fingerprint: (HashMap<usize, usize>, HashMap<usize, usize>),
        fingerprint_to_signals: (HashMap<usize, Vec<usize>>, HashMap<usize, Vec<usize>>),
        is_singular_class: Option<bool>
    ) -> impl Hash + Eq;

    fn normalise_constraints(&self) -> ();

    // fn normalise_constraints(&self) -> None:

    //     if len(&self.normalised_constraints) != 0: 
    //         warnings.warn("Attempting to normalised already normalised constraints")
    //     else:

    //         fn _normalised_constraint_building_step(coni: int, cons: Constraint):
    //             norms = cons.normalise()
    //             &self.normalised_constraints.extend(norms)
    //             &self.normi_to_coni.extend(coni for _ in range(len(norms)))

    //         deque(
    //             maxlen=0,
    //             iterable = itertools.starmap(_normalised_constraint_building_step, enumerate(&self.constraints))
    //         )
}