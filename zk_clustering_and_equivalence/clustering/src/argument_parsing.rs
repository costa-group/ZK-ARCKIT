use clap::{Parser, ValueEnum};

#[derive(Copy, Clone, ValueEnum)]
pub enum GraphBackend {
    GraphRS,
    SingleClustering
}

#[derive(Parser)]
#[command(version, about, long_about = None)]
pub struct Args {
    // filepath to input circuit
    pub filepath: String,

    #[arg(short, long, value_enum)]
    pub graph_backend: GraphBackend

}