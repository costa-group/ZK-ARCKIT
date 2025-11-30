use num_bigint::{BigInt};
use std::collections::{HashSet, HashMap};
use std::hash::Hash;
use std::cmp::Eq;

use super::{R1CSConstraint};
use crate::constraint::{Constraint};

impl Constraint for R1CSConstraint {

    fn normalise(&self) -> Vec<impl Constraint>{
        unimplemented!("This function is not implemented yet");
        vec![(HashMap::new(), HashMap::new(), HashMap::new())]
    }
    fn normalisation_choices(&self) -> Vec<BigInt>{
        unimplemented!("This function is not implemented yet")
    }
    fn signals(&self) -> &HashSet<usize>{
        unimplemented!("This function is not implemented yet")
    }
    fn fingerprint(&self, signal_to_fingerprint: &HashMap<usize, usize>) -> impl Hash + Eq{
        unimplemented!("This function is not implemented yet")
    }
    fn is_nonlinear(self) -> bool{
        unimplemented!("This function is not implemented yet")
    }
    fn get_coefficients(self) -> impl Hash + Eq{
        unimplemented!("This function is not implemented yet")
    }

}