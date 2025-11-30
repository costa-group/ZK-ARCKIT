/*
Bare Bones Version

TODO:: Option Parsing
TODO:: Equivalence
TODO:: ...

Step 1: Read R1CS
Step 2: Preprocess
Step 3: Convert to Graph
Step 4: Run Clustering
Step 5: Convert to DAG
Step 6: Run Postprocessing

*/

use circuits_and_constraints::r1cs_reader::{read_r1cs, R1CSData};
use std::env;

fn main() {
    let result = start();
}

fn start() -> Result<(), ()> {
    let args: Vec<String> = env::args().collect();
    let r1cs: R1CSData = read_r1cs(&args[1]).unwrap();

    Result::Ok(())
}
