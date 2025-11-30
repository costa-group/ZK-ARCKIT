/*
Bare Bones Version

TODO:: Option Parsing
TODO:: Equivalence
TODO:: ...

Step 1: Read R1CS -- DONE
Step 2: Preprocess
Step 3: Convert to Graph
Step 4: Run Clustering
Step 5: Convert to DAG
Step 6: Run Postprocessing

*/
use ansi_term::Colour;
use std::env;

use circuits_and_constraints::r1cs::{R1CSData};
use circuits_and_constraints::circuit::Circuit;
use circuit_graphing::graphing_circuits::shared_signal_graph;
// use circuits_and_constraints::constraint::Constraint;


fn main() {
    let result = start();
    if result.is_err() {
        eprintln!("{}", Colour::Red.paint("previous errors were found"));
        std::process::exit(1);
    } else {
        println!("{}", Colour::Green.paint("Everything went okay, clustered"));
        //std::process::exit(0);
    }
}

fn start() -> Result<(), ()> {
    let args: Vec<String> = env::args().collect();
    let mut r1cs: R1CSData = R1CSData::new();
    r1cs.parse_file(&args[1]);

    let mut graph = shared_signal_graph(&r1cs);

    Result::Ok(())
}
