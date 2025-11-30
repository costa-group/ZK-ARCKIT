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
    fn signals(&self) -> HashSet<usize>{
        // really georgous code here
        let mut set = HashSet::new();
        set.extend(self.0.keys().chain(self.1.keys()).chain(self.2.keys()).filter(|signal| **signal != 0));

        set
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