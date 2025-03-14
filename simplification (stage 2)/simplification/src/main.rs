mod constraint_simplification;
mod non_linear_simplification;
use num_bigint_dig::BigInt;
use serde::Deserialize;
use std::collections::{HashSet, LinkedList, HashMap};
use circom_algebra::algebra::AIRConstraint;
use circom_algebra::algebra::Substitution;
use circom_algebra::algebra::ArithmeticExpression;
use circom_algebra::constraint_storage::AIRConstraintStorage;
use crate::constraint_simplification::simplification;

use std::env;


use std::error::Error;
use std::fs::File;
use std::io::BufReader;
use std::path::Path;


use ansi_term::Colour;

pub type C = AIRConstraint<usize>;
pub type S = Substitution<usize>;
pub type A = ArithmeticExpression<usize>;

#[derive(Deserialize, Debug)]
struct LinearInfo{
   witness: usize,
   coeff: String, 
}

#[derive(Deserialize, Debug)]
struct MulInfo{
    witness1: usize,
    witness2: usize,
    coeff: String
}


#[derive(Deserialize, Debug)]
struct ConstraintInfo{
    linear: Vec<LinearInfo>,
    mul: Vec<MulInfo>,
    constant: String
}

#[derive(Deserialize, Debug)]
struct CircuitInfo{
    constraints: Vec<ConstraintInfo>,
    inputs: Vec<usize>,
    outputs: Vec<usize>,
    number_of_signals: usize,
    //field: String
}



fn read_air_constraint_info_from_file<P: AsRef<Path>>(path: P) -> Result<CircuitInfo, Box<dyn Error>> {
    // Open the file in read-only mode with buffer.
    let file = File::open(path)?;
    let reader = BufReader::new(file);

    // Read the JSON contents of the file as an instance of `StructureInfo`.
    let u: CircuitInfo = serde_json::from_reader(reader)?;

    // Return the `StructureInfo`.
    Ok(u)
}



struct ProcessedCircuit{
    storage: AIRConstraintStorage,
    linear: LinkedList<C>,
    forbidden: HashSet<usize>, 
    no_labels: usize,
    field: BigInt
}

fn process_air_constraint(cinfo: ConstraintInfo) -> C{
    let mut linear = HashMap::new();
    let mut muls = HashMap::new();

    let to_bi_constant = cinfo.constant.parse::<BigInt>().unwrap();
    if to_bi_constant != BigInt::from(0){
        linear.insert(0, to_bi_constant);
    }
    for lin_info in cinfo.linear{
        let to_bi_coef = lin_info.coeff.parse::<BigInt>().unwrap();
        linear.insert(lin_info.witness + 1, to_bi_coef);
    }

    for muls_info in cinfo.mul{
        let to_bi_coef = muls_info.coeff.parse::<BigInt>().unwrap();

        let ord_signals = if muls_info.witness1 < muls_info.witness2{
            (muls_info.witness1 + 1, muls_info.witness2 + 1)
        } else {
            (muls_info.witness2 + 1, muls_info.witness1 + 1)
        };
        muls.insert(ord_signals, to_bi_coef);
    }

    AIRConstraint::new(muls, linear)    
}


fn move_constraint_info_to_storage(info: CircuitInfo) ->ProcessedCircuit{
    let mut storage = AIRConstraintStorage::new();
    let mut linear = LinkedList::new();
    let mut forbidden = HashSet::new();
    let mut signals = HashSet::new();
    
    for constraint_info in info.constraints{
        let processed_constraint = process_air_constraint(constraint_info);
        let signals_constraint = C::take_cloned_signals(&processed_constraint);
        signals.extend(signals_constraint);
        if C::is_linear(&processed_constraint){
            linear.push_back(processed_constraint);
        } else{
            storage.add_constraint(processed_constraint);
        }
    }

    for out in info.outputs{
        forbidden.insert(out);
    }
    let field = "21888242871839275222246405745257275088548364400416034343698204186575808495617";
    let to_bi_field = field.parse::<BigInt>().unwrap();
    if signals.len() != info.number_of_signals{
        println!("Different number of signals: Real -> {}, Given -> {}", signals.len(), info.number_of_signals);
    }
    ProcessedCircuit{
        storage, 
        linear, 
        forbidden,
        field: to_bi_field,
        no_labels: info.number_of_signals
    }
}

fn main() {
    let result = start();
    if result.is_err() {
        eprintln!("{}", Colour::Red.paint("previous errors were found"));
        std::process::exit(1);
    } else {
        println!("{}", Colour::Green.paint("Everything went okay, circom safe"));
        //std::process::exit(0);
    }
}

fn start() -> Result<(), ()> {
    use std::sync::Arc;
    let args: Vec<String> = env::args().collect();
    let circuit = read_air_constraint_info_from_file(&args[1]).unwrap();
    let proc_circuit = move_constraint_info_to_storage(circuit);
    
    
    let (new_constraints, signals) = simplification(
        proc_circuit.linear,
        proc_circuit.storage,
        Arc::new(proc_circuit.forbidden),
        proc_circuit.no_labels,
        proc_circuit.no_labels,
        proc_circuit.field,

    );

    Result::Ok(())
}
