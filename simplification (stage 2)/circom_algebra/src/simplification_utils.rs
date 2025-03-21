use super::num_bigint::BigInt;
use crate::num_traits::ToPrimitive;
use crate::modular_arithmetic;
use std::collections::{BTreeMap, HashMap, HashSet, LinkedList};
use std::mem::replace;

type C = crate::algebra::AIRConstraint<usize>;
type S = crate::algebra::Substitution<usize>;
type A = crate::algebra::ArithmeticExpression<usize>;
type SH = BTreeMap<usize, S>;
type SHNotNormalized = BTreeMap<usize, (BigInt, S)>;

#[allow(dead_code)]
fn debug_check_keys_in_order(tree: &BTreeMap<usize, S>) -> bool {
    let mut prev: i32 = -1;
    let mut ret = true;
    for i in tree.keys() {
        ret = ret && (i.to_i32().unwrap() > prev);
        prev = i.to_i32().unwrap();
    }
    ret
}

struct SignalDefinition<'a> {
    deleted_symbols: HashSet<usize>,
    forbidden: &'a HashSet<usize>,
}

impl<'a> SignalDefinition<'a> {
    pub fn can_be_taken(&self, k: usize) -> bool {
        !self.forbidden.contains(&k)
    }
    pub fn delete(&mut self, k: usize) {
        self.deleted_symbols.insert(k);
    }
    pub fn is_deleted(&self, k: usize) -> bool {
        self.deleted_symbols.contains(&k)
    }
}

struct SignalDefinition4<'a> {
    deleted_symbols: HashSet<usize>,
    forbidden: &'a HashSet<usize>,
    order_signals: LinkedList<usize>, // the last eliminated is the first in the list
}

impl<'a> SignalDefinition4<'a> {
    pub fn can_be_taken(&self, k: usize) -> bool {
        !self.forbidden.contains(&k)
    }
    pub fn delete(&mut self, k: usize) {
        self.deleted_symbols.insert(k);
        self.order_signals.push_front(k);
    }
    pub fn is_deleted(&self, k: usize) -> bool {
        self.deleted_symbols.contains(&k)
    }
}

struct SignalsInformation {
    pub signal_to_ocurrences: HashMap<usize, usize>,
}

impl SignalsInformation {

    pub fn new(constraints: &Vec<C>, signals: &SignalDefinition4, num_signals: usize) -> (SignalsInformation, BTreeMap<usize, usize>) {
        let mut signal_to_ocurrences: HashMap<usize, usize> = HashMap::with_capacity(num_signals);
        let mut signal_to_rep: HashMap<usize, usize> = HashMap::with_capacity(num_signals);
        let mut uniques: BTreeMap<usize, usize> = BTreeMap::new();
        for pos in 0..constraints.len(){
            for k in constraints[pos].linear().keys() {
                if signals.can_be_taken(*k) {
                    match signal_to_ocurrences.get_mut(k){
                        Some(prev_ocu) =>{
                            *prev_ocu = *prev_ocu + 1;
                        },
                        None => {
                            signal_to_ocurrences.insert(*k, 1);
                            signal_to_rep.insert(*k, pos);
                        }
                    }
                }
            }
        }

        for (k, ocu) in &signal_to_ocurrences{
            if *ocu == 1{
                uniques.insert(*k, *signal_to_rep.get(k).unwrap());
            }
        }
        (SignalsInformation{signal_to_ocurrences}, uniques)
    }

    pub fn remove_constraint(&mut self, constraint: &C, signals: &SignalDefinition4){
        for signal in constraint.linear().keys(){
            if signals.can_be_taken(*signal){
                match self.signal_to_ocurrences.get_mut(&signal){
                    Some(ocurrences) =>{
                        *ocurrences = *ocurrences - 1;
                    },
                    None => {},
                }
            }
        }
        
    }


    pub fn remove_signal(&mut self, signal: usize){
        self.signal_to_ocurrences.remove(&signal);
    }

}

fn substitution_process_3(
    signals: &mut SignalDefinition,
    constraints: &mut LinkedList<C>,
    substitutions: &mut SHNotNormalized,
    field: &BigInt,
    only_plonk: bool,
) {
    let mut lconst = LinkedList::new();
    while let Option::Some(actual_constraint) = LinkedList::pop_back(constraints) {
        treat_constraint_3(signals, substitutions, &mut lconst, actual_constraint, field, only_plonk);
    }
    *constraints = lconst;
}

