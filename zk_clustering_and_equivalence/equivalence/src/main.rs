use clap::Parser;
use std::array::from_fn;
use std::collections::{HashMap};

use circuits_and_constraints::r1cs::{R1CSData};
use circuits_and_constraints::circuit::{Circuit};
use circuits_and_constraints::utils::{circuit_shuffle, signals_to_constraints_with_them};
use utils::small_utilities::count_ints;

mod argument_parsing;
mod fingerprinting;

use fingerprinting::{iterated_refinement, sanity_check_fingerprints};
use argument_parsing::Args;

fn main() {
    let args = Args::parse();
    if args.test {
        println!("{} {:?}", args.file1path, args.file2path);

        let (r1cs, r1cs_shuffled): (R1CSData, R1CSData) = circuit_shuffle(&args.file1path, 25565, true, true, true, !args.dont_shuffle_internals);
        println!("shuffled");
        // dummy test expand later

        let circuits = [&r1cs, &r1cs_shuffled];

        let init_fingerprints_to_signals: [HashMap<usize, Vec<usize>>; 2] = from_fn(|idx| [
            (1, circuits[idx].get_output_signals().into_iter().collect()),
            (2, circuits[idx].get_input_signals().into_iter().collect()),
            (3, circuits[idx].get_signals().filter(|&sig| !circuits[idx].signal_is_input(sig) && !circuits[idx].signal_is_output(sig)).collect())
        ].into_iter().collect()
        );

        // TODO: look into improving performance of normalise constraints -- Need to try REALLY hard not to clone things I'd imagine
        let normalised_constraints: [_; 2] = from_fn(|idx| circuits[idx].normalise_constraints());
        let init_fingerprints_to_normi: [HashMap<usize, Vec<usize>>; 2] = from_fn(|idx| [(1, (0..normalised_constraints[idx].len()).into_iter().collect())].into_iter().collect());

        let signals_to_normi: [_; 2] = from_fn(|idx| signals_to_constraints_with_them(&normalised_constraints[idx], None, None));

        let (fingerprints_to_normi, fingerprints_to_signals, norm_fingerprints, sig_fingerprints) = iterated_refinement(
            &circuits, &normalised_constraints, &signals_to_normi, init_fingerprints_to_normi, init_fingerprints_to_signals, true, None, false, false
        );

        println!("Norm Sanity Check");
        sanity_check_fingerprints(&norm_fingerprints, &fingerprints_to_normi);
        println!("\nSig Sanity Check");
        sanity_check_fingerprints(&sig_fingerprints, &fingerprints_to_signals);
    } else {
        println!("{} {:?}", args.file1path, args.file2path);
    }
}