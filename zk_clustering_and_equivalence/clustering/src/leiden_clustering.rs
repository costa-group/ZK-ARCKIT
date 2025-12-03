use single_clustering::network::CSRNetwork;
use single_clustering::community_search::leiden::{LeidenOptimizer, LeidenConfig};
use single_clustering::community_search::leiden::partition::{RBConfigurationPartition, VertexPartition};
use single_clustering::network::grouping::{VectorGrouping};
use graphrs::Graph;
use graphrs::algorithms::community::leiden::{leiden, QualityFunction};


pub trait CanLeiden {
    fn num_edges(&self) -> usize;
    fn get_partition(self: Box<Self>, target: f64, max_iterations: usize, seed: u64) -> Vec<Vec<usize>>;
}

impl CanLeiden for CSRNetwork<f64, f64> {
    fn num_edges(&self) -> usize {
        self.edge_count()
    }

    fn get_partition(self: Box<Self>, target: f64, max_iterations: usize, seed: u64) -> Vec<Vec<usize>> {
        let config = LeidenConfig {
            max_iterations: max_iterations,
            tolerance: 1e-6,
            seed: Some(seed),
            ..Default::default()
        };

        // Initialize the optimizer
        let mut optimizer = LeidenOptimizer::new(config);

        let resolution: f64 = (self.num_edges() << 1) as f64 / target.powi(2);

        let mut partition: RBConfigurationPartition<f64, VectorGrouping> = RBConfigurationPartition::new_singleton(*self, resolution);

        // Find communities using modularity optimization
        let _ = optimizer.optimize_single_partition::<f64, VectorGrouping, RBConfigurationPartition<f64, VectorGrouping>>(&mut partition, None);

        partition.get_communities()
    }
}

impl CanLeiden for Graph<usize, usize> {
    fn num_edges(&self) -> usize {
        self.number_of_edges()
    }

    fn get_partition(self: Box<Self>, target: f64, _max_iterations: usize, _seed: u64) -> Vec<Vec<usize>> {
        let resolution: f64 = (self.num_edges() << 1) as f64 / target.powi(2);
        let result = leiden(&self, true, QualityFunction::Modularity, Some(resolution), None, None);

        result.unwrap().into_iter().map(|set| set.into_iter().collect()).collect()
    }
}