use num_bigint::{BigInt};
use std::collections::{HashMap, HashSet};
use std::hash::{Hash};
use std::cmp::{Eq};

pub trait Constraint {

    fn normalise(&self) -> Vec<impl Constraint>;
    fn normalisation_choices(&self) -> Vec<BigInt>;
    fn signals(&self) -> &HashSet<usize>;
    fn fingerprint(&self, signal_to_fingerprint: &HashMap<usize, usize>) -> impl Hash + Eq;
    fn is_nonlinear(self) -> bool;
    fn get_coefficients(self) -> impl Hash + Eq;
}