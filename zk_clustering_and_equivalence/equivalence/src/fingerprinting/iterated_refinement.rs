use std::collections::{HashMap, HashSet};
use std::array::from_fn;
use std::hash::Hash;
use std::cmp::Eq;

use circuits_and_constraints::circuit::Circuit;
use circuits_and_constraints::constraint::Constraint;
use utils::assignment::Assignment;

pub fn iterated_refinement<C: Constraint, S: Circuit<C>, const N: usize>(
        circuits: &[&S; N],
        signal_to_normi: &[&Vec<Vec<usize>>; N],
        init_fingerprints_to_normi: [HashMap<usize, Vec<usize>>; N],
        init_fingerprints_to_signals: [HashMap<usize, Vec<usize>>; N],
        start_with_constraints: bool,
        per_iteration_postprocessing: Option<fn(&mut [HashMap<usize, (usize, usize)>; N], &mut [HashMap<(usize, usize), Vec<usize>>;N], &mut [HashMap<usize, (usize, usize)>; N], &mut [HashMap<(usize, usize), Vec<usize>>; N], &mut [HashMap<(usize, usize), usize>; N] ) -> ()>,
        return_index_to_fingerprint: bool,
        strict_unique: bool
    ) -> ([HashMap<usize, Vec<usize>>; N], [HashMap<usize, Vec<usize>>; N], [HashMap<usize, usize>; N], [HashMap<usize, usize>; N]) {

    let signal_sets: [HashSet<usize>; N] = from_fn(|idx| circuits[idx].get_signals().collect());
    let norms_being_fingerprinted: [&Vec<C>; N] = from_fn(|idx| circuits[idx].get_normalised_constraints());

    let mut norm_fingerprints: [HashMap<usize, (usize, usize)>; N] = from_fn(|_| HashMap::new());
    let mut sig_fingerprints: [HashMap<usize, (usize, usize)>; N] = from_fn(|_| HashMap::new());

    let (init_num_singular_norm_fingerprints, mut norms_to_update) = iterated_refinement_preprocessing(&init_fingerprints_to_normi, &mut norm_fingerprints, !start_with_constraints as usize + 1, strict_unique);
    let (init_num_singular_sig_fingerprints, mut signals_to_update) = iterated_refinement_preprocessing(&init_fingerprints_to_signals, &mut sig_fingerprints, start_with_constraints as usize + 1, strict_unique);

    fn exit_postprocessing<const N: usize >(index_to_label_and_roundnum: &[HashMap<usize, (usize, usize)>; N]) -> ([HashMap<usize, Vec<usize>>;N], [HashMap<usize, usize>;N]) {
            let mut label_to_indices: [HashMap<usize, Vec<usize>>;N] = from_fn(|_| HashMap::new());
            let mut index_to_label: [HashMap<usize, usize>;N] = from_fn(|_| HashMap::new());
            
            for (idx, hm) in index_to_label_and_roundnum.iter().enumerate() {
                for index in hm.keys() {
                    let label = hm.get(index).unwrap().1;
                    index_to_label[idx].insert(*index, label);
                    label_to_indices[idx].entry(label).or_insert(Vec::new()).push(*index)
                }
            }

            (label_to_indices, index_to_label)
        }

    let (mut any_norms_to_update, mut any_sigs_to_update): (bool, bool) = (norms_to_update.iter().all(|arr| arr.len() > 0), signals_to_update.iter().all(|arr| arr.len() > 0));

    if !any_norms_to_update && !any_sigs_to_update {
        // TODO: these might not line up at first !!

        let (return_fingerprints_to_normi, return_norm_fingerprints) = exit_postprocessing(&norm_fingerprints);
        let (return_fingerprints_to_signals, return_sig_fingerprints) = exit_postprocessing(&sig_fingerprints);

        (return_fingerprints_to_normi, return_fingerprints_to_signals, return_norm_fingerprints, return_sig_fingerprints)
    } else {

        let (mut previous_distinct_norm_fingerprints, mut previous_distinct_sig_fingerprints): ([usize; N], [usize; N]) = (from_fn(|idx| init_fingerprints_to_normi[idx].len()), from_fn(|idx| init_fingerprints_to_signals[idx].len()));
        let (mut break_on_next_norm, mut break_on_next_signal): (bool, bool) = (false, false);

        let (mut norm_assignment, mut signal_assignment) = (Assignment::<C::Fingerprint<(usize, usize)>, 1>::new(init_num_singular_norm_fingerprints), Assignment::<S::SignalFingerprint<(usize, usize)>, 1>::new(init_num_singular_sig_fingerprints));

        let mut fingerprints_to_normi: [HashMap<(usize, usize), Vec<usize>>;N] = from_fn(|_| HashMap::new());
        let mut fingerprints_to_signals: [HashMap<(usize, usize), Vec<usize>>;N] = from_fn(|_| HashMap::new());

        let mut num_singular_norm_fingerprints: HashMap<usize, usize> = [(!start_with_constraints as usize + 1, init_num_singular_norm_fingerprints)].into_iter().collect();
        let mut num_singular_sig_fingerprints: HashMap<usize, usize> = [(!start_with_constraints as usize + 1, init_num_singular_sig_fingerprints)].into_iter().collect();

        let (mut prev_fingerprints_to_normi_count, mut prev_fingerprints_to_sig_count): ([HashMap<(usize, usize), usize>; N], [HashMap<(usize, usize), usize>; N]) = (from_fn(|_| HashMap::new()), from_fn(|_| HashMap::new()));
        let (mut prev_fingerprints_to_normi, mut prev_fingerprints_to_sig): ([HashMap<(usize, usize), Vec<usize>>; N], [HashMap<(usize, usize), Vec<usize>>; N]) = (from_fn(|_| HashMap::new()), from_fn(|_| HashMap::new()));
        let mut prev_normi_to_fingerprints: [HashMap<usize, (usize, usize)>; N] = from_fn(|idx| (0..norms_being_fingerprinted[idx].len()).into_iter().map(|normi| (normi, *norm_fingerprints[idx].get(&normi).unwrap())).collect());
        let mut prev_sig_to_fingerprints: [HashMap<usize, (usize, usize)>; N] = from_fn(|idx| signal_sets[idx].iter().copied().map(|sig| (sig, *sig_fingerprints[idx].get(&sig).unwrap())).collect());

        let get_to_update_normi = |normi: usize, idx: usize| norms_being_fingerprinted[idx][normi].signals().into_iter().collect::<Vec<_>>();
        let get_to_update_signal = |sig: usize, idx: usize| signal_to_normi[idx][sig].iter().copied().collect::<Vec<_>>();

        // this lets 0 be some unique check round_num value.
        let mut round_num = 3;
        let mut assignment_offset: usize;

        fn loop_iteration<C: Constraint, S: Circuit<C>, const N: usize, H: Hash + Eq + Clone>(
            circuits: &[&S; N], norms_being_fingerprinted: &[&Vec<C>; N], round_num: usize, strict_unique: bool,
            indices_to_update: [HashSet<usize>; N], signal_to_normi: &[&Vec<Vec<usize>>; N],
            per_iteration_postprocessing: Option<fn(&mut [HashMap<usize, (usize, usize)>; N], &mut [HashMap<(usize, usize), Vec<usize>>;N], &mut [HashMap<usize, (usize, usize)>; N], &mut [HashMap<(usize, usize), Vec<usize>>; N], &mut [HashMap<(usize, usize), usize>; N] ) -> ()>,
            get_fingerprint: impl Fn(usize, &S, &Vec<C>, &HashMap<usize, (usize, usize)>, &HashMap<usize, (usize, usize)>, &Vec<Vec<usize>>) -> H,
            last_loop: bool, assignment: &mut Assignment<H, 1>, get_to_update: impl Fn(usize, usize) -> Vec<usize>,
            index_to_label: &mut [HashMap<usize, (usize, usize)>; N], label_to_indices: &mut [HashMap<(usize, usize), Vec<usize>>;N], 
            other_index_to_label: &mut [HashMap<usize, (usize, usize)>; N],
            prev_index_to_label: &mut [HashMap<usize, (usize, usize)>; N], prev_label_to_indices: &mut [HashMap<(usize, usize), Vec<usize>>; N], prev_label_to_indices_count: &mut [HashMap<(usize, usize), usize>; N],
            prev_other_index_to_label: &mut [HashMap<usize, (usize, usize)>; N],
            prev_distinct_labels: &mut [usize; N], num_singular_labels: &mut HashMap<usize, usize>, num_other_singular_labels: &mut HashMap<usize, usize>
        ) -> (bool, [HashSet<usize>; N]) {
            for (idx, to_update) in indices_to_update.into_iter().enumerate() {
                for index in to_update {
                    
                    let fingerprint = get_fingerprint(index, circuits[idx], norms_being_fingerprinted[idx], &other_index_to_label[idx], &prev_index_to_label[idx], &signal_to_normi[idx]);
                    let new_hash = assignment.get_assignment([fingerprint]);
                    index_to_label[idx].insert(index, (round_num, new_hash));
                    label_to_indices[idx].entry((round_num, new_hash)).or_insert(Vec::new()).push(index);

                }
            }

            if let Some(f) = per_iteration_postprocessing {
                f(index_to_label, label_to_indices, prev_index_to_label, prev_label_to_indices, prev_label_to_indices_count);
            }

            let break_on_next_loop = (0..N).into_iter().all(|idx| num_singular_labels[&(idx - 2)] + label_to_indices[idx].len() == prev_distinct_labels[idx]);
            *prev_distinct_labels = from_fn(|idx| num_singular_labels[&(idx - 2)] + label_to_indices[idx].len());

            if !last_loop {
                let other_signals_to_update: [HashSet<usize>; N];
                (*assignment, *prev_other_index_to_label, other_signals_to_update) = fingerprint_switch(
                    &assignment, index_to_label, label_to_indices, num_singular_labels, prev_index_to_label, prev_label_to_indices, prev_label_to_indices_count, get_to_update,
                    other_index_to_label, num_other_singular_labels, round_num, strict_unique
                );
                *label_to_indices = from_fn(|_| HashMap::new());
                (break_on_next_loop, other_signals_to_update)
            } else {
                (break_on_next_loop, from_fn(|_| HashSet::new()))
            }
        }

        let get_norm_fingerprint = |index: usize, _: &S, norms_being_fingerprinted: &Vec<C>, other_index_to_label: &HashMap<usize, (usize, usize)>, _: &HashMap<usize, (usize, usize)>, _: &Vec<Vec<usize>>|
            norms_being_fingerprinted[index].fingerprint(other_index_to_label);

        let get_sig_fingerprint = |index: usize, circ: &S, norms_being_fingerprinted: &Vec<C>, other_index_to_label: &HashMap<usize, (usize, usize)>, prev_index_to_label: &HashMap<usize, (usize, usize)>, signal_to_normi: &Vec<Vec<usize>>|
            circ.fingerprint_signal(index, norms_being_fingerprinted, other_index_to_label, prev_index_to_label, signal_to_normi);

        // handle starting with signals
        if !start_with_constraints {
            (break_on_next_signal, norms_to_update) = loop_iteration(circuits, &norms_being_fingerprinted, round_num, strict_unique,
                signals_to_update, signal_to_normi, per_iteration_postprocessing, get_sig_fingerprint, 
                !break_on_next_norm && !break_on_next_signal, &mut signal_assignment, get_to_update_signal,
                &mut sig_fingerprints, &mut fingerprints_to_signals, &mut norm_fingerprints,
                &mut prev_sig_to_fingerprints, &mut prev_fingerprints_to_sig, &mut prev_fingerprints_to_sig_count,
                &mut prev_normi_to_fingerprints, &mut previous_distinct_sig_fingerprints, 
                &mut num_singular_sig_fingerprints, &mut num_singular_norm_fingerprints
            );
            any_norms_to_update = norms_to_update.iter().all(|arr| arr.len() > 0);
            round_num += 1;
        }

        while any_norms_to_update {

            // TODO: make a single loop with options? maybe the small differences are enough -- looks like just another switch function though.
            
            // loop for norms
            // norms_being_fingerprinted[idx][normi].fingerprint(&sig_fingerprints[idx]);
            if break_on_next_norm {break;}
            (break_on_next_norm, signals_to_update) = loop_iteration(circuits, &norms_being_fingerprinted, round_num, strict_unique,
                norms_to_update, signal_to_normi, per_iteration_postprocessing, get_norm_fingerprint, 
                !break_on_next_norm && !break_on_next_signal, &mut norm_assignment, get_to_update_normi,
                &mut norm_fingerprints, &mut fingerprints_to_normi, &mut sig_fingerprints,
                &mut prev_normi_to_fingerprints, &mut prev_fingerprints_to_normi, &mut prev_fingerprints_to_normi_count,
                &mut prev_sig_to_fingerprints, &mut previous_distinct_norm_fingerprints, 
                &mut num_singular_norm_fingerprints, &mut num_singular_sig_fingerprints
            );
            any_sigs_to_update = signals_to_update.iter().all(|arr| arr.len() > 0);
            round_num += 1;

            if !any_sigs_to_update || break_on_next_signal {break;}
            //let fingerprint = circuits[idx].fingerprint_signal(signal, &norms_being_fingerprinted[idx], &norm_fingerprints[idx], &prev_sig_to_fingerprints[idx], &signal_to_normi[idx]);
            (break_on_next_signal, norms_to_update) = loop_iteration(circuits, &norms_being_fingerprinted, round_num, strict_unique,
                signals_to_update, signal_to_normi, per_iteration_postprocessing, get_sig_fingerprint, 
                !break_on_next_norm && !break_on_next_signal, &mut signal_assignment, get_to_update_signal,
                &mut sig_fingerprints, &mut fingerprints_to_signals, &mut norm_fingerprints,
                &mut prev_sig_to_fingerprints, &mut prev_fingerprints_to_sig, &mut prev_fingerprints_to_sig_count,
                &mut prev_normi_to_fingerprints, &mut previous_distinct_sig_fingerprints, 
                &mut num_singular_sig_fingerprints, &mut num_singular_norm_fingerprints
            );
            any_norms_to_update = norms_to_update.iter().all(|arr| arr.len() > 0);
            round_num += 1;

            
        };

        let (return_fingerprints_to_normi, return_norm_fingerprints) = exit_postprocessing(&norm_fingerprints);
        let (return_fingerprints_to_signals, return_sig_fingerprints) = exit_postprocessing(&sig_fingerprints);

        (return_fingerprints_to_normi, return_fingerprints_to_signals, return_norm_fingerprints, return_sig_fingerprints)
    }
} 

