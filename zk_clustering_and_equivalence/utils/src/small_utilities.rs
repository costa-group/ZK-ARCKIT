use std::collections::{HashMap, HashSet, VecDeque};
use either::Either;

use circuits_and_constraints::constraint::Constraint;

pub fn signals_to_constraints_with_them(
    cons: &Vec<impl Constraint>,
    names: Option<&Vec<usize>>,
    mut signal_to_cons: Option<HashMap<usize, Vec<usize>>>
) -> HashMap<usize, Vec<usize>> {
    
    let mut signal_to_cons = signal_to_cons.unwrap_or_else(HashMap::new);

    for (i, con) in names.map(|v| Either::Left(v.iter().copied())).unwrap_or_else(|| Either::Right(0..cons.len())).zip(cons.iter()) {
        for signal in con.signals().iter().copied() { // hmmm copied copied...
            signal_to_cons.entry(signal).or_insert_with(Vec::new).push(i)
        }
    }

    signal_to_cons
}

pub fn distance_to_source_set(source_set: impl Iterator<Item = usize>, adjacencies: &HashMap<usize, HashSet<usize>>) -> HashMap<usize, usize> {

    let mut distance: HashMap<usize, usize> = source_set.map(|idx| (idx, 0)).collect();
    let mut queue: VecDeque<usize> = distance.keys().copied().collect();

    while queue.len() > 0 {
        let curr = queue.pop_front().unwrap();
        queue.extend(adjacencies.get(&curr).unwrap().iter().filter(|key| !distance.contains_key(key)));
        let next_distance = distance.get(&curr).unwrap() + 1;
        for adj in adjacencies.get(&curr).unwrap().iter() {distance.entry(curr).or_insert(next_distance);}
    };

    distance
}