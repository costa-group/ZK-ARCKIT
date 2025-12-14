use std::collections::HashMap;

use circuits_and_constraints::constraint::Constraint;
use circuits_and_constraints::circuit::Circuit;
use equivalence::compare_circuits::compare_circuits_with_inits;

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

// fingerprint_subcircuit

// naive_equivalency_analysis