/*
Bare Bones Version

TODO:: Option Parsing
TODO:: Equivalence
TODO:: ...

Step 1: Read R1CS -- DONE
Step 2: Preprocess
Step 3: Convert to Graph -- DONE
Step 4: Run Clustering -- DONE
Step 5: Convert to DAG
Step 6: Run Postprocessing

*/
use ansi_term::Colour;
use std::env;
use serde::{Serialize};
use std::fs::File;
use std::io::{BufReader, BufWriter};
use std::path::Path;
use std::io::Write;
use std::collections::HashMap;
use std::error::Error;

mod leiden_clustering;

use leiden_clustering::leiden_clustering;
use circuits_and_constraints::r1cs::{R1CSData};
use circuits_and_constraints::circuit::Circuit;
use circuit_graphing::graphing_circuits::shared_signal_graph;
use circuit_graphing::directed_acyclic_graph::{DAGNode, NodeInfo};
use circuit_graphing::directed_acyclic_graph::dag_from_partition::dag_from_partition;
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

#[derive(Serialize)]
pub struct ResultInfo{
    seed: usize,
    timing: HashMap<Box<str>, f64>, //ids of the constraints
    data: HashMap<Box<str>, Box<str>>,
    nodes: Vec<NodeInfo>,
    equivalence: HashMap<Box<str>, Vec<Vec<usize>>>
}

fn write_output_into_file<P: AsRef<Path>>(path: P, result: &ResultInfo) -> Result<(), Box<dyn Error>> {
    // Open the file in read-only mode with buffer.

    let file = File::create(path)?;
    let mut writer = BufWriter::new(file);

    // Write the result.
    let value = serde_json::to_string_pretty(result)?;
    writer.write(value.as_bytes())?;
    writer.flush()?;
    Ok(())
}


fn start() -> Result<(), Box<dyn Error>> {
    let args: Vec<String> = env::args().collect();
    let mut r1cs: R1CSData = R1CSData::new();
    r1cs.parse_file(&args[1]);

    let graph = shared_signal_graph(&r1cs);
    let edge_count: f64 = graph.edge_count() as f64;

    let partition = leiden_clustering(graph, f64::log2(edge_count), 5, 25565);
    let dagnodes = dag_from_partition(&r1cs, partition);

    println!("here");

    let dagnode_info: Vec<NodeInfo> = dagnodes.into_values().map(|node| node.to_json(None, None)).collect();
    let result: ResultInfo = ResultInfo {seed: 0, timing: HashMap::new(), data: HashMap::new(), nodes: dagnode_info, equivalence: HashMap::new()};

    write_output_into_file("testing.json", &result)
}
