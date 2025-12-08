use std::collections::{HashSet, HashMap};
use itertools::Itertools;

use crate::num_bigint::BigInt;
use crate::modular_arithmetic::{add, div, ArithmeticError};


fn non_zero_sum_normalise(lineq: &Vec<&BigInt>, prime: &BigInt) -> Result<BigInt, ArithmeticError> {
    
    let sum: BigInt = lineq.into_iter().fold(BigInt::from(0), |curr, next| add(&curr, next, prime));
    if sum == BigInt::from(0) {
        Err(ArithmeticError::DivisionByZero)
    } else {
        Ok(sum)
    }
}

pub fn division_normalise(lineq: &Vec<&BigInt>, prime: &BigInt, early_exit: bool) -> Vec<BigInt> {

    // If can early exit then do
    let ee_value: Option<BigInt> = if early_exit {non_zero_sum_normalise(lineq, prime).ok()} else {None};

    if let Some(choice) = ee_value {
        [choice].into_iter().collect()
    } else {

        let unique_lineq: Vec<&BigInt> = lineq.into_iter().collect::<HashSet<_>>().into_iter().copied().collect();
        
        // If can early exit with unique then do

        let ee_value: Option<BigInt> = if early_exit {non_zero_sum_normalise(&unique_lineq, prime).ok()} else {None};
        if let Some(choice) = ee_value {
            [choice].into_iter().collect()
        } else {

            fn find_next_subset<'a>(lineq: Vec<&'a BigInt>, prime: &'a BigInt) -> Vec<&'a BigInt> {

                let mut equiv_classes: HashMap<BigInt, Vec<usize>> = HashMap::new();

                for (l, r) in (0..lineq.len()).into_iter().cartesian_product((0..lineq.len()).into_iter()) {
                    equiv_classes.entry(div(lineq[l], lineq[r], prime).ok().expect("Value passed to lineq for divisionnorm is 0")).or_insert(Vec::new()).push(l);
                }

                let equiv_classes_vec = equiv_classes.into_iter().collect::<Vec<_>>();
                equiv_classes_vec.iter().min_by_key(|&(k, class)| (class.len(), k)).unwrap().1.iter().copied().map(|idx| lineq[idx]).collect()
            }

            let mut prev_length: usize = 0;
            let mut subset = unique_lineq;

            while prev_length != subset.len() {
                prev_length = subset.len();
                subset = find_next_subset(subset, prime);
            }

            // this ensures we can actually be early exiting -- performance loss is minimal as this is basically always <2 BigInts -- still annoying
            subset.into_iter().cloned().collect::<Vec<BigInt>>()
        }
    }
}