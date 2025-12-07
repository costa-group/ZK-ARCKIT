use num_bigint::{BigInt};
use std::collections::{HashMap, HashSet};
use std::hash::{Hash};
use std::cmp::{Eq};

pub trait Constraint {

    type Fingerprint<T: Hash + Eq + Default + Copy + Ord>: Hash + Eq + Clone;

    fn normalise(&self) -> Vec<Self> where Self: Sized;
    fn normalisation_choices(&self) -> Vec<BigInt>;
    fn signals(&self) -> HashSet<usize>;
    fn fingerprint<T: Hash + Eq + Default + Copy + Ord>(&self, signal_to_fingerprint: &HashMap<usize, T>) -> Self::Fingerprint<T>;
    fn is_nonlinear(self) -> bool;
    fn get_coefficients(self) -> impl Hash + Eq;
}