fn iterated_refinement_preprocessing<const N: usize>(label_to_indices: &[HashMap<usize, Vec<usize>>; N], index_to_label: &mut [HashMap<usize, (usize, usize)>; N], init_round: usize, strict_unique: bool)
 -> (usize, [HashSet<usize>; N]) {

    let mut nonsingular_keys: [Vec<usize>; N] = from_fn(|_| Vec::new());
    let mut singular_remapping = Assignment::<usize, 1>::new(0);

    for index in 0..N {
        for label in label_to_indices[index].keys() {
            if key_is_unique(label, index, label_to_indices, strict_unique) {
                index_to_label[index].insert(label_to_indices[index][label][0], (init_round, singular_remapping.get_assignment([*label])));
            } else {
                nonsingular_keys[index].push(*label)
            }
        }
    }

    let mut to_update: [HashSet<usize>; N] = from_fn(|_| HashSet::new());
    let num_singular = singular_remapping.len();

    let mut nonsingular_remapping = Assignment::<usize, 1>::new(num_singular);

    for (idx, nonsingular_vec) in nonsingular_keys.into_iter().enumerate() {
        for label in nonsingular_vec.into_iter() {

            to_update[idx].extend(&label_to_indices[idx][&label]);
            for index in label_to_indices[idx][&label].iter().copied() { index_to_label[idx].insert(index, (init_round, nonsingular_remapping.get_assignment([label]))); }
        }
    }

    (num_singular, to_update)
 }

