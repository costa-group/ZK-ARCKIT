use std::collections::HashMap;
use either::Either;

use crate::constraint::Constraint;

pub fn signals_to_constraints_with_them(
    cons: &Vec<impl Constraint>,
    names: Option<&Vec<usize>>,
    mut _signal_to_cons: Option<HashMap<usize, Vec<usize>>>
) -> HashMap<usize, Vec<usize>> {
    
    let mut signal_to_cons = _signal_to_cons.unwrap_or_else(HashMap::new);

    for (i, con) in names.map(|v| Either::Left(v.iter().copied())).unwrap_or_else(|| Either::Right(0..cons.len())).zip(cons.iter()) {
        for signal in con.signals().iter().copied() { // hmmm copied copied...
            signal_to_cons.entry(signal).or_insert_with(Vec::new).push(i)
        }
    }

    signal_to_cons
}