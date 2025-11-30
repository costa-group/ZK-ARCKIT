use single_clustering::network::CSRNetwork;
use combinatorial::Combinations;
use std::collections::HashMap;

use circuits_and_constraints::circuit::Circuit;
use circuits_and_constraints::constraint::Constraint;
use utils::small_utilities::signals_to_constraints_with_them;

pub fn shared_signal_graph<C: Constraint>(circ: &impl Circuit<C>) -> CSRNetwork<f32, f32> {

    let signal_to_coni = signals_to_constraints_with_them(&circ.constraints(), None, None);
    let mut weights: HashMap<(usize, usize), usize> = HashMap::new();

    for pair in signal_to_coni.keys().flat_map(|signal| Combinations::of_size(signal_to_coni.get(signal).unwrap(), 2)).map(|pair| (*pair[0], *pair[1])){
        weights.insert(pair, 1 + weights.get(&pair).unwrap_or(&0));
    }
    
    CSRNetwork::from_edges(weights.iter().map(|(pair, val)| (pair.0, pair.1, *val as f32)).collect::<Vec<_>>().as_ref(), vec![1 as f32; circ.n_constraints()])
}