fn substitution_process_4(
    signals: &mut SignalDefinition4,
    constraints: &mut LinkedList<C>,
    substitutions: &mut SHNotNormalized,
    num_signals: usize,
    field: &BigInt,
    only_plonk: bool,
) {
    let mut lconst = LinkedList::new();
    let mut vec_constraints = Vec::new();
    for c in &mut *constraints{
        vec_constraints.push(c.clone());
    }

    let (mut info_ocurrences, uniques) = SignalsInformation::new(&vec_constraints, signals, num_signals);
    for (signal, index) in uniques{
        if !vec_constraints[index].is_empty(){
            let actual_constraint = replace(&mut vec_constraints[index], C::empty());
            info_ocurrences.remove_constraint(&actual_constraint, signals);  
            treat_unique_constraint_4(signals, substitutions, &mut lconst, actual_constraint, &mut info_ocurrences, signal, field, only_plonk);
        }
    }

    while !vec_constraints.is_empty(){
        if let Option::Some(actual_constraint) = Vec::pop(&mut vec_constraints) {
            info_ocurrences.remove_constraint(&actual_constraint, signals);    
            treat_constraint_4(signals, substitutions, &mut lconst, actual_constraint, &mut info_ocurrences, field, only_plonk);
        }
    }
    *constraints = lconst;
}


fn treat_constraint_3(
    signals: &mut SignalDefinition,
    substitutions: &mut SHNotNormalized,
    lconst: &mut LinkedList<C>,
    mut work: C,
    field: &BigInt,
    only_plonk: bool
) {
    loop {
        if C::is_empty(&work) {
            break;
        }
        let out = take_signal_3(signals, &work, only_plonk);
        if out.is_none() {
            LinkedList::push_back(lconst, work);
            break;
        }
        let out = out.unwrap();
        signals.delete(out);
        let (coefficient, substitution) = C::clear_signal_from_linear_not_normalized(work, &out, field);
        let in_conflict = substitutions.get(&substitution.from()).cloned();
        if in_conflict.is_none() {
            substitutions.insert(*substitution.from(), (coefficient, substitution));
            break;
        }
        let (in_conflict_coef, in_conflict_subs) = in_conflict.unwrap();
        let right = S::decompose(in_conflict_subs).1;
        let left = S::decompose(substitution).1;
        let exp_coef_right = A::Number {value : in_conflict_coef};
        let exp_coef_left = A::Number {value : coefficient};
        let new_left  = A::mul(&exp_coef_right,&left,field);
        let new_right  = A::mul(&exp_coef_left,&right,field);
        let merge = A::sub(&new_left, &new_right, field);
        work = A::transform_expression_to_air_constraint_form(merge, field).unwrap();
        C::remove_zero_value_coefficients(&mut work);
    }
}

fn treat_unique_constraint_4(
    signals: &mut SignalDefinition4,
    substitutions: &mut SHNotNormalized,
    _lconst: &mut LinkedList<C>,
    work: C,
    info_ocurrences: &mut SignalsInformation,
    signal: usize,
    field: &BigInt,
    only_plonk: bool,
) {

    if only_plonk{ // check if the substitution is valid for the plonk format
        if !work.can_take_plonk_signal(){
            return;
        }
    }

    let (coefficient, substitution) = C::clear_signal_from_linear_not_normalized(work, &signal, field);
    substitutions.insert(*substitution.from(), (coefficient, substitution));
    info_ocurrences.remove_signal(signal);
    signals.delete(signal);
}

