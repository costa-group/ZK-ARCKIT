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

    #[arg(short, default_value="./")]
    pub out_directory: String,

    #[arg(short, long, conflicts_with="target_size")]
    // specifies the rsolution used in the modularity-based clustering algorithms
    pub resolution: Option<f64>,

    #[arg(short='x', long, conflicts_with="resolution")]
    // specifies the target_size used in the modularity-based clustering algorithms
    pub target_size: Option<f64>,

    #[arg(short, long, value_enum, default_value_t=GraphBackend::GraphRS)]
    pub graph_backend: GraphBackend 
}