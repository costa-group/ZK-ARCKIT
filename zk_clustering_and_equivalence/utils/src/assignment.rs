use std::collections::HashMap;

use std::hash::Hash;
use std::cmp::Eq;

pub struct Assignment<'a, T: Hash + Eq, const N: usize> {
    assignment: HashMap<[&'a T; N], usize>,
    inv_assignment: Option<Vec<[&'a T; N]>>,
    curr: usize,
    offset: usize,
    has_assigned: Vec<usize>
} 

impl<'a, T: Hash + Eq, const N: usize> Assignment<'a, T, N> {

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

    pub fn get_assignment(&mut self, input: [&'a T; N]) -> usize {


        if !self.assignment.contains_key(&input) {

            self.assignment.insert(input, self.curr + self.offset);
            if let Some(inv_assignment) = &mut self.inv_assignment {inv_assignment.push(input.clone());}
            self.has_assigned.push(self.curr);

            self.curr += 1;
        }

        *self.assignment.get(&input).unwrap() + 1
    }
    
    pub fn get_inv_assignment(&self, inverse: usize) -> Option<[&'a T; N]> {
        if let Some(inv_assignment) = &self.inv_assignment {Some(inv_assignment[inverse - 1 - self.offset])}
        else {None}
    }

    pub fn number_assigned(&self) -> usize {
        self.assignment.len()
    }
}