fn treat_constraint_4(
    signals: &mut SignalDefinition4,
    substitutions: &mut SHNotNormalized,
    lconst: &mut LinkedList<C>,
    mut work: C,
    info_ocurrences: &mut SignalsInformation,
    field: &BigInt,
    only_plonk: bool,
) {
    loop {
        if C::is_empty(&work) {
            break;
        }
        let out = take_signal_4(signals, info_ocurrences, &work, only_plonk);
        if out.is_none() {
            LinkedList::push_back(lconst, work);
            break;
        }
        let out = out.unwrap();
        let (coefficient, substitution) = C::clear_signal_from_linear_not_normalized(work, &out, field);
        let in_conflict = substitutions.get(&substitution.from()).cloned();
        if in_conflict.is_none() {
            signals.delete(out);
            info_ocurrences.remove_signal(out);
            substitutions.insert(*substitution.from(), (coefficient, substitution));
            break;
        }
        let (in_conflict_coef, in_conflict_subs) = in_conflict.unwrap();
        let right = S::decompose(in_conflict_subs).1;
        let left = S::decompose(substitution).1;
        let exp_coef_right = A::Number {value : in_conflict_coef};
        let exp_coef_left = A::Number {value : coefficient};
        let new_left  = A::mul(&exp_coef_right,&left,field);
        let new_right  = A::mul(&exp_coef_left,&right,field);
        let merge = A::sub(&new_left, &new_right, field);
        work = A::transform_expression_to_air_constraint_form(merge, field).unwrap();
        C::remove_zero_value_coefficients(&mut work);
    }
}

fn take_signal_3(signals: &SignalDefinition, constraint: &C, only_plonk: bool) -> Option<usize> {
    let mut ret = Option::None;
    let keys = constraint.linear().keys();

    if only_plonk{ // check if the substitution is valid for the plonk format
        if !constraint.can_take_plonk_signal(){
            return None;
        }
    }

    for k in keys {
        if signals.can_be_taken(*k) {
            let new_v = ret.map_or(*k, |v| std::cmp::max(*k, v));
            ret = Some(new_v);
        }
    }
    ret
}

fn take_signal_4(signals: &SignalDefinition4, info_ocurrences: &SignalsInformation, constraint: &C, only_plonk: bool) -> Option<usize> {
    let mut ret = Option::None;
    let mut ocurrences_ret: Option<usize> = Option::None;

    let keys = constraint.linear().keys();

    if only_plonk{ // check if the substitution is valid for the plonk format
        if !constraint.can_take_plonk_signal(){
            return None;
        }
    }

    for k in keys {
        if signals.can_be_taken(*k) {
            if signals.is_deleted(*k) {
                ret = Some(*k);
                break;
            }
            else {
                let new_ocurrences = info_ocurrences.signal_to_ocurrences.get(k).unwrap();
                match ocurrences_ret{
                    Some(val_ant) => {
                        if *new_ocurrences < val_ant{
                            ret = Some(*k);
                            ocurrences_ret = Some(*new_ocurrences);
                        }
                        else if *new_ocurrences == val_ant{
                            if ret.unwrap() < *k{
                                ret = Some(*k);
                            }
                        }
                    },
                    None => {
                        ret = Some(*k);
                        ocurrences_ret = Some(*new_ocurrences);
                    }
                } 
            }
        }
    }
    ret
}


fn normalize_substitutions(substitutions: SHNotNormalized, field: &BigInt) -> SH{
    let mut coeffs : Vec<BigInt> = Vec::new();

    for (_signal, (coeff, _sub)) in &substitutions{
        coeffs.push(coeff.clone());
    }
    
    let inverses = modular_arithmetic::multi_inv(&coeffs, field);
    let mut tree : BTreeMap<usize,S> = BTreeMap::new();
    let mut i = 0;
    for (signal, (_coeff, sub)) in substitutions{
        let inv = inverses.get(i).unwrap();
        let arith_sub = A::hashmap_into_arith(sub.to().clone());
        let mult_by_inverse = A::mul(
            &arith_sub, 
            &A::Number {value : inv.clone()}, 
            field
        );
        let new_sub = S::new(signal.clone(), mult_by_inverse).unwrap(); 
        tree.insert(signal, new_sub);
        i = i + 1;
    }
    tree
}

fn take_substitutions_to_be_applied<'a>(sh: &'a HashMap<usize, S>, subs: &S) -> Vec<&'a S> {
    let mut to_be_applied = vec![];
    for s in subs.to().keys() {
        if let Option::Some(s) = sh.get(s) {
            to_be_applied.push(s);
        }
    }
    to_be_applied.shrink_to_fit();
    to_be_applied
}

#[allow(dead_code)]
fn create_nonoverlapping_substitutions(possible_overlap: SH, field: &BigInt) -> HashMap<usize, S> {
    debug_assert!(debug_check_keys_in_order(&possible_overlap));
    let mut no_overlap = HashMap::with_capacity(possible_overlap.len());
    for (s, mut substitution) in possible_overlap {
        let to_be_applied = take_substitutions_to_be_applied(&no_overlap, &substitution);
        for sub in to_be_applied {
            S::apply_substitution(&mut substitution, sub, field);
        }
        no_overlap.insert(s, substitution);
    }
    no_overlap.shrink_to_fit();
    no_overlap
}

