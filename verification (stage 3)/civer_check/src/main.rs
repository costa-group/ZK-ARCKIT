mod tags_checking;
mod tree_constraints;
mod r1cs_reader;
use circom_algebra::num_traits::float::TotalOrder;
use circom_algebra::num_traits::Float;
use num_bigint_dig::BigInt;
use serde::{Serialize, Deserialize};
use tree_constraints::TreeConstraints;
use std::ops::Bound;
use std::collections::{HashMap, HashSet, BTreeMap};
use circom_algebra::algebra::Constraint;
use crate::r1cs_reader::read_r1cs;
use std::env;
use crate::tags_checking::PossibleResult;



use std::error::Error;
use std::fs::File;
use std::io::{BufReader, BufWriter};
use std::path::Path;
use std::io::Write;


use ansi_term::Colour;

#[derive(Deserialize, Debug)]
struct TimingInfo{
    clustering: f32,
    dag_construction: f32,
    equivalency: f32,
    total: f32,
}

#[derive(Deserialize, Debug)]
struct NodeInfo{
    node_id: usize,
    constraints: Vec<usize>, //ids of the constraints
    input_signals: Vec<usize>,
    output_signals: Vec<usize>,
    signals: Vec<usize>, 
    successors: Vec<usize> //ids of the successors 

}

#[derive(Deserialize, Debug)]
struct StructureInfo {
    timing: TimingInfo,
    nodes: Vec<NodeInfo>, //all the nodes of the circuit, position of the node is not the position.
    local_equivalency: Vec<Vec<usize>>, //equivalence classes, each inner vector is a class
    structural_equivalency: Vec<Vec<usize>>, //equivalence classes, each inner vector is a class
}

#[derive(Deserialize, Debug)]
struct StructureReader {
    timing: TimingInfo,
    nodes: Vec<NodeInfo>, //all the nodes of the circuit, position of the node is not the position.
    equivalency_local: Option<Vec<Vec<usize>>>, //equivalence classes, each inner vector is a class
    equivalency_structural: Option<Vec<Vec<usize>>>, //equivalence classes, each inner vector is a class

 }



fn read_structure_info_from_file<P: AsRef<Path>>(path: P) -> Result<StructureInfo, Box<dyn Error>> {
    // Open the file in read-only mode with buffer.
    let file = File::open(path)?;
    let reader = BufReader::new(file);

    // Read the JSON contents of the file as an instance of `StructureInfo`.
    let u: StructureReader = serde_json::from_reader(reader)?;

    let mut local_equivalence = Vec::new();
    if u.equivalency_local.is_some() { local_equivalence = u.equivalency_local.unwrap(); }

    let mut structural_equivalence = Vec::new();
    if u.equivalency_structural.is_some() { structural_equivalence = u.equivalency_structural.unwrap(); }
    else { structural_equivalence = local_equivalence.clone();}

    let structure_info = StructureInfo {
        timing: u.timing,
        nodes: u.nodes,
        local_equivalency: local_equivalence,
        structural_equivalency: structural_equivalence,
    };
    Ok(structure_info)
}

#[derive(Serialize, Debug)]

struct ResultInfo{
    //For each class, we store the duration and the size of the equivalence class, and the number of constraints and the number of smt calls.
    local_verified_classes: HashMap<usize, (f64, usize, usize, usize, usize)>,
    structural_verified_classes: HashMap<usize, (f64, usize, usize, usize, usize)>,
    total_number_of_local_classes: usize,
    total_number_of_structural_classes: usize,
    total_number_of_nodes: usize,
    verified_nodes: HashMap<usize, (f64, usize, usize, usize, usize)>,
    failed_nodes: HashMap<usize, (f64, usize, usize, usize, usize)>,
    unknown_nodes: HashMap<usize, (f64, usize, usize, usize, usize,)>,
    verified_with_parent_nodes: HashMap<usize, (f64, usize, usize, usize, usize)>
}

