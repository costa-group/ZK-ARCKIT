use num_bigint::{BigInt};
use std::collections::{HashSet, HashMap};
use std::hash::Hash;
use std::cmp::Eq;
use itertools::sorted;

use super::{R1CSConstraint};
use crate::constraint::{Constraint};

impl Constraint for R1CSConstraint {

    fn normalise(&self) -> Vec<R1CSConstraint>{
        unimplemented!("This function is not implemented yet");
        vec![(HashMap::new(), HashMap::new(), HashMap::new())]
    }
    fn normalisation_choices(&self) -> Vec<BigInt>{
        unimplemented!("This function is not implemented yet")
    }
    fn signals(&self) -> HashSet<usize>{
        self.0.keys().chain(self.1.keys()).chain(self.2.keys()).filter(|signal| **signal != 0).copied().collect() //probably quite ugly
    }

    type Fingerprint<T: Hash + Eq + Default + Copy + Ord> = (Vec<(T, (BigInt, BigInt))>, Vec<(T, BigInt)>, Vec<(T, BigInt)>);

    fn fingerprint<T: Hash + Eq + Default + Copy + Ord>(&self, signal_to_fingerprint: &HashMap<usize, T>) -> Self::Fingerprint<T> {
        let is_ordered = !(self.0.len() > 0 && self.1.len() > 0 && sorted(self.0.values()).eq(sorted(self.1.values())));

        fn _get_signal_fingerprint<T: Hash + Eq + Default + Copy>(sig: &usize, signal_to_fingerprint: &HashMap<usize, T>) -> T {
            if sig == &0 {T::default()} else {*signal_to_fingerprint.get(sig).unwrap()}
        }

        let part_to_sorted_vec = |part: &HashMap<usize, BigInt>| sorted(part.iter().map(|(sig, val)| (_get_signal_fingerprint(sig, signal_to_fingerprint), val.clone()))).collect::<Vec<_>>();
        // Ended up having to Clone BigInts... not sure there's a way around this unless we convert to some smaller form which I don't like

        if is_ordered {
            // first has a buffer to maintain the same type. when comparing to unordered it will never equal as no unordered has 0 as coef in first part
            (sorted(self.0.iter().map(|(sig, val)| (_get_signal_fingerprint(sig, signal_to_fingerprint), (val.clone(), BigInt::default())))).collect::<Vec<_>>(), part_to_sorted_vec(&self.1), part_to_sorted_vec(&self.2))
        } else {
            let (lsignals, rsignals) = (self.0.keys().copied().collect::<HashSet<_>>(), self.1.keys().copied().collect::<HashSet<_>>());

            let in_both = lsignals.intersection(&rsignals).copied().collect::<HashSet<_>>();
            let (only_left, only_right) = (lsignals.difference(&in_both), rsignals.difference(&in_both));

            let sort_pair_bigint = |left: BigInt, right: BigInt| if left <= right {(left, right)} else {(right, left)};

            (
                sorted(in_both.iter().map(|sig| (_get_signal_fingerprint(sig, signal_to_fingerprint), sort_pair_bigint(self.0.get(sig).unwrap().clone(), self.1.get(sig).unwrap().clone()) ) )).collect::<Vec<_>>(), // both parts
                sorted(only_left.map(|sig| (sig, self.0.get(sig).unwrap().clone())).chain(only_right.map(|sig| (sig, self.1.get(sig).unwrap().clone()))).map(|(sig, val)| (_get_signal_fingerprint(sig, signal_to_fingerprint), val) )).collect::<Vec<_>>(), // only one part
                part_to_sorted_vec(&self.2)
            )
        }
    }

    fn is_nonlinear(self) -> bool{
        unimplemented!("This function is not implemented yet")
    }
    fn get_coefficients(self) -> impl Hash + Eq{
        unimplemented!("This function is not implemented yet")
    }

}