fn create_nonoverlapping_substitutions_4(mut possible_overlap: SH, signals: &SignalDefinition4,field: &BigInt) -> HashMap<usize, S> {
    debug_assert!(debug_check_keys_in_order(&possible_overlap));

    let mut no_overlap = HashMap::with_capacity(possible_overlap.len());
    for s in &signals.order_signals{
        let mut substitution = possible_overlap.remove(s).unwrap();
        let to_be_applied = take_substitutions_to_be_applied(&no_overlap, &substitution);
        for sub in to_be_applied {
            S::apply_substitution(&mut substitution, sub, field);
        }
        no_overlap.insert(*s, substitution);
    }
    no_overlap.shrink_to_fit();
    no_overlap
}

pub fn fast_encoded_constraint_substitution(c: &mut C, enc: &HashMap<usize, A>, field: &BigInt)-> bool {
    let signals = C::take_cloned_signals(c);
    let mut applied_substitution = false;
    for signal in signals {
        if let Some(expr) = HashMap::get(enc, &signal) {
            let sub = S::new(signal, expr.clone()).unwrap();
            C::apply_substitution(c, &sub, field);
            applied_substitution = true;
        }
    }
    applied_substitution
}

pub fn fast_encoded_substitution_substitution(s: &mut S, enc: &HashMap<usize, A>, field: &BigInt) {
    let signals = S::take_cloned_signals(s);
    for signal in signals {
        if let Some(expr) = HashMap::get(enc, &signal) {
            let sub = S::new(signal, expr.clone()).unwrap();
            S::apply_substitution(s, &sub, field);
        }
    }
    S::rmv_zero_coefficients(s)
}

pub fn build_encoded_fast_substitutions(fast_sub: LinkedList<S>) -> HashMap<usize, A> {
    let mut encoded = HashMap::with_capacity(LinkedList::len(&fast_sub));
    for sub in fast_sub {
        let (from, to) = S::decompose(sub);
        HashMap::insert(&mut encoded, from, to);
    }
    encoded
}

pub struct Config<T> {
    pub field: BigInt,
    pub constraints: LinkedList<C>,
    pub forbidden: T,
    pub num_signals: usize,
    pub use_old_heuristics: bool,
    pub only_plonk: bool,

}

pub struct Simplified {
    pub constraints: LinkedList<C>,
    pub substitutions: LinkedList<S>,
    pub removed: LinkedList<usize>,
}

pub fn full_simplification<T>(config: Config<T>) -> Simplified
where
    T: AsRef<HashSet<usize>>,
{
    //debug_new_substitutions(&config);
    let min = 350;
    let max = 1000000;
    let apply_less_ocurrences = 
        config.constraints.len() >= min && 
        config.constraints.len() < max && 
        !config.use_old_heuristics;

    let field = config.field;
    let mut constraints = config.constraints;
    let mut holder = SHNotNormalized::new();
    let normalized_holder: SH;
    let non_overlapping: HashMap<usize, S>;

    if apply_less_ocurrences{
        let mut signals = SignalDefinition4 { forbidden: config.forbidden.as_ref(), deleted_symbols: HashSet::new(),  order_signals: LinkedList::new() };
        substitution_process_4(&mut signals, &mut constraints, &mut holder, config.num_signals, &field, config.only_plonk);
        normalized_holder = normalize_substitutions(holder, &field);
        non_overlapping = create_nonoverlapping_substitutions_4(normalized_holder, &signals, &field);
    }
    else{
        let mut signals = SignalDefinition { forbidden: config.forbidden.as_ref(), deleted_symbols: HashSet::new() };
        substitution_process_3(&mut signals, &mut constraints, &mut holder, &field, config.only_plonk);
        normalized_holder = normalize_substitutions(holder, &field);
        non_overlapping = create_nonoverlapping_substitutions(normalized_holder, &field);
    }
    let mut substitutions = LinkedList::new();
    let mut removed = LinkedList::new();
    for (s, v) in non_overlapping {
        LinkedList::push_back(&mut removed, s);
        LinkedList::push_back(&mut substitutions, v);
    }

    Simplified { constraints, substitutions, removed }
}

