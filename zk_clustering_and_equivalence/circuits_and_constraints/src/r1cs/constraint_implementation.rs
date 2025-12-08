use num_bigint::{BigInt};
use std::collections::{HashSet, HashMap};
use std::hash::Hash;
use std::cmp::Eq;
use rand::Rng;
use std::array::from_fn;
use itertools::Itertools;
use std::mem::swap;
use std::fmt::Debug;

use super::{R1CSConstraint};
use crate::constraint::{Constraint};
use crate::normalisation::division_normalise;
use crate::modular_arithmetic::{mul, div};

impl Constraint for R1CSConstraint {

    fn normalise(&self, prime: &BigInt) -> Vec<R1CSConstraint> {

        // first normalise the quadratic term if there is one
        let mut choices_ab: Vec<(&BigInt, &BigInt)> = Vec::new();
        let choices_a: Vec<BigInt>;
        let choices_b: Vec<BigInt>;

        if self.is_nonlinear() {
            choices_a = self.0.get(&0).map(|bigint| vec![bigint.clone()]).unwrap_or_else(|| division_normalise( &self.0.values().collect::<Vec<&BigInt>>(), prime, true ) );
            choices_b = self.1.get(&0).map(|bigint| vec![bigint.clone()]).unwrap_or_else(|| division_normalise( &self.1.values().collect::<Vec<&BigInt>>(), prime, true ) );
        
            choices_ab.extend(choices_a.iter().cartesian_product(choices_b.iter()));
        }

        // now collect the choices for AB with the choices for C
        let big_one = BigInt::from(1);
        let choices: Vec<((&BigInt, &BigInt), &BigInt)>;
        let choices_c: Vec<BigInt>;

        // if C has a constant normalise by that
        if let Some(c_constant) = self.2.get(&0) {
            if choices_ab.len() == 0 {choices_ab.push((&big_one, &big_one))}
            choices = choices_ab.into_iter().cartesian_product([c_constant].into_iter()).collect();

        // Otherwise if there are no AB choices normalise by C division norm
        } else if choices_ab.len() == 0 {
            choices_ab.push((&big_one, &big_one));
            choices_c = division_normalise( &self.2.values().collect::<Vec<&BigInt>>(), prime, true );
            choices = choices_ab.into_iter().cartesian_product(choices_c.iter()).collect();
        // Otherwise if there are AB choices, normalise by this and calculate the appropriate c_factor
        } else {
            choices_c = choices_ab.iter().map(|&(l, r)| mul(l, r, prime)).collect();
            choices = choices_ab.into_iter().zip(choices_c.iter()).collect();
        }

        choices.into_iter().map(|((a_factor, b_factor), c_factor)| {
            let nonlinear_part_a = self.0.keys().map(|sig| (*sig, div(self.0.get(sig).unwrap(), a_factor, prime).ok().unwrap()) ).collect::<HashMap<usize, BigInt>>();
            let nonlinear_part_b = self.1.keys().map(|sig| (*sig, div(self.1.get(sig).unwrap(), b_factor, prime).ok().unwrap()) ).collect::<HashMap<usize, BigInt>>();
            let nonlinear_part_c = self.2.keys().map(|sig| (*sig, div(self.2.get(sig).unwrap(), c_factor, prime).ok().unwrap()) ).collect::<HashMap<usize, BigInt>>();
            if nonlinear_part_a.values().sorted().cmp(nonlinear_part_b.values().sorted()).is_gt() {
                (nonlinear_part_b, nonlinear_part_a, nonlinear_part_c)
            } else {
                (nonlinear_part_a, nonlinear_part_b, nonlinear_part_c)
            }
        }).collect()
    }

    fn signals(&self) -> HashSet<usize>{
        self.0.keys().chain(self.1.keys()).chain(self.2.keys()).filter(|signal| **signal != 0).copied().collect() //probably quite ugly
    }

