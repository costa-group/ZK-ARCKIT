
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

impl R1CSData {
    pub fn new() -> Self {
        R1CSData {
            header_data: HeaderData {
                field: BigInt::from(0),
                field_size: 0,
                total_wires: 0,
                public_outputs: 0,
                public_inputs: 0,
                private_inputs: 0,
                number_of_labels: 0,
                number_of_constraints: 0,
            },
            custom_gates: false,
            constraints: ConstraintList::new(),
            signals: SignalList::new(),
            custom_gates_used_data: None,
            custom_gates_applied_data: None,
        }
    }
}