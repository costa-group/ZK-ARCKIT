use crate::algebra::{AIRConstraint, Constraint};
use crate::num_bigint::BigInt;
use constant_tracking::{ConstantTracker, CID};
use std::collections::LinkedList;

mod logic;

type RawField = Vec<u8>;
type FieldTracker = ConstantTracker<RawField>;
type S = usize;
type C = Constraint<usize>;
type AC = AIRConstraint<usize>;


type CompressedExpr = Vec<(CID, S)>;
type CompressedMul = Vec<(CID, S, S)>;
type CompressedConstraint = (CompressedExpr, CompressedExpr, CompressedExpr); // A, B, C
type CompressedAIRConstraint = (CompressedMul, CompressedExpr); // mul, linear


pub type ConstraintID = usize;
pub struct ConstraintStorage {
    field_tracker: FieldTracker,
    constraints: Vec<CompressedConstraint>,
}

impl ConstraintStorage {
    pub fn new() -> ConstraintStorage {
        ConstraintStorage { field_tracker: FieldTracker::new(), constraints: Vec::new() }
    }

    pub fn add_constraint(&mut self, constraint: C) -> ConstraintID {
        let id = self.constraints.len();
        let compressed = logic::code_constraint(constraint, &mut self.field_tracker);
        self.constraints.push(compressed);
        id
    }

    pub fn read_constraint(&self, id: ConstraintID) -> Option<C> {
        if id < self.constraints.len() {
            Some(logic::decode_constraint(&self.constraints[id], &self.field_tracker))
        } else {
            None
        }
    }

    pub fn replace(&mut self, id: ConstraintID, new: C) {
        if id < self.constraints.len() {
            self.constraints[id] = logic::code_constraint(new, &mut self.field_tracker);
        }
    }

    pub fn extract_with(&mut self, filter: &dyn Fn(&C) -> bool) -> LinkedList<C> {
        let old = std::mem::take(&mut self.constraints);
        let mut removed = LinkedList::new();
        for c in old {
            let decoded = logic::decode_constraint(&c, &self.field_tracker);
            if filter(&decoded) {
                removed.push_back(decoded);
            } else {
                self.constraints.push(c);
            }
        }
        removed
    }

    pub fn get_ids(&self) -> Vec<ConstraintID> {
        (0..self.constraints.len()).collect()
    }

    pub fn no_constants(&self) -> CID {
        self.field_tracker.next_id()
    }
}


pub struct AIRConstraintStorage{
    field_tracker: FieldTracker,
    constraints: Vec<CompressedAIRConstraint>
}

impl AIRConstraintStorage {
    pub fn new() -> AIRConstraintStorage {
        AIRConstraintStorage { field_tracker: FieldTracker::new(), constraints: Vec::new() }
    }

    pub fn add_constraint(&mut self, constraint: AC) -> ConstraintID {
        let id = self.constraints.len();
        let compressed = logic::code_air_constraint(constraint, &mut self.field_tracker);
        self.constraints.push(compressed);
        id
    }

    pub fn read_constraint(&self, id: ConstraintID) -> Option<AC> {
        if id < self.constraints.len() {
            Some(logic::decode_air_constraint(&self.constraints[id], &self.field_tracker))
        } else {
            None
        }
    }

    pub fn replace(&mut self, id: ConstraintID, new: AC) {
        if id < self.constraints.len() {
            self.constraints[id] = logic::code_air_constraint(new, &mut self.field_tracker);
        }
    }

    pub fn extract_with(&mut self, filter: &dyn Fn(&AC) -> bool) -> LinkedList<AC> {
        let old = std::mem::take(&mut self.constraints);
        let mut removed = LinkedList::new();
        for c in old {
            let decoded = logic::decode_air_constraint(&c, &self.field_tracker);
            if filter(&decoded) {
                removed.push_back(decoded);
            } else {
                self.constraints.push(c);
            }
        }
        removed
    }

    pub fn get_ids(&self) -> Vec<ConstraintID> {
        (0..self.constraints.len()).collect()
    }

    pub fn no_constants(&self) -> CID {
        self.field_tracker.next_id()
    }
}