    type Fingerprint<T: Hash + Eq + Default + Copy + Ord + Debug> = (Vec<(T, (BigInt, BigInt))>, Vec<(T, BigInt)>, Vec<(T, BigInt)>);

    fn fingerprint<T: Hash + Eq + Default + Copy + Ord + Debug>(&self, signal_to_fingerprint: &HashMap<usize, T>) -> Self::Fingerprint<T> {
        let is_ordered = !(self.0.len() > 0 && self.1.len() > 0 && self.0.values().sorted().eq(self.1.values().sorted()));

        fn _get_signal_fingerprint<T: Hash + Eq + Default + Copy>(sig: &usize, signal_to_fingerprint: &HashMap<usize, T>) -> T {
            if sig == &0 {T::default()} else {*signal_to_fingerprint.get(sig).unwrap()}
        }

        let part_to_sorted_vec = |part: &HashMap<usize, BigInt>| part.iter().map(|(sig, val)| (_get_signal_fingerprint(sig, signal_to_fingerprint), val.clone())).sorted().collect::<Vec<_>>();
        // Ended up having to Clone BigInts... not sure there's a way around this unless we convert to some smaller form which I don't like

        if is_ordered {
            // first has a buffer to maintain the same type. when comparing to unordered it will never equal as no unordered has 0 as coef in first part
            (self.0.iter().map(|(sig, val)| (_get_signal_fingerprint(sig, signal_to_fingerprint), (val.clone(), BigInt::default()))).sorted().collect::<Vec<_>>(), part_to_sorted_vec(&self.1), part_to_sorted_vec(&self.2))
        } else {
            let (lsignals, rsignals) = (self.0.keys().copied().collect::<HashSet<_>>(), self.1.keys().copied().collect::<HashSet<_>>());

            let in_both = lsignals.intersection(&rsignals).copied().collect::<HashSet<_>>();
            let (only_left, only_right) = (lsignals.difference(&in_both), rsignals.difference(&in_both));

            let sort_pair_bigint = |left: BigInt, right: BigInt| if left <= right {(left, right)} else {(right, left)};

            (
                in_both.iter().map(|sig| (_get_signal_fingerprint(sig, signal_to_fingerprint), sort_pair_bigint(self.0.get(sig).unwrap().clone(), self.1.get(sig).unwrap().clone()) ) ).sorted().collect::<Vec<_>>(), // both parts
                only_left.map(|sig| (sig, self.0.get(sig).unwrap().clone())).chain(only_right.map(|sig| (sig, self.1.get(sig).unwrap().clone()))).map(|(sig, val)| (_get_signal_fingerprint(sig, signal_to_fingerprint), val) ).sorted().collect::<Vec<_>>(), // only one part
                part_to_sorted_vec(&self.2)
            )
        }
    }

    fn is_nonlinear(&self) -> bool{
        self.0.len() > 0 && self.1.len() > 0
    }
    fn get_coefficients(&self) -> impl Hash + Eq{
        unimplemented!("This function is not implemented yet")
    }

    fn add_random_constant_factor(&mut self, rng: &mut impl Rng, field: &BigInt) -> () {
        let factors: [u64; 2] = from_fn(|_| rng.random::<u32>() as u64);
    
        let a_bigfactor = &BigInt::from(factors[0]);
        let b_bigfactor = &BigInt::from(factors[1]);
        let c_bigfactor = &BigInt::from(factors[0] * factors[1]);

        for (bigint, big_factor) in self.0.values_mut().map(|bigint| (bigint, a_bigfactor)).chain(
                                    self.1.values_mut().map(|bigint| (bigint, b_bigfactor))).chain(
                                    self.2.values_mut().map(|bigint| (bigint, c_bigfactor))) 
            {*bigint = mul(big_factor, bigint, field)}
    }

    fn shuffle_constraint_internals(&mut self, rng: &mut impl Rng) -> () {
        // HashMap is already unordered so no need to shuffle there

        // Swap A/B parts at random
        if rng.random::<bool>() {
            swap(&mut self.0, &mut self.1);
        }
    }

}