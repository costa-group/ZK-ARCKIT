use std::collections::HashMap;
use itertools::Itertools;

use circuits_and_constraints::constraint::Constraint;
use circuits_and_constraints::circuit::Circuit;
use equivalence::compare_circuits::compare_circuits_with_inits;
use equivalence::fingerprinting::iterated_refinement;
use utils::assignment::Assignment;

use crate::directed_acyclic_graph::{DAGNode};
use crate::directed_acyclic_graph::iterated_label_propagation::iterated_label_propagation;

// TODO: if required implement the mapping handler -- this requires refactoring compare_circuits

fn naive_equivalency_analysis<'a, C: Constraint + 'a, S: Circuit<C> + 'a>(
    nodes: &HashMap<usize, DAGNode<'a, C, S>>, normalised_constraints_by_id: &HashMap<usize, Vec<C>>, sig_to_normi_by_id: &HashMap<usize, HashMap<usize, Vec<usize>>>,
    fingerprints_to_normi_by_id: &HashMap<usize, HashMap<usize, Vec<usize>>>, fingerprints_to_sig_by_id: &HashMap<usize, HashMap<usize, Vec<usize>>>
) -> Vec<Vec<usize>> {

    let mut classes: Vec<Vec<usize>> = Vec::new();

    for node_id in nodes.keys() {

        let subcircuit = nodes[node_id].get_subcircuit();

        let mut equivalent = false;
        for (_class_ind, class) in classes.iter_mut().enumerate() {

            let representative_id = &class[0];
            let representative_circuit = nodes[representative_id].get_subcircuit();

            let circuits = [subcircuit, representative_circuit];
            let init_norm_fingerprints = [
                &fingerprints_to_normi_by_id[node_id],
                &fingerprints_to_normi_by_id[representative_id]
            ];
            let init_sig_fingerprints = [
                &fingerprints_to_sig_by_id[node_id],
                &fingerprints_to_sig_by_id[representative_id]
            ];
            let normalised_constraints = [
                &normalised_constraints_by_id[node_id],
                &normalised_constraints_by_id[representative_id]
            ];
            let sig_to_normi = [
                &sig_to_normi_by_id[node_id],
                &sig_to_normi_by_id[representative_id]
            ];

            let result = compare_circuits_with_inits(&circuits, Some(&normalised_constraints), Some(&sig_to_normi), Some(&init_norm_fingerprints), Some(&init_sig_fingerprints), false);
            equivalent = result.result;

            if equivalent {
                class.push(*node_id);
                // mapping stuff here
                break;
            }
        }

        if !equivalent {
            classes.push(vec![*node_id])
            // mapping stuff here
        }

    }

    classes
}

fn class_iterated_label_passing<'a, C: Constraint + 'a, S: Circuit<C> + 'a>(
    nodes: &HashMap<usize, DAGNode<'a, C, S>>, initial_labels: HashMap<usize, Vec<usize>>
) -> HashMap<usize, Vec<usize>> {

    let [label_to_nodes] = iterated_label_propagation(
        &[nodes.keys().map(|key| (*key, nodes[key].get_successors())).collect::<HashMap<usize, &Vec<usize>>>()],
        [initial_labels]
    );

    label_to_nodes
}

fn fingerprint_subcircuits<'a, C: Constraint + 'a, S: Circuit<C> + 'a>(
    nodes: &HashMap<usize, DAGNode<'a, C, S>>, 
    normalised_constraints_by_id: &HashMap<usize, Vec<C>>,
    sig_to_normi_by_id: &HashMap<usize, HashMap<usize, Vec<usize>>>
) -> (HashMap<usize, Vec<usize>>, HashMap<usize, HashMap<usize, Vec<usize>>>, HashMap<usize, HashMap<usize, Vec<usize>>>) {

    // Get classes for norms/signals by fingerprinting

    let n = nodes.len();

    let indices: Vec<usize> = nodes.keys().copied().sorted().collect();

    let circuits: Vec<&S> = indices.iter().map(|id| nodes[id].get_subcircuit()).collect();
    let norms_being_fingerprinted: Vec<&Vec<C>> = indices.iter().map(|id| &normalised_constraints_by_id[id]).collect();
    let sig_to_normi: Vec<&HashMap<usize, Vec<usize>>> = indices.iter().map(|id| &sig_to_normi_by_id[id]).collect();
    
    let init_fingerprints_to_normi: Vec<HashMap<usize, Vec<usize>>> = (0..n).into_iter().map(|idx| [(1, (0..norms_being_fingerprinted[idx].len()).into_iter().collect())].into_iter().collect()).collect();
    let init_fingerprints_to_signals: Vec<HashMap<usize, Vec<usize>>> = (0..n).into_iter().map(|idx|
        [(1, circuits[idx].get_output_signals().into_iter().collect()),
        (2, circuits[idx].get_input_signals().into_iter().collect()),
        (3, circuits[idx].get_signals().filter(|&sig| !circuits[idx].signal_is_input(sig) && !circuits[idx].signal_is_output(sig)).collect())
        ].into_iter().collect()
    ).collect();

    let (fingerprints_to_normi, fingerprints_to_signals, _, _) = iterated_refinement(
        &circuits,
        &norms_being_fingerprinted,
        &sig_to_normi,
        &init_fingerprints_to_normi.iter().collect::<Vec<&_>>(),
        &init_fingerprints_to_signals.iter().collect::<Vec<&_>>(),
        true,
        None,
        false,
        false
    );

    // Combine these into a unified node fingerprint
    let mut unifier = Assignment::<Vec<(usize, usize)>, 1>::new(0);
    let node_to_hash: HashMap<usize, Vec<(usize, usize)>> = indices.iter().copied().enumerate().map(|(idx, node_id)|
        (node_id, fingerprints_to_normi[idx].iter().map(|(key, class)| (*key, class.len())).collect())
    ).collect();

    let mut fingerprints_to_nodes: HashMap<usize, Vec<usize>> = HashMap::new();
    for node_id in indices.iter().copied() {
        let new_key = unifier.get_assignment([node_to_hash.get(&node_id).unwrap()]);
        fingerprints_to_nodes.entry(new_key).or_insert_with(|| Vec::new()).push(node_id);
    }

    let fingerprints_to_normi_by_id: HashMap<usize, HashMap<usize, Vec<usize>>> = fingerprints_to_normi.into_iter().enumerate().map(|(idx, label_to_indices)| (indices[idx], label_to_indices)).collect();
    let fingerprints_to_signals_by_id: HashMap<usize, HashMap<usize, Vec<usize>>> = fingerprints_to_signals.into_iter().enumerate().map(|(idx, label_to_indices)| (indices[idx], label_to_indices)).collect();

    (fingerprints_to_nodes, fingerprints_to_normi_by_id, fingerprints_to_signals_by_id)
}