fn key_is_unique<H: Hash + Eq, const N: usize>(label: &H, index: usize, label_to_indices: &[HashMap<H, Vec<usize>>; N], strict: bool) -> bool {
    if strict {
        (0..N).into_iter().all(|idx| label_to_indices[idx].get(label).unwrap_or(&Vec::new()).len() == 1)
    } else {
        label_to_indices[index].get(label).unwrap_or(&Vec::new()).len() == 1
    }
}

fn fingerprint_switch<const N: usize, H: Hash + Eq + Clone>(
    assignment: &Assignment<H, 1>, fingerprints: &mut [HashMap<usize, (usize, usize)>; N], fingerprints_to_index: &mut [HashMap<(usize, usize), Vec<usize>>;N], num_singular_fingerprints: &mut HashMap<usize, usize>,
    prev_fingerprints: &[HashMap<usize, (usize, usize)>; N], prev_fingerprints_to_index: &mut [HashMap<(usize, usize), Vec<usize>>; N], prev_fingerprints_to_index_count: &mut [HashMap<(usize, usize), usize>; N], 
    get_to_update: impl Fn(usize, usize) -> Vec<usize>, other_fingerprints: &[HashMap<usize, (usize, usize)>; N], other_num_singular: &HashMap<usize, usize>, round_num: usize, strict: bool
) -> (Assignment<H, 1>, [HashMap<usize, (usize, usize)>; N], [HashSet<usize>; N]) {
    // TODO: reset Assignment outside -- with passed offset 

    let mut next_to_update: [HashSet<usize>; N] = from_fn(|_| HashSet::new());
    let mut add_to_update = |index: usize, idx: usize| next_to_update[idx].extend(get_to_update(index, idx).into_iter());

    let mut nonsingular_fingerprints: [Vec<(usize, usize)>; N] = from_fn(|_| Vec::new());

    let mut singular_renaming = Assignment::<(usize, usize), 1>::new(*num_singular_fingerprints.get(&(round_num-2)).unwrap());
    singular_renaming.drop_inverse();

    for idx in 0..N {
        for label in fingerprints_to_index[idx].keys() {
            if key_is_unique(label, idx, fingerprints_to_index, strict) {

                let index = fingerprints_to_index[idx].get(label).unwrap()[0];
                fingerprints[idx].insert(index, (round_num, singular_renaming.get_assignment([*label])));
                add_to_update(index, idx);

                let prev_fingerprint = prev_fingerprints[idx].get(&index).unwrap();

                if round_num > 4 && prev_fingerprint.0 >= 3 {
                    prev_fingerprints_to_index_count[idx].entry(*prev_fingerprint).and_modify(|val| *val -= 1);
                    if *prev_fingerprints_to_index_count[idx].get(prev_fingerprint).unwrap() == 0 {
                        prev_fingerprints_to_index[idx].remove(prev_fingerprint);
                        prev_fingerprints_to_index_count[idx].remove(prev_fingerprint);
                    }
                }

            } else {
                nonsingular_fingerprints[idx].push(*label);
            }
        }
    }

    num_singular_fingerprints.insert(round_num, *num_singular_fingerprints.get(&(round_num-2)).unwrap() + singular_renaming.len() );

    let mut new_assignment = Assignment::<H, 1>::new(*num_singular_fingerprints.get(&round_num).unwrap());

    // now we collect all the labels that have actually changed by comparing the old/new sets
    // TODO: do this better, so not comparing each class multiple times
    // TODO: when the prev_fingerprint was from a very old round -- this struggles
    for (idx, nonsingular_batch) in nonsingular_fingerprints.into_iter().enumerate() {
        for label in nonsingular_batch.into_iter() {

            let new_key = new_assignment.get_assignment(assignment.get_inv_assignment(label.1).unwrap());
            let new_label = (round_num, new_key);

            prev_fingerprints_to_index[idx].insert(new_label, fingerprints_to_index[idx].remove(&label).unwrap());

            let class: &Vec<usize> = prev_fingerprints_to_index[idx].get(&new_label).unwrap();
            prev_fingerprints_to_index_count[idx].insert(new_label, class.len());

            for index in class.into_iter().copied() {
                fingerprints[idx].insert(index, new_label);
            }

            let mut labels_to_delete: Vec<(usize, usize)> = Vec::new();
            let an_old_key: &(usize, usize) = prev_fingerprints[idx].get(&class[0]).unwrap();

            if round_num <= 4 || an_old_key.0 < 3 {
                for index in class.into_iter().copied() {add_to_update(index, idx)};
            } else {
                if *prev_fingerprints_to_index_count[idx].get(an_old_key).unwrap() == class.len() && class == prev_fingerprints_to_index[idx].get(an_old_key).unwrap() {
                    // class has not changed, delete old info as it is redundant
                    labels_to_delete.push(*an_old_key);
                } else {
                    // class has changed -- need to check these on next iteration, need to update index counts / delete if empty
                    for index in class.into_iter().copied() {

                        add_to_update(index, idx);

                        let index_old_key = prev_fingerprints[idx].get(&index).unwrap();
                        prev_fingerprints_to_index_count[idx].entry(*index_old_key).and_modify(|val| *val -= 1);

                        if *prev_fingerprints_to_index_count[idx].get(index_old_key).unwrap() == 0 {
                            labels_to_delete.push(*index_old_key);
                        }
                    }
                }
            }

            // deleting here because of class borrow checking -- specifically the for index in class.into_iter() loop will always cause problems -- 
            for label_to_delete in labels_to_delete.iter() {
                prev_fingerprints_to_index[idx].remove(label_to_delete);
                prev_fingerprints_to_index_count[idx].remove(label_to_delete);
            }
        }
    }

    let new_prev_other_index_to_label: [HashMap<usize, (usize, usize)>; N] = from_fn(|idx| next_to_update[idx].iter().map(|index| (*index, *other_fingerprints[idx].get(index).unwrap())).collect());

    (new_assignment, new_prev_other_index_to_label, next_to_update)
}