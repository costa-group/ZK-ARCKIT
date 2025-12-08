use num_bigint::{BigInt};
use std::collections::{HashMap, HashSet};
use std::hash::{Hash};
use std::cmp::{Eq};
use rand::Rng;
use std::fmt::Debug;

pub trait Constraint {

    type Fingerprint<T: Hash + Eq + Default + Copy + Ord + Debug>: Hash + Eq + Clone + Debug;

    fn normalise(&self, prime: &BigInt) -> Vec<Self> where Self: Sized;
    fn signals(&self) -> HashSet<usize>;
    fn fingerprint<T: Hash + Eq + Default + Copy + Ord + Debug>(&self, signal_to_fingerprint: &HashMap<usize, T>) -> Self::Fingerprint<T>;
    fn is_nonlinear(&self) -> bool;
    fn get_coefficients(&self) -> impl Hash + Eq;
    fn add_random_constant_factor(&mut self, rng: &mut impl Rng, field: &BigInt) -> ();
    fn shuffle_constraint_internals(&mut self, rng: &mut impl Rng) -> ();
}