fn write_output_into_file<P: AsRef<Path>>(path: P, result: &ResultInfo) -> Result<(), Box<dyn Error>> {
    // Open the file in read-only mode with buffer.

    let file = File::create(path)?;
    let mut writer = BufWriter::new(file);

    // Write the result.
    let value = serde_json::to_string_pretty(result)?;
    writer.write(value.as_bytes())?;
    //write the number of equivalence classes
    writer.write_all(format!("\nNumber of local equivalence classes: {}\n", result.total_number_of_local_classes).as_bytes())?;
    //write the number of nodes
    writer.write_all(format!("Number of local equivalence classes verified: {}\n", result.local_verified_classes.len()).as_bytes())?;
    //compute mean duration and size of the equivalence classes
    write_equivalence_class_stats(&mut writer, "l-verified", &result.local_verified_classes)?;
     writer.write_all(format!("\nNumber of structural equivalence classes: {}\n", result.total_number_of_local_classes).as_bytes())?;
    
    writer.write_all(format!("Number of structural equivalence classes verified: {}\n", result.structural_verified_classes.len()).as_bytes())?;
    //compute mean duration and size of the equivalence classes
    write_equivalence_class_stats(&mut writer, "s-verified", &result.structural_verified_classes)?;
    writer.write_all(format!("Number of total nodes: {}\n", result.total_number_of_nodes).as_bytes())?;
    writer.write_all(format!("Number of remaining nodes: {}\n", result.verified_with_parent_nodes.len() + result.failed_nodes.len() + result.unknown_nodes.len()).as_bytes())?;
    //write the number of verified nodes
    writer.write_all(format!("Number of verified nodes: {}\n", result.verified_nodes.len()).as_bytes())?;
    write_node_stats(&mut writer, "verified", &result.verified_nodes)?;
    //write the number of failed nodes
    writer.write_all(format!("Number of failed nodes: {}\n", result.failed_nodes.len()).as_bytes())?;
    write_node_stats(&mut writer, "failed", &result.failed_nodes)?;
    //write the number of unknown nodes
    writer.write_all(format!("Number of unknown nodes: {}\n", result.unknown_nodes.len()).as_bytes())?;
    write_node_stats(&mut writer, "unknown", &result.unknown_nodes)?;
    //write the number of verified nodes with parent
    writer.write_all(format!("Number of verified nodes with parent: {}\n", result.verified_with_parent_nodes.len()).as_bytes())?;
    write_node_stats(&mut writer, "verified with parent", &result.verified_with_parent_nodes)?;
    writer.flush()?;
    Ok(())
}

fn write_node_stats<W: Write>(writer: &mut W, node_type: &str, nodes: &HashMap<usize, (f64, usize, usize, usize,usize)>) -> Result<(), Box<dyn Error>> {
    let mut total_duration = 0.0;
    let mut total_rounds = 0;
    let mut total_size = 0;
    let mut total_predecessors = 0;
    let mut max_size = 0;
    let mut max_duration = 0.0;
    let mut max_predecessors = 0;
    let mut max_rounds = 0;
    let mut max_smt = 0;
    let mut total_smt = 0;
    for (_, (duration, rounds, predecessors, size,num_smt_calls)) in nodes {
        
        total_rounds += rounds;
        total_size += size;
        total_predecessors += predecessors;
        max_size = max_size.max(*size);
        total_duration += duration;
        max_duration = max_duration.max(*duration);
        max_predecessors = max_predecessors.max(*predecessors);
        max_rounds = max_rounds.max(*rounds);
        total_smt += num_smt_calls;
        max_smt = max_smt.max(*num_smt_calls);
    }
    
    let mean_duration = (total_duration / nodes.len() as f64 * 10.0).round() / 10.0;
    let mean_rounds =  ((total_rounds as f64 / nodes.len() as f64) * 10.0).round() / 10.0;
    let mean_size = ((total_size as f64 / nodes.len() as f64) * 10.0).round() / 10.0;
    let mean_predecessors = ((total_predecessors as f64 / nodes.len() as f64) * 10.0).round() / 10.0;
    let max_duration = (max_duration * 10.0).round() / 10.0;
    let mean_smt = ((total_smt as f64 / nodes.len() as f64) * 10.0).round() / 10.0;
    writer.write_all(format!("Mean duration of {} nodes: {}\n", node_type, mean_duration).as_bytes())?;
    writer.write_all(format!("Mean number of children {} nodes: {}\n", node_type, mean_rounds).as_bytes())?;
    writer.write_all(format!("Mean size of {} nodes: {}\n", node_type, mean_size).as_bytes())?;
    writer.write_all(format!("Mean number of predecessors of {} nodes: {}\n", node_type, mean_predecessors).as_bytes())?; //write the
    writer.write_all(format!("Mean number of SMT calls of {} nodes: {}\n", node_type, mean_smt).as_bytes())?;
    writer.write_all(format!("Maximum size of {} nodes: {}\n", node_type, max_size).as_bytes())?;
    writer.write_all(format!("Maximum duration of {} nodes: {}\n", node_type, max_duration).as_bytes())?;
    writer.write_all(format!("Maximum number of children {} nodes: {}\n", node_type, max_rounds).as_bytes())?;
    writer.write_all(format!("Maximum number of predecessors of {} nodes: {}\n", node_type, max_predecessors).as_bytes())?;
    writer.write_all(format!("Maximum number of SMT calls of {} nodes: {}\n", node_type, max_smt).as_bytes())?;
    writer.write_all(format!("Total number of constraints of  {} nodes: {}\n", node_type, total_size).as_bytes())?;
    Ok(())
}

