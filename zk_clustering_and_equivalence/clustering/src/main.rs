/*
Bare Bones Version

TODO:: Option Parsing
TODO:: Equivalence
TODO:: ...

Step 1: Read R1CS -- DONE
Step 2: Preprocess
Step 3: Convert to Graph -- DONE
Step 4: Run Clustering -- DONE
Step 5: Convert to DAG -- DONE
Step 6: Run Postprocessing

*/
use ansi_term::Colour;
use serde::{Serialize};
use std::fs::File;
use std::io::{BufReader, BufWriter};
use std::path::Path;
use std::io::Write;
use std::collections::HashMap;
use std::error::Error;
use std::time::Instant;
use clap::Parser;

mod leiden_clustering;
mod argument_parsing;

use argument_parsing::{Args, GraphBackend};
use leiden_clustering::{CanLeiden};
use circuits_and_constraints::r1cs::{R1CSData};
use circuits_and_constraints::circuit::Circuit;
use circuit_graphing::graphing_circuits::{shared_signal_graph_single_clustering, shared_signal_graph_graphrs};
use circuit_graphing::directed_acyclic_graph::{NodeInfo};
use circuit_graphing::directed_acyclic_graph::dag_from_partition::dag_from_partition;
use circuit_graphing::directed_acyclic_graph::dag_postprocessing::{merge_passthrough};
// use circuits_and_constraints::constraint::Constraint;




fn main() {
    let args = Args::parse();
    let result = start(args);
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

fn start(args: Args) -> Result<(), Box<dyn Error>> {
    let mut r1cs: R1CSData = R1CSData::new();
    r1cs.parse_file(&args.filepath);

    let backend = args.graph_backend;

    let graph_construction_timer = Instant::now();
    let graph: Box<dyn CanLeiden> = 
        match backend {
            GraphBackend::GraphRS => {
                Box::new(shared_signal_graph_graphrs(&r1cs))
            }
            GraphBackend::SingleClustering => {
                Box::new(shared_signal_graph_single_clustering(&r1cs))
            }
        };
    println!("Graph Construction Took: {:?}", graph_construction_timer.elapsed());


    let partition_timer = Instant::now();
    let edge_count = graph.num_edges() as f64;
    let partition: Vec<Vec<usize>> = graph.get_partition(f64::log2(edge_count), 5, 25565);
    println!("Clustering took: {:?}", partition_timer.elapsed());

    let mut dagnodes = dag_from_partition(&r1cs, partition);
    merge_passthrough(&r1cs, &mut dagnodes);

    let dagnode_info: Vec<NodeInfo> = dagnodes.into_values().map(|node| node.to_json(None, None)).collect();
    let result = ResultInfo {seed: 0, timing: HashMap::new(), data: HashMap::new(), nodes: dagnode_info, equivalence: HashMap::new()};

    write_output_into_file("testing.json", &result)
}
