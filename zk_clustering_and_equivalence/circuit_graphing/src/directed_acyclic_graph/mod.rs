use std::marker::PhantomData;
use std::collections::HashSet;

use circuits_and_constraints::constraint::Constraint;
use circuits_and_constraints::circuit::Circuit;

mod dag_from_partition;

pub struct DAGNode<'a, C: Constraint + 'a, S: Circuit<C> + 'a> {
    circ : &'a S,
    id : usize,
    constraints : Vec<usize>,
    input_signals : HashSet<usize>,
    output_signals : HashSet<usize>,
    successors : Vec<usize>,
    predecessors : Vec<usize>,
    subcircuit : Option<S>,

    _phantom: PhantomData<C>
}

impl<'a, C: Constraint + 'a, S: Circuit<C> + 'a> DAGNode<'a, C, S> {

    pub fn new(circ: &'a S, node_id: usize, constraints: Vec<usize>, input_signals: HashSet<usize>, output_signals: HashSet<usize>) -> DAGNode<'a, C, S> {
        
        Self { circ: circ, id: node_id, constraints: constraints, input_signals: input_signals, output_signals: output_signals, successors: Vec::new(), predecessors: Vec::new(), subcircuit: None, _phantom: PhantomData }
    }

    pub fn add_successors(&mut self, to_add: impl Iterator<Item = usize>) -> () {
        self.successors.extend(to_add)
    }

    pub fn add_predecessors(&mut self, to_add: impl Iterator<Item = usize>) -> () {
        self.predecessors.extend(to_add)
    }

    pub fn update_input_signals(&mut self, to_add: impl Iterator<Item = usize>) -> () {
        self.input_signals.extend(to_add)
    }

    pub fn update_output_signals(&mut self, to_add: impl Iterator<Item = usize>) -> () {
        self.output_signals.extend(to_add)
    }

    pub fn get_subcircuit(&mut self) -> &S {
        if self.subcircuit.is_none() {
            self.subcircuit = Some(self.circ.take_subcircuit(&self.constraints, Some(&self.input_signals), Some(&self.output_signals), None, None))
        }
        self.subcircuit.as_ref().unwrap()
    }
}