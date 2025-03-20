mod constraint_simplification;
mod non_linear_simplification;
use num_bigint_dig::BigInt;
use serde::{Deserialize, Serialize};
use std::collections::{HashSet, LinkedList, HashMap};
use circom_algebra::algebra::AIRConstraint;
use circom_algebra::algebra::Substitution;
use circom_algebra::algebra::AIRSubstitution;

use circom_algebra::algebra::ArithmeticExpression;
use circom_algebra::constraint_storage::AIRConstraintStorage;
use crate::constraint_simplification::simplification;

use std::env;


use std::error::Error;
use std::fs::File;
use std::io::{BufReader, BufWriter, Write};
use std::path::Path;


use ansi_term::Colour;

pub type C = AIRConstraint<usize>;
pub type S = Substitution<usize>;
pub type A = ArithmeticExpression<usize>;

#[derive(PartialEq)]
pub enum SimplificationType{
    PLONK,
    ACIR,
    R1CS
}


#[derive(Deserialize, Debug, Serialize)]
struct LinearInfo{
   witness: usize,
   coeff: String, 
}

#[derive(Deserialize, Debug, Serialize)]
struct MulInfo{
    witness1: usize,
    witness2: usize,
    coeff: String
}


#[derive(Deserialize, Debug, Serialize)]
struct ConstraintInfo{
    linear: Vec<LinearInfo>,
    mul: Vec<MulInfo>,
    constant: String
}

#[derive(Deserialize, Debug, Serialize)]
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


fn write_output_into_file<P: AsRef<Path>>(path: P, result: &CircuitInfo) -> Result<(), Box<dyn Error>> {
    // Open the file in read-only mode with buffer.

    let file = File::create(path)?;
    let mut writer = BufWriter::new(file);
    // Write the result.
    let value = serde_json::to_string_pretty(result)?;
    writer.write(value.as_bytes())?;
    writer.flush()?;
    Ok(())
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

fn process_constraint_info(cons: C) -> ConstraintInfo{
    let mut linear = Vec::new();
    let mut mul = Vec::new();
    let mut constant = "0".to_string();

    for ((s1, s2), coef) in cons.muls(){
        let new_mul = MulInfo{
            witness1: *s1,
            witness2: *s2,
            coeff: coef.to_string()
        };
        mul.push(new_mul);
    }  
    for (s, coef) in cons.linear(){
        if *s != C::constant_coefficient(){
            let new_lin = LinearInfo{
                witness: *s,
                coeff: coef.to_string()
            };
            linear.push(new_lin);
        } else{
            constant = coef.to_string();
        }
        
    }  
    ConstraintInfo{
        mul,
        linear,
        constant
    }
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
    if signals.len() + 1 != info.number_of_signals{
        println!("Different number of signals: Real -> {}, Given -> {}", signals.len(), info.number_of_signals);
    }
    ProcessedCircuit{
        storage, 
        linear, 
        forbidden,
        field: to_bi_field,
        no_labels: signals.len() + 1
    }
}

fn move_storage_to_constraint_info(constraints: AIRConstraintStorage, no_signals: usize, outputs: Vec<usize>)
-> CircuitInfo{

    let mut info_constraints = Vec::new();
    for c_id in constraints.get_ids(){
        let c = constraints.read_constraint(c_id).unwrap();
        let info = process_constraint_info(c);
        info_constraints.push(info);
    }

    
    CircuitInfo { 
        constraints: info_constraints, 
        inputs: Vec::new(),
        outputs,
         number_of_signals: no_signals
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
    let out_copy = circuit.outputs.clone();
    let proc_circuit = move_constraint_info_to_storage(circuit);
    
    let simp_mode = if args.len() == 4{
        match args[3].as_str(){
            "plonk" => {SimplificationType::PLONK },
            "acir" => {SimplificationType::ACIR },
            "r1cs" => {SimplificationType::R1CS },
            _ => {unreachable!()}

        }
    } else{
        SimplificationType::ACIR 
    };


    let (new_constraints, signals) = simplification(
        proc_circuit.linear,
        proc_circuit.storage,
        Arc::new(proc_circuit.forbidden),
        proc_circuit.no_labels,
        proc_circuit.no_labels,
        proc_circuit.field,
        simp_mode // CHOOSES IF APPLYING PLONK OR NOT
    );


    let circuit_info = move_storage_to_constraint_info(new_constraints, signals.len(), out_copy);
    let _ = write_output_into_file(&args[2], &circuit_info);

    Result::Ok(())
}