fn write_equivalence_class_stats<W: Write>(writer: &mut W, class_type: &str, classes: &HashMap<usize, (f64, usize, usize, usize, usize)>) -> Result<(), Box<dyn Error>> {
    let mut total_duration = 0.0;
    let mut total_size = 0;
    let mut max_size = 0;
    let mut max_duration = 0.0;
    let mut max_smt = 0;
    let mut total_smt = 0;
    let mut mean_constraints = 0;
    let mut max_constraints = 0;
    let mut total_verified_classes = 0;
    let mut maximum_different_classes = 0;
    let mut total_constraints = 0;
    for (_, (duration, size, different_classes, num_constraints, smt_calls)) in classes {
        total_duration += duration;
        total_size += size;
        total_constraints += num_constraints * size; 
        max_size = max_size.max(*size);
        max_duration = max_duration.max(*duration);
        max_smt = max_smt.max(*smt_calls);
        total_smt += smt_calls;
        mean_constraints += num_constraints;
        max_constraints = max_constraints.max(*num_constraints);
        maximum_different_classes = maximum_different_classes.max(*different_classes);
        total_verified_classes += different_classes;
    }

    let total_duration = (total_duration * 10.0).round() / 10.0;
    let max_duration = (max_duration * 10.0).round() / 10.0;
    let mean_constraints = (mean_constraints as f64 / classes.len() as f64 * 10.0).round() / 10.0;
    writer.write_all(format!("Total duration of {} equivalence classes: {}\n", class_type, total_duration).as_bytes())?;
    writer.write_all(format!("Total number of {} nodes: {}\n", class_type, total_size).as_bytes())?;
    writer.write_all(format!("Total number of SMT calls of {} equivalence classes: {}\n", class_type, total_smt).as_bytes())?;
    writer.write_all(format!("Mean number of constraints of {} equivalence classes: {}\n", class_type, mean_constraints).as_bytes())?;
    //write the maximum size of the equivalence classes
    writer.write_all(format!("Maximum size of {} equivalence classes: {}\n", class_type, max_size).as_bytes())?;
    //write the maximum duration of the equivalence classes
    writer.write_all(format!("Maximum duration of {} equivalence classes: {}\n", class_type, max_duration).as_bytes())?;
    //write the maximum number of SMT calls of the equivalence classes
    writer.write_all(format!("Maximum number of SMT calls of {} equivalence classes: {}\n", class_type, max_smt).as_bytes())?;
    //write the maximum number of constraints of the equivalence classes
    writer.write_all(format!("Maximum number of constraints of {} equivalence classes: {}\n", class_type, max_constraints).as_bytes())?;
    if class_type == "l-verified" {
        //write the total number of different local equivalence classes
        writer.write_all(format!("Maximum number of different local equivalence classes: {}\n", total_verified_classes).as_bytes())?;
        writer.write_all(format!("Total number of different local equivalence classes: {}\n", total_verified_classes).as_bytes())?;
    }
  
    writer.write_all(format!("Total number of constraints: {}\n",  total_constraints).as_bytes())?;
   
    Ok(())
}

fn read_constraints(input: &str) -> Vec<Constraint<usize>>{
    println!("Reading constraints of {}", input);
    let result = read_r1cs(input).unwrap();
    let constraint_list = result.constraints;
    let mut formatted_list = Vec::new();
    for (a, b, c) in constraint_list{
        formatted_list.push(Constraint::new(a,b,c));
    }
    formatted_list
}

fn read_init_constraints_info<P: AsRef<Path>>(path: P) -> Result<BTreeMap<usize, String>, Box<dyn Error>> {
    // Open the file in read-only mode with buffer.
    let file = File::open(path)?;
    let reader = BufReader::new(file);

    // Read the JSON contents of the file as an instance of `StructureInfo`.
    let u: BTreeMap<usize, String> = serde_json::from_reader(reader)?;

    Ok(u)

}

fn get_constraint_info_component(info: &BTreeMap<usize, String>, c: usize) -> (usize, String){
    let mut previous_c = 0;
    let mut previous_comp = "";
    for (init, comp) in info{
        if *init > c{
            return (previous_c, previous_comp.to_string());
        } else{
            previous_c = *init;
            previous_comp = comp;
        }
    }
    (previous_c, previous_comp.to_string())

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
    let args: Vec<String> = env::args().collect();
    let constraints = read_constraints(&args[1]);
    let structure = read_structure_info_from_file(&args[2]).unwrap();
    let timeout = &args[3];
    let output_json = &args[4];
    
    let starting_constraints = if args.len() > 5{
        let init_constraints = read_init_constraints_info(&args[5]).unwrap();
        Some(init_constraints)
    } else{
        None
    };


    let mut local_equivalence_classes = HashMap::new();
    let mut structural_equivalence_classes = HashMap::new();
    let mut id_equiv_class = 0;

    let mut nodeid2pos = HashMap::new(); // node id to position in vector
    let mut node2parent = HashMap::new(); // node id to parent node ids
    let mut pos = 0;
    for node in &structure.nodes {
        nodeid2pos.insert(node.node_id, pos);
        pos += 1;
        for child in &node.successors {
            node2parent.entry(*child).or_insert_with(Vec::new).push(node.node_id);
        }
    }


    for eq_class in &structure.local_equivalency{
        for node_id in eq_class{
            local_equivalence_classes.insert(*node_id, id_equiv_class);
        }
        id_equiv_class += 1;
    }

    id_equiv_class = 0;
    for eq_class in &structure.structural_equivalency{
        for node_id in eq_class{
            structural_equivalence_classes.insert(*node_id, id_equiv_class);
        }
        id_equiv_class += 1;
    }

    println!("Local equivalence classes: {:?}", local_equivalence_classes);
    for c in local_equivalence_classes.keys() {
        println!("Node {} belongs to local equivalence class {}", c, local_equivalence_classes[c]);
    }
    println!("Structural equivalence classes: {:?}", structural_equivalence_classes);
    for c in structural_equivalence_classes.keys() {
        println!("Node {} belongs to structural equivalence class {}", c, structural_equivalence_classes[c]);
    }

    let field_str = "21888242871839275222246405745257275088548364400416034343698204186575808495617";
    let field = field_str.parse::<BigInt>().unwrap();
    //let mut studied_eq_classes = HashMap::new();
    let mut studied_nodes = HashMap::new();

    
    let mut results = ResultInfo{
        local_verified_classes: HashMap::new(),
        structural_verified_classes: HashMap::new(),
        total_number_of_local_classes: structure.local_equivalency.len(),
        total_number_of_structural_classes: structure.structural_equivalency.len(),
        total_number_of_nodes: structure.nodes.len(),
        verified_nodes: HashMap::new(),
        failed_nodes: HashMap::new(),
        unknown_nodes: HashMap::new(),
        verified_with_parent_nodes: HashMap::new()
    };

    for node in &structure.nodes{
        process_node(node, 
            &structure, 
            &constraints, 
            &local_equivalence_classes,
            &structural_equivalence_classes,
            &mut studied_nodes,
            &nodeid2pos, 
            &node2parent,
            &field, 
            timeout, 
            output_json, 
            &mut results);
    }

    let _ = write_output_into_file(output_json, &results);

    let mut templates_with_unverified_constraints: HashMap<String, Vec<usize>> = HashMap::new();

    //Print the studied nodes
    println!("### Studied nodes");
    let mut number_of_constraints = 0;
    let mut number_of_constraints_verified = 0;
    for (node_id, result) in &studied_nodes{
        println!("Node {}: {:?}", node_id, result.result_to_str());
        let node_info = &structure.nodes[nodeid2pos[node_id]];
        number_of_constraints += node_info.constraints.len();
        if *result == PossibleResult::VERIFIED {
            number_of_constraints_verified += node_info.constraints.len();
        } else{
            if starting_constraints.is_some(){
                for c in &node_info.constraints{
                    let (init_constraint, component) = 
                        get_constraint_info_component(starting_constraints.as_ref().unwrap(), *c);
                    if templates_with_unverified_constraints.contains_key(&component){
                        let value = templates_with_unverified_constraints.get_mut(&component).unwrap();
                        value.push(c - init_constraint);
                    } else{
                        templates_with_unverified_constraints.insert(component.clone(), vec![c - init_constraint]);
                    }
                }
            }
        }
    }
    println!("Components that contain constraints that have not been verified: {:?}", templates_with_unverified_constraints);
    println!("Total number of constraints: {}", number_of_constraints);
    println!("Total number of verified constraints: {}", number_of_constraints_verified);
    Result::Ok(())
}

fn process_node(
    node: &NodeInfo,
    structure: &StructureInfo,
    constraints: &Vec<Constraint<usize>>,
    local_equivalence_classes: &HashMap<usize, usize>,
    structural_equivalence_classes: &HashMap<usize, usize>,
    //studied_eq_classes: &mut HashMap<usize, PossibleResult>,
    studied_nodes: &mut HashMap<usize, PossibleResult>,
    nodeid2pos: &HashMap<usize, usize>,
    node2parent: &HashMap<usize, Vec<usize>>,
    field: &BigInt,
    timeout: &str,
    output_json: &String,
    results: &mut ResultInfo,
) {

    if studied_nodes.contains_key(&node.node_id) {
        // If the node has already been studied, we skip it.
        return;
    }

    // If the equivalence class of the node has already been studied, we skip it.
    //let eq_class = equivalence_classes.get(&node.node_id).unwrap();

    //if !studied_eq_classes.contains_key(&eq_class) || studied_eq_classes[&eq_class] != PossibleResult::VERIFIED {
            
        // If the equivalence class of the node has not been studied, we process it.
        // First, we process the child nodes.
    let mut num_smt_calls = 0;
    for successor in &node.successors{
            let pos_successor = nodeid2pos[successor];
            let successor_node = structure.nodes.get(pos_successor).unwrap();
            if  studied_nodes.contains_key(&successor_node.node_id) {
                // If the equivalence class has already been studied, we skip processing it
                // and move on to the next node.
                continue;
            } else {
                process_node(
                    successor_node,
                    structure,
                    constraints,
                    local_equivalence_classes,
                    structural_equivalence_classes,
                    //studied_eq_classes,
                    studied_nodes,
                    nodeid2pos,
                    node2parent,
                    field,
                    timeout,
                    output_json,
                    results,
                );
            }
        }
        // Now, we process the node itself.
        let constraint_tree = TreeConstraints::new(node);
        let (result, duration, n_rounds, logs) = constraint_tree.check_tags(
            &field,
            timeout.parse::<u64>().unwrap(),
            &structure.nodes,
            &nodeid2pos, 
            &constraints 
        );
        for log in logs{
            println!("{}", log);
        }
        num_smt_calls = 1 + n_rounds; // 1 for the initial check + n_rounds for the subsequent checks
        match result{
            PossibleResult::VERIFIED =>{
                        //println!("### The node {} has been verified", node.node_id);
                        if n_rounds == 0 {
                           println!("### The node {} has been verified in 0 rounds", node.node_id);
                           
                           let local_eq_class = local_equivalence_classes.get(&node.node_id);
                           let structural_eq_class = structural_equivalence_classes.get(&node.node_id);
                           if local_eq_class.is_some() {
                                let local_eq_class = local_eq_class.unwrap();
                                let mut different_structural_classes = HashSet::new();
                                for equivalent_node in &structure.local_equivalency[*local_eq_class]{
                                    let structural_eq_class = structural_equivalence_classes.get(equivalent_node);
                                    if structural_eq_class.is_some() {
                                        different_structural_classes.insert(*structural_eq_class.unwrap());
                                    }
                                }
                                results.local_verified_classes.insert(*local_eq_class, (duration, structure.local_equivalency[*local_eq_class].len(), different_structural_classes.len(), node.constraints.len(), num_smt_calls));
                                for equivalent_node in &structure.local_equivalency[*local_eq_class]{
                                    studied_nodes.insert(*equivalent_node, result.clone());
                                }
                           }
                           else if structural_eq_class.is_some(){
                                let structural_eq_class = structural_eq_class.unwrap();
                                results.structural_verified_classes.insert(*structural_eq_class, (duration, structure.structural_equivalency[*structural_eq_class].len(), 0, node.constraints.len(), num_smt_calls));
                                for equivalent_node in &structure.structural_equivalency[*structural_eq_class]{
                                    studied_nodes.insert(*equivalent_node, result.clone());
                                }
                           } else {
                                unreachable!("The node {} has no equivalence class", node.node_id);
                           }
       
                           
                        } else {                            
                            //results.verified_nodes.insert(node.node_id, (duration, n_rounds, 0, node.signals.len()));
                            let structural_eq_class = structural_equivalence_classes.get(&node.node_id);
                            if structural_eq_class.is_some(){
                                let structural_eq_class = structural_eq_class.unwrap();
                                results.structural_verified_classes.insert(*structural_eq_class, (duration, structure.structural_equivalency[*structural_eq_class].len(), 0, node.constraints.len(), num_smt_calls));
                                for equivalent_node in &structure.structural_equivalency[*structural_eq_class]{
                                    studied_nodes.insert(*equivalent_node, result.clone());
                                }
                            } else if !structural_equivalence_classes.is_empty() {
                                unreachable!("The node {} has no equivalence class", node.node_id);
                            }
                        }
                    }
            PossibleResult::FAILED =>{   
                        results.failed_nodes.insert(node.node_id, (duration, n_rounds, 0, node.constraints.len(),num_smt_calls));
                    }
            PossibleResult::UNKNOWN =>{
                        results.unknown_nodes.insert(node.node_id, (duration, n_rounds, 0, node.constraints.len(),num_smt_calls));
                    }
            _ => unreachable!(),
        }
    studied_nodes.insert(node.node_id, result.clone());

    if studied_nodes[&node.node_id] == PossibleResult::VERIFIED {
        //If the equivalence class has been verified, we skip it.
        // If the node has been verified, we skip it.
        return;
    }

    // If the node has failed children, we try to verify again the node with the failed children.

    println!("### Trying to verify adding constraints of {} with predecessors\n",node.node_id);
    let mut  constraint_tree = TreeConstraints::new(node);
    
    let father = node2parent.get(&node.node_id);
    if father.is_none(){
        println!("### The node {} has no parent", node.node_id);
        return;
    } 

    
    let mut result = PossibleResult::NOTHING;
    let mut number_predecessors = 0;
    let mut pending_parents = node2parent[&node.node_id].clone();
    let mut already_inserted = HashSet::new();
    let mut maximum_number_predecessors = 0;
    already_inserted.insert(node.node_id);
    while !pending_parents.is_empty() && result != PossibleResult::VERIFIED && (result != PossibleResult::UNKNOWN && number_predecessors < maximum_number_predecessors) {
        println!("The current result is: {}",result.result_to_str());
        let modified = get_next_parent(node, structure, nodeid2pos, node2parent, &mut constraint_tree, &mut number_predecessors, &mut pending_parents, &mut already_inserted);
        let duration;
        let n_rounds;
        let logs;
        if !modified {
            // If there are no more pending parents, we break the loop.
            println!("### No more pending parents for node {}", node.node_id);
            break;
        }
        (result, duration, n_rounds, logs) = constraint_tree.check_tags(
            &field,
            timeout.parse::<u64>().unwrap(),
            &structure.nodes,
            &nodeid2pos, 
            &constraints
        );
        num_smt_calls += 1 + n_rounds; // 1 for the initial check + n_rounds for the subsequent checks
        println!("{}",result.result_to_str());
        if let PossibleResult::VERIFIED = result  {
            results.verified_with_parent_nodes.insert(node.node_id, (duration, n_rounds,number_predecessors, node.constraints.len(),num_smt_calls));
            results.unknown_nodes.remove(&node.node_id);
            results.failed_nodes.remove(&node.node_id);
            println!("### The node {} has been verified with {} predecessors", node.node_id, number_predecessors);
        } else if let PossibleResult::FAILED = result {
            results.failed_nodes.insert(node.node_id, (duration, n_rounds, number_predecessors, node.constraints.len(),num_smt_calls));
            results.unknown_nodes.remove(&node.node_id);
            println!("### The node {} has failed with {} predecessors", node.node_id, number_predecessors);
        } else if let PossibleResult::UNKNOWN = result {
            results.failed_nodes.remove(&node.node_id);
            results.unknown_nodes.insert(node.node_id, (duration, n_rounds, number_predecessors, node.constraints.len(),num_smt_calls));
            println!("### The node {} is unknown with {} predecessors", node.node_id, number_predecessors);
        } else {
            unreachable!();
            
        }
        studied_nodes.insert(node.node_id, result.clone());
        for log in logs{
            println!("{}", log);
        }
        if result == PossibleResult::UNKNOWN && n_rounds > 0 {
            result = PossibleResult::NOTHING; // We continue trying to add more predecessors
        }
    }
}

fn get_next_parent(node: &NodeInfo, structure: &StructureInfo, nodeid2pos: &HashMap<usize, usize>, node2parent: &HashMap<usize, Vec<usize>>, 
    constraint_tree: &mut TreeConstraints, number_predecessors: &mut usize, pending_parents: &mut Vec<usize>, already_inserted: &mut HashSet<usize>) -> bool {
    let mut next_pending_parents = Vec::new();
    let mut modified = false;
    for parent_id in &*pending_parents {
        if already_inserted.contains(&parent_id) {
            // If the parent has already been inserted, we skip it.
            continue;
        }
        already_inserted.insert(*parent_id);
        println!("### Adding constraints to node {} of the predecessor: {}", node.node_id, parent_id);
        let pos_parent = nodeid2pos[&parent_id];
        let parent_node = &structure.nodes[pos_parent];
        constraint_tree.constraints.extend(parent_node.constraints.clone());
        constraint_tree.signals.extend(parent_node.signals.clone());
        constraint_tree.inputs.extend(parent_node.input_signals.clone());
        modified = true;
        *number_predecessors += 1;
        if node2parent.contains_key(&parent_id) {
            // If the parent has children, we add them to the next pending parents.
            next_pending_parents.extend(node2parent[&parent_id].clone());
        }
    }
    *pending_parents = next_pending_parents;
    return modified;
}

fn get_next_parent2(node: &NodeInfo, structure: &StructureInfo, nodeid2pos: &HashMap<usize, usize>, node2parent: &HashMap<usize, Vec<usize>>, 
    constraint_tree: &mut TreeConstraints, number_predecessors: &mut usize, pending_parents: &mut Vec<usize>, already_inserted: &mut HashSet<usize>) -> bool {
    while let Some(parent_id) = pending_parents.pop() {
        if already_inserted.contains(&parent_id) {
            // If the parent has already been inserted, we skip it.
            continue;
        }
        already_inserted.insert(parent_id);
        println!("### Adding constraints to node {} of the predecessor: {}", node.node_id, parent_id);
        let pos_parent = nodeid2pos[&parent_id];
        let parent_node = &structure.nodes[pos_parent];
        constraint_tree.constraints.extend(parent_node.constraints.clone());
        constraint_tree.signals.extend(parent_node.signals.clone());
        constraint_tree.inputs.extend(parent_node.input_signals.clone());
        *number_predecessors += 1;
        if node2parent.contains_key(&parent_id) {
                // If the parent has children, we add them to the pending parents.
            pending_parents.extend(node2parent[&parent_id].clone());
        }
        return true;
    }
    return false;
}
