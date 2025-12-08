use std::collections::HashMap;

use std::hash::Hash;
use std::cmp::Eq;

pub struct Assignment<T: Hash + Eq, const N: usize> {
    assignment: HashMap<[T; N], usize>,
    inv_assignment: Option<Vec<[T; N]>>,
    curr: usize,
    offset: usize,
    has_assigned: Vec<usize>
}

impl<T: Hash + Eq + Clone, const N: usize> Assignment<T, N> {

    pub fn new(offset: usize) -> Self {
        Assignment { assignment: HashMap::new(), inv_assignment: Some(Vec::new()), curr: 0, offset: offset, has_assigned: Vec::new() }
    }

    pub fn get_offset(&self) -> usize {
        self.offset
    }

    pub fn drop_inverse(&mut self) -> () {
        self.inv_assignment = None;
    }

    pub fn len(&self) -> usize {
        self.assignment.len()
    }

    pub fn get_assignment(&mut self, input: [T; N]) -> usize {


        if !self.assignment.contains_key(&input) {

            self.assignment.insert(input.clone(), self.curr + self.offset);
            self.inv_assignment.as_mut().map(|inv_assignment| inv_assignment.push(input.clone()));
            self.has_assigned.push(self.curr);

            self.curr += 1;
        }

        *self.assignment.get(&input).unwrap() + 1
    }
    
    pub fn get_inv_assignment(&self, inverse: usize) -> Option<[T; N]> {
        self.inv_assignment.as_ref().map(|inv_assignment| inv_assignment[inverse - 1 - self.offset].clone() )
        
    }

    pub fn number_assigned(&self) -> usize {
        self.assignment.len()
    }
}