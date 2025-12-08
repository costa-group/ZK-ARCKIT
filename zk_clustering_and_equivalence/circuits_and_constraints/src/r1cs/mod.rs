
use num_bigint::{BigInt};
use std::collections::{HashMap};

mod r1cs_reader;
mod circuit_implementation;
mod constraint_implementation;

//This struct contained all the sections
pub struct HeaderData {
    pub field: BigInt,
    pub field_size: usize,
    pub total_wires: usize,
    pub public_outputs: usize,
    pub public_inputs: usize,
    pub private_inputs: usize,
    pub number_of_labels: usize,
    pub number_of_constraints: usize,
}


type R1CSConstraint = (HashMap<usize, BigInt>, HashMap<usize, BigInt>, HashMap<usize, BigInt>);
type ConstraintList = Vec<R1CSConstraint>;
type SignalList = Vec<usize>;

pub type CustomGatesUsedData = Vec<(String, Vec<BigInt>)>;
pub type CustomGatesAppliedData = Vec<(usize, Vec<usize>)>;

pub struct R1CSData {
    header_data: HeaderData,
    pub constraints: ConstraintList,
    signals: SignalList,
    custom_gates: bool,
    custom_gates_used_data: Option<CustomGatesUsedData>,
    custom_gates_applied_data: Option<CustomGatesAppliedData>,
}