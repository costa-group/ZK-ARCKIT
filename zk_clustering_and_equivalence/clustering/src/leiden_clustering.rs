use single_clustering::network::CSRNetwork;
use single_clustering::community_search::leiden::{LeidenOptimizer, LeidenConfig};
use single_clustering::community_search::leiden::partition::{RBConfigurationPartition, VertexPartition};
use single_clustering::network::grouping::{VectorGrouping};

pub fn leiden_clustering(
    graph: CSRNetwork<f64, f64>,
    target: f64,
    max_iterations: usize,
    seed: u64
) -> Vec<Vec<usize>> {


    let config = LeidenConfig {
        max_iterations: max_iterations,
        tolerance: 1e-6,
        seed: Some(seed),
        ..Default::default()
    };

    // Initialize the optimizer
    let mut optimizer = LeidenOptimizer::new(config);

    let resolution: f64 = (graph.edge_count() << 1) as f64 / target.powi(2);

    let mut partition: RBConfigurationPartition<f64, VectorGrouping> = RBConfigurationPartition::new_singleton(graph, resolution);

    // Find communities using modularity optimization
    let _ = optimizer.optimize_single_partition::<f64, VectorGrouping, RBConfigurationPartition<f64, VectorGrouping>>(&mut partition, None);

    println!("{:?}", partition.get_communities());

    partition.get_communities()
}