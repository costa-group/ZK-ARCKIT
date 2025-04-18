use super::modular_arithmetic;
pub use super::modular_arithmetic::ArithmeticError;
use num_bigint::BigInt;
use num_traits::{ToPrimitive, Zero};
use std::collections::{HashMap, HashSet, BTreeSet};
use std::fmt::{Display, Formatter};
use std::hash::Hash;

pub enum ArithmeticExpression<C>
where
    C: Hash + Eq,
{
    Number {
        value: BigInt,
    },
    Signal {
        symbol: C,
    },
    Linear {
        // Represents the expression: c1*s1 + .. + cn*sn + C
        // where c1..cn are integers modulo a prime and
        // s1..sn are signals. C is a constant value
        coefficients: HashMap<C, BigInt>,
    },
    Quadratic {
        // Is a quadratic expression of the form:
        //              a*b + c
        // Where a,b and c are linear expression
        a: HashMap<C, BigInt>,
        b: HashMap<C, BigInt>,
        c: HashMap<C, BigInt>,
    },
    NonQuadratic,
}
impl<C: Default + Clone + Display + Hash + Eq> Display for ArithmeticExpression<C> {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        use ArithmeticExpression::*;
        let msg = match self {
            Number { value } => value.to_str_radix(10),
            Signal { symbol } => format!("{}", symbol),
            NonQuadratic => "Non quadratic".to_string(),
            Linear { coefficients } => ArithmeticExpression::string_from_coefficients(coefficients),
            Quadratic { a, b, c } => {
                let a_string = ArithmeticExpression::string_from_coefficients(a);
                let b_string = ArithmeticExpression::string_from_coefficients(b);
                let c_string = ArithmeticExpression::string_from_coefficients(c);
                format!("({})*({}) + ({})", a_string, b_string, c_string)
            }
        };
        f.write_str(msg.as_str())
    }
}

impl<C: Default + Clone + Display + Hash + Eq> Clone for ArithmeticExpression<C> {
    fn clone(&self) -> Self {
        use ArithmeticExpression::*;
        match self {
            Number { value } => Number { value: value.clone() },
            Signal { symbol } => Signal { symbol: symbol.clone() },
            Linear { coefficients } => Linear { coefficients: coefficients.clone() },
            Quadratic { a, b, c } => Quadratic { a: a.clone(), b: b.clone(), c: c.clone() },
            NonQuadratic => NonQuadratic,
        }
    }
}

impl<C: Default + Clone + Display + Hash + Eq> Eq for ArithmeticExpression<C> {}
impl<C: Default + Clone + Display + Hash + Eq> PartialEq for ArithmeticExpression<C> {
    fn eq(&self, other: &Self) -> bool {
        use ArithmeticExpression::*;
        match (self, other) {
            (Number { value: v_0 }, Number { value: v_1 }) => *v_0 == *v_1,
            (Signal { symbol: s_0 }, Signal { symbol: s_1 }) => *s_0 == *s_1,
            (Linear { coefficients: c_0 }, Linear { coefficients: c_1 }) => *c_0 == *c_1,
            (Quadratic { a: a_0, b: b_0, c: c_0 }, Quadratic { a: a_1, b: b_1, c: c_1 }) => {
                *a_0 == *a_1 && *b_0 == *b_1 && *c_0 == *c_1
            }
            _ => false,
        }
    }
}

impl<C: Default + Clone + Display + Hash + Eq> Default for ArithmeticExpression<C> {
    fn default() -> Self {
        ArithmeticExpression::NonQuadratic
    }
}

impl<C: Default + Clone + Display + Hash + Eq> ArithmeticExpression<C> {
    pub fn new() -> ArithmeticExpression<C> {
        ArithmeticExpression::default()
    }

    // printing utils
    fn string_from_coefficients(coefficients: &HashMap<C, BigInt>) -> String {
        let mut string_coefficients = "".to_string();
        for (signal, value) in coefficients {
            let component_string = if value.is_zero() {
                "".to_string()
            } else if signal.eq(&ArithmeticExpression::constant_coefficient()) {
                format!("{}+", value.to_str_radix(10))
            } else {
                format!("{}*{}+", signal, value.to_str_radix(10))
            };
            string_coefficients.push_str(component_string.as_str());
        }
        string_coefficients.pop();
        string_coefficients
    }

    // constraint generation utils
    // transforms constraints into a constraint, None if the expression was non-quadratic
    pub fn transform_expression_to_constraint_form(
        arithmetic_expression: ArithmeticExpression<C>,
        field: &BigInt,
    ) -> Option<Constraint<C>> {
        use ArithmeticExpression::*;
        let mut a = HashMap::new();
        let mut b = HashMap::new();
        let mut c = HashMap::new();
        ArithmeticExpression::initialize_hashmap_for_expression(&mut a);
        ArithmeticExpression::initialize_hashmap_for_expression(&mut b);
        ArithmeticExpression::initialize_hashmap_for_expression(&mut c);
        match arithmetic_expression {
            NonQuadratic => {
                return Option::None;
            }
            Quadratic { a: old_a, b: old_b, c: old_c } => {
                a = old_a;
                b = old_b;
                c = old_c;
            }
            Number { value } => {
                c.insert(ArithmeticExpression::constant_coefficient(), value);
            }
            Signal { symbol } => {
                c.insert(symbol, BigInt::from(1));
            }
            Linear { coefficients } => {
                c = coefficients;
            }
        }
        ArithmeticExpression::multiply_coefficients_by_constant(&BigInt::from(-1), &mut c, field);
        Option::Some(Constraint::new(a, b, c))
    }


    // !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    // All the operations must ensure that the Hashmaps used
    // to construct Expressions contain the empty string
    // as key.
    // Therefore the function 'initialize_hashmap_for_expression'
    // is meant to be call each time a hashmap is going to be
    // part of a Expression
    // !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    fn constant_coefficient() -> C {
        C::default()
    }
    fn initialize_hashmap_for_expression(initial: &mut HashMap<C, BigInt>) {
        initial
            .entry(ArithmeticExpression::constant_coefficient())
            .or_insert_with(|| BigInt::from(0));
        debug_assert!(ArithmeticExpression::valid_hashmap_for_expression(initial));
    }
    fn valid_hashmap_for_expression(h: &HashMap<C, BigInt>) -> bool {
        let cc = ArithmeticExpression::constant_coefficient();
        h.contains_key(&cc)
    }
    fn initialize_symbol_in_coefficients(symbol: &C, coefficients: &mut HashMap<C, BigInt>) {
        debug_assert!(ArithmeticExpression::valid_hashmap_for_expression(coefficients));
        if !coefficients.contains_key(symbol) {
            coefficients.insert(symbol.clone(), BigInt::from(0));
        }
        debug_assert!(ArithmeticExpression::valid_hashmap_for_expression(coefficients));
    }
    fn add_constant_to_coefficients(
        value: &BigInt,
        coefficients: &mut HashMap<C, BigInt>,
        field: &BigInt,
    ) {
        debug_assert!(ArithmeticExpression::valid_hashmap_for_expression(coefficients));
        let cc: C = ArithmeticExpression::constant_coefficient();
        coefficients.insert(
            cc.clone(),
            modular_arithmetic::add(coefficients.get(&cc).unwrap(), value, field),
        );
        debug_assert!(ArithmeticExpression::valid_hashmap_for_expression(coefficients));
    }
    fn add_symbol_to_coefficients(
        symbol: &C,
        coefficient: &BigInt,
        coefficients: &mut HashMap<C, BigInt>,
        field: &BigInt,
    ) {
        debug_assert!(ArithmeticExpression::valid_hashmap_for_expression(coefficients));
        ArithmeticExpression::initialize_symbol_in_coefficients(symbol, coefficients);
        coefficients.insert(
            symbol.clone(),
            modular_arithmetic::add(coefficients.get(symbol).unwrap(), coefficient, field),
        );
        debug_assert!(ArithmeticExpression::valid_hashmap_for_expression(coefficients));
    }
    fn add_coefficients_to_coefficients(
        coefficients_0: &HashMap<C, BigInt>,
        coefficients_1: &mut HashMap<C, BigInt>,
        field: &BigInt,
    ) {
        debug_assert!(ArithmeticExpression::valid_hashmap_for_expression(coefficients_0));
        debug_assert!(ArithmeticExpression::valid_hashmap_for_expression(coefficients_1));
        for (symbol, coefficient) in coefficients_0 {
            ArithmeticExpression::add_symbol_to_coefficients(
                symbol,
                coefficient,
                coefficients_1,
                field,
            );
        }
        debug_assert!(ArithmeticExpression::valid_hashmap_for_expression(coefficients_0));
        debug_assert!(ArithmeticExpression::valid_hashmap_for_expression(coefficients_1));
    }
    fn multiply_coefficients_by_constant(
        constant: &BigInt,
        coefficients: &mut HashMap<C, BigInt>,
        field: &BigInt,
    ) {
        debug_assert!(ArithmeticExpression::valid_hashmap_for_expression(coefficients));
        for value in coefficients.values_mut() {
            *value = modular_arithmetic::mul(value, constant, field);
        }
        debug_assert!(ArithmeticExpression::valid_hashmap_for_expression(coefficients));
    }
    fn divide_coefficients_by_constant(
        constant: &BigInt,
        coefficients: &mut HashMap<C, BigInt>,
        field: &BigInt,
    ) -> Result<(), ArithmeticError> {
        debug_assert!(ArithmeticExpression::valid_hashmap_for_expression(coefficients));
        let inverse_constant = modular_arithmetic::div(
            &BigInt::from(1),
            constant,
            &field
        )?;
        ArithmeticExpression::multiply_coefficients_by_constant(&inverse_constant, coefficients, field);
        debug_assert!(ArithmeticExpression::valid_hashmap_for_expression(coefficients));
        Result::Ok(())
    }

    pub fn add(
        left: &ArithmeticExpression<C>,
        right: &ArithmeticExpression<C>,
        field: &BigInt,
    ) -> ArithmeticExpression<C> {
        use ArithmeticExpression::*;
        match (left, right) {
            (NonQuadratic, _) | (_, NonQuadratic) | (Quadratic { .. }, Quadratic { .. }) => {
                NonQuadratic
            }
            (Number { value: v_0 }, Number { value: v_1 }) => {
                Number { value: modular_arithmetic::add(v_0, v_1, field) }
            }
            (Number { value }, Signal { symbol }) | (Signal { symbol }, Number { value }) => {
                let mut coefficients = HashMap::new();
                ArithmeticExpression::initialize_hashmap_for_expression(&mut coefficients);
                ArithmeticExpression::add_constant_to_coefficients(value, &mut coefficients, field);
                ArithmeticExpression::add_symbol_to_coefficients(
                    symbol,
                    &BigInt::from(1),
                    &mut coefficients,
                    field,
                );
                Linear { coefficients }
            }
            (Number { value }, Linear { coefficients })
            | (Linear { coefficients }, Number { value }) => {
                let mut n_coefficients = coefficients.clone();
                ArithmeticExpression::add_constant_to_coefficients(
                    value,
                    &mut n_coefficients,
                    field,
                );
                Linear { coefficients: n_coefficients }
            }
            (Number { value }, Quadratic { a, b, c })
            | (Quadratic { a, b, c }, Number { value }) => {
                let mut n_c = c.clone();
                ArithmeticExpression::add_constant_to_coefficients(value, &mut n_c, field);
                Quadratic { a: a.clone(), b: b.clone(), c: n_c }
            }
            (Signal { symbol: symbol_0 }, Signal { symbol: symbol_1 }) => {
                let mut coefficients = HashMap::new();
                ArithmeticExpression::initialize_hashmap_for_expression(&mut coefficients);
                ArithmeticExpression::add_symbol_to_coefficients(
                    symbol_0,
                    &BigInt::from(1),
                    &mut coefficients,
                    field,
                );
                ArithmeticExpression::add_symbol_to_coefficients(
                    symbol_1,
                    &BigInt::from(1),
                    &mut coefficients,
                    field,
                );
                Linear { coefficients }
            }
            (Signal { symbol }, Linear { coefficients })
            | (Linear { coefficients }, Signal { symbol }) => {
                let mut n_coefficients = coefficients.clone();
                ArithmeticExpression::add_symbol_to_coefficients(
                    symbol,
                    &BigInt::from(1),
                    &mut n_coefficients,
                    field,
                );
                Linear { coefficients: n_coefficients }
            }
            (Signal { symbol }, Quadratic { a, b, c })
            | (Quadratic { a, b, c }, Signal { symbol }) => {
                let mut coefficients = c.clone();
                ArithmeticExpression::add_symbol_to_coefficients(
                    symbol,
                    &BigInt::from(1),
                    &mut coefficients,
                    field,
                );
                Quadratic { a: a.clone(), b: b.clone(), c: coefficients }
            }
            (Linear { coefficients: coefficients_0 }, Linear { coefficients: coefficients_1 }) => {
                let mut n_coefficients = coefficients_1.clone();
                ArithmeticExpression::add_coefficients_to_coefficients(
                    coefficients_0,
                    &mut n_coefficients,
                    field,
                );
                Linear { coefficients: n_coefficients }
            }
            (Linear { coefficients }, Quadratic { a, b, c })
            | (Quadratic { a, b, c }, Linear { coefficients }) => {
                let mut coefficients_1 = c.clone();
                ArithmeticExpression::add_coefficients_to_coefficients(
                    coefficients,
                    &mut coefficients_1,
                    field,
                );
                Quadratic { a: a.clone(), b: b.clone(), c: coefficients_1 }
            }
        }
    }

    pub fn mul(
        left: &ArithmeticExpression<C>,
        right: &ArithmeticExpression<C>,
        field: &BigInt,
    ) -> ArithmeticExpression<C> {
        use ArithmeticExpression::*;
        match (left, right) {
            (NonQuadratic, _)
            | (_, NonQuadratic)
            | (Quadratic { .. }, Quadratic { .. })
            | (Quadratic { .. }, Linear { .. })
            | (Linear { .. }, Quadratic { .. })
            | (Quadratic { .. }, Signal { .. })
            | (Signal { .. }, Quadratic { .. }) => NonQuadratic,
            (Number { value: value_0 }, Number { value: value_1 }) => {
                Number { value: modular_arithmetic::mul(value_0, value_1, field) }
            }
            (Number { value }, Signal { symbol }) | (Signal { symbol }, Number { value }) => {
                let mut coefficients = HashMap::new();
                ArithmeticExpression::initialize_hashmap_for_expression(&mut coefficients);
                ArithmeticExpression::add_symbol_to_coefficients(
                    symbol,
                    value,
                    &mut coefficients,
                    field,
                );
                Linear { coefficients }
            }
            (Number { value }, Linear { coefficients })
            | (Linear { coefficients }, Number { value }) => {
                let mut n_coefficients = coefficients.clone();
                ArithmeticExpression::multiply_coefficients_by_constant(
                    value,
                    &mut n_coefficients,
                    field,
                );
                Linear { coefficients: n_coefficients }
            }
            (Number { value }, Quadratic { a, b, c })
            | (Quadratic { a, b, c }, Number { value }) => {
                let mut n_a = a.clone();
                let n_b = b.clone();
                let mut n_c = c.clone();
                ArithmeticExpression::multiply_coefficients_by_constant(value, &mut n_a, field);
                ArithmeticExpression::multiply_coefficients_by_constant(value, &mut n_c, field);
                Quadratic { a: n_a, b: n_b, c: n_c }
            }
            (Signal { symbol: symbol_0 }, Signal { symbol: symbol_1 }) => {
                let mut a = HashMap::new();
                let mut b = HashMap::new();
                let mut c = HashMap::new();
                ArithmeticExpression::initialize_hashmap_for_expression(&mut a);
                ArithmeticExpression::initialize_hashmap_for_expression(&mut b);
                ArithmeticExpression::initialize_hashmap_for_expression(&mut c);
                ArithmeticExpression::add_symbol_to_coefficients(
                    symbol_0,
                    &BigInt::from(1),
                    &mut a,
                    field,
                );
                ArithmeticExpression::add_symbol_to_coefficients(
                    symbol_1,
                    &BigInt::from(1),
                    &mut b,
                    field,
                );
                Quadratic { a, b, c }
            }
            (Signal { symbol }, Linear { coefficients })
            | (Linear { coefficients }, Signal { symbol }) => {
                let a = coefficients.clone();
                let mut b = HashMap::new();
                let mut c = HashMap::new();
                ArithmeticExpression::initialize_hashmap_for_expression(&mut b);
                ArithmeticExpression::initialize_hashmap_for_expression(&mut c);
                ArithmeticExpression::add_symbol_to_coefficients(
                    symbol,
                    &BigInt::from(1),
                    &mut b,
                    field,
                );
                Quadratic { a, b, c }
            }
            (Linear { coefficients: coefficients_0 }, Linear { coefficients: coefficients_1 }) => {
                let a = coefficients_0.clone();
                let b = coefficients_1.clone();
                let mut c = HashMap::new();
                ArithmeticExpression::initialize_hashmap_for_expression(&mut c);
                Quadratic { a, b, c }
            }
        }
    }
    pub fn sub(
        left: &ArithmeticExpression<C>,
        right: &ArithmeticExpression<C>,
        field: &BigInt,
    ) -> ArithmeticExpression<C> {
        use ArithmeticExpression::*;
        let minus_one = Number { value: BigInt::from(-1) };
        let step_one = ArithmeticExpression::mul(&minus_one, right, field);
        ArithmeticExpression::add(left, &step_one, field)
    }

    pub fn div(
        left: &ArithmeticExpression<C>,
        right: &ArithmeticExpression<C>,
        field: &BigInt,
    ) -> Result<ArithmeticExpression<C>, ArithmeticError> {
        use ArithmeticExpression::*;
        match (left, right) {
            (Number { value: value_0 }, Number { value: value_1 }) => {
                let value = modular_arithmetic::div(value_0, value_1, field)?;
                Result::Ok(Number { value })
            }
            (Signal { symbol }, Number { value }) => {
                let mut coefficients = HashMap::new();
                ArithmeticExpression::initialize_hashmap_for_expression(&mut coefficients);
                ArithmeticExpression::add_symbol_to_coefficients(
                    symbol,
                    &BigInt::from(1),
                    &mut coefficients,
                    field,
                );
                ArithmeticExpression::divide_coefficients_by_constant(
                    value,
                    &mut coefficients,
                    field,
                )?;
                Result::Ok(Linear { coefficients })
            }
            (Linear { coefficients }, Number { value }) => {
                let mut coefficients = coefficients.clone();
                ArithmeticExpression::divide_coefficients_by_constant(
                    value,
                    &mut coefficients,
                    field,
                )?;
                Result::Ok(Linear { coefficients })
            }
            (Quadratic { a, b, c }, Number { value }) => {
                let mut a = a.clone();
                let b = b.clone();
                let mut c = c.clone();
                ArithmeticExpression::divide_coefficients_by_constant(value, &mut a, field)?;
                ArithmeticExpression::divide_coefficients_by_constant(value, &mut c, field)?;
                Result::Ok(Quadratic { a, b, c })
            }
            _ => Result::Ok(NonQuadratic),
        }
    }
    pub fn idiv(
        left: &ArithmeticExpression<C>,
        right: &ArithmeticExpression<C>,
        field: &BigInt,
    ) -> Result<ArithmeticExpression<C>, ArithmeticError> {
        use ArithmeticExpression::*;
        match (left, right) {
            (Number { value: value_0 }, Number { value: value_1 }) => {
                let value = modular_arithmetic::idiv(value_0, value_1, field)?;
                Result::Ok(Number { value })
            }
            _ => Result::Ok(NonQuadratic),
        }
    }
    pub fn mod_op(
        left: &ArithmeticExpression<C>,
        right: &ArithmeticExpression<C>,
        field: &BigInt,
    ) -> Result<ArithmeticExpression<C>, ArithmeticError> {
        use ArithmeticExpression::*;
        if let (Number { value: value_0 }, Number { value: value_1 }) = (left, right) {
            let value = modular_arithmetic::mod_op(value_0, value_1, field)?;
            Result::Ok(Number { value })
        } else {
            Result::Ok(NonQuadratic)
        }
    }
    pub fn pow(
        left: &ArithmeticExpression<C>,
        right: &ArithmeticExpression<C>,
        field: &BigInt,
    ) -> ArithmeticExpression<C> {
        use ArithmeticExpression::*;
        match (left, right) {
            (Number { value: value_0 }, Number { value: value_1 }) => {
                let value = modular_arithmetic::pow(value_0, value_1, field);
                Number { value }
            }
            (Signal { symbol }, Number { value }) if *value == BigInt::from(2) => {      
                let left = Signal { symbol: symbol.clone() };
                let right = Signal { symbol: symbol.clone() };
                ArithmeticExpression::mul(&left, &right, field)
            }
            (Linear { coefficients }, Number {value}) if *value == BigInt::from(2) => {
                let left = Linear { coefficients: coefficients.clone() };
                let right = Linear { coefficients: coefficients.clone() };
                ArithmeticExpression::mul(&left, &right, field)
            }
            _ => NonQuadratic,
        }
    }
    pub fn prefix_sub(elem: &ArithmeticExpression<C>, field: &BigInt) -> ArithmeticExpression<C> {
        use ArithmeticExpression::*;
        let minus_one = Number { value: BigInt::from(-1) };
        ArithmeticExpression::mul(elem, &minus_one, field)
    }

    // Bit operations
    pub fn complement_256(
        elem: &ArithmeticExpression<C>,
        field: &BigInt,
    ) -> ArithmeticExpression<C> {
        use ArithmeticExpression::*;
        if let Number { value } = elem {
            Number { value: modular_arithmetic::complement_256(value, field) }
        } else {
            NonQuadratic
        }
    }
    pub fn shift_l(
        left: &ArithmeticExpression<C>,
        right: &ArithmeticExpression<C>,
        field: &BigInt,
    ) -> Result<ArithmeticExpression<C>, ArithmeticError> {
        use ArithmeticExpression::*;
        if let (Number { value: value_0 }, Number { value: value_1 }) = (left, right) {
            let shifted_elem = modular_arithmetic::shift_l(value_0, value_1, field)?;
            Result::Ok(Number { value: shifted_elem })
        } else {
            Result::Ok(NonQuadratic)
        }
    }
    pub fn shift_r(
        left: &ArithmeticExpression<C>,
        right: &ArithmeticExpression<C>,
        field: &BigInt,
    ) -> Result<ArithmeticExpression<C>, ArithmeticError> {
        use ArithmeticExpression::*;
        if let (Number { value: value_0 }, Number { value: value_1 }) = (left, right) {
            let shifted_elem = modular_arithmetic::shift_r(value_0, value_1, field)?;
            Result::Ok(Number { value: shifted_elem })
        } else {
            Result::Ok(NonQuadratic)
        }
    }
    pub fn bit_or(
        left: &ArithmeticExpression<C>,
        right: &ArithmeticExpression<C>,
        field: &BigInt,
    ) -> ArithmeticExpression<C> {
        use ArithmeticExpression::*;
        if let (Number { value: value_0 }, Number { value: value_1 }) = (left, right) {
            let value = modular_arithmetic::bit_or(value_0, value_1, field);
            Number { value }
        } else {
            NonQuadratic
        }
    }
    pub fn bit_and(
        left: &ArithmeticExpression<C>,
        right: &ArithmeticExpression<C>,
        field: &BigInt,
    ) -> ArithmeticExpression<C> {
        use ArithmeticExpression::*;
        if let (Number { value: value_0 }, Number { value: value_1 }) = (left, right) {
            let value = modular_arithmetic::bit_and(value_0, value_1, field);
            Number { value }
        } else {
            NonQuadratic
        }
    }
    pub fn bit_xor(
        left: &ArithmeticExpression<C>,
        right: &ArithmeticExpression<C>,
        field: &BigInt,
    ) -> ArithmeticExpression<C> {
        use ArithmeticExpression::*;
        if let (Number { value: value_0 }, Number { value: value_1 }) = (left, right) {
            let value = modular_arithmetic::bit_xor(value_0, value_1, field);
            Number { value }
        } else {
            NonQuadratic
        }
    }

    // Boolean operations
    pub fn get_boolean_equivalence(elem: &ArithmeticExpression<C>, field: &BigInt) -> Option<bool> {
        use ArithmeticExpression::*;
        if let Number { value } = elem {
            Option::Some(modular_arithmetic::as_bool(value, field))
        } else {
            Option::None
        }
    }
    pub fn not(elem: &ArithmeticExpression<C>, field: &BigInt) -> ArithmeticExpression<C> {
        use ArithmeticExpression::*;
        if let Number { value } = elem {
            let value = modular_arithmetic::not(value, field);
            Number { value }
        } else {
            NonQuadratic
        }
    }
    pub fn bool_or(
        left: &ArithmeticExpression<C>,
        right: &ArithmeticExpression<C>,
        field: &BigInt,
    ) -> ArithmeticExpression<C> {
        use ArithmeticExpression::*;
        if let (Number { value: value_0 }, Number { value: value_1 }) = (left, right) {
            let value = modular_arithmetic::bool_or(value_0, value_1, field);
            Number { value }
        } else {
            NonQuadratic
        }
    }
    pub fn bool_and(
        left: &ArithmeticExpression<C>,
        right: &ArithmeticExpression<C>,
        field: &BigInt,
    ) -> ArithmeticExpression<C> {
        use ArithmeticExpression::*;
        if let (Number { value: value_0 }, Number { value: value_1 }) = (left, right) {
            let value = modular_arithmetic::bool_and(value_0, value_1, field);
            Number { value }
        } else {
            NonQuadratic
        }
    }
    pub fn eq(
        left: &ArithmeticExpression<C>,
        right: &ArithmeticExpression<C>,
        field: &BigInt,
    ) -> ArithmeticExpression<C> {
        use ArithmeticExpression::*;
        if let (Number { value: value_0 }, Number { value: value_1 }) = (left, right) {
            let value = modular_arithmetic::eq(value_0, value_1, field);
            Number { value }
        } else {
            NonQuadratic
        }
    }
    pub fn not_eq(
        left: &ArithmeticExpression<C>,
        right: &ArithmeticExpression<C>,
        field: &BigInt,
    ) -> ArithmeticExpression<C> {
        use ArithmeticExpression::*;
        if let (Number { value: value_0 }, Number { value: value_1 }) = (left, right) {
            let value = modular_arithmetic::not_eq(value_0, value_1, field);
            Number { value }
        } else {
            NonQuadratic
        }
    }
    pub fn lesser(
        left: &ArithmeticExpression<C>,
        right: &ArithmeticExpression<C>,
        field: &BigInt,
    ) -> ArithmeticExpression<C> {
        use ArithmeticExpression::*;
        if let (Number { value: value_0 }, Number { value: value_1 }) = (left, right) {
            let value = modular_arithmetic::lesser(value_0, value_1, field);
            Number { value }
        } else {
            NonQuadratic
        }
    }
    pub fn lesser_eq(
        left: &ArithmeticExpression<C>,
        right: &ArithmeticExpression<C>,
        field: &BigInt,
    ) -> ArithmeticExpression<C> {
        use ArithmeticExpression::*;
        if let (Number { value: value_0 }, Number { value: value_1 }) = (left, right) {
            let value = modular_arithmetic::lesser_eq(value_0, value_1, field);
            Number { value }
        } else {
            NonQuadratic
        }
    }
    pub fn greater(
        left: &ArithmeticExpression<C>,
        right: &ArithmeticExpression<C>,
        field: &BigInt,
    ) -> ArithmeticExpression<C> {
        use ArithmeticExpression::*;
        if let (Number { value: value_0 }, Number { value: value_1 }) = (left, right) {
            let value = modular_arithmetic::greater(value_0, value_1, field);
            Number { value }
        } else {
            NonQuadratic
        }
    }
    pub fn greater_eq(
        left: &ArithmeticExpression<C>,
        right: &ArithmeticExpression<C>,
        field: &BigInt,
    ) -> ArithmeticExpression<C> {
        use ArithmeticExpression::*;
        if let (Number { value: value_0 }, Number { value: value_1 }) = (left, right) {
            let value = modular_arithmetic::greater_eq(value_0, value_1, field);
            Number { value }
        } else {
            NonQuadratic
        }
    }

    // Utils
    pub fn apply_substitutions(
        expr: &mut ArithmeticExpression<C>,
        substitution: &Substitution<C>,
        field: &BigInt,
    ) {
        use ArithmeticExpression::*;
        match expr {
            Linear { coefficients } => {
               raw_substitution(coefficients, substitution, field);
               *coefficients = remove_zero_value_coefficients(std::mem::take(coefficients));
            }
            Signal { symbol } if *symbol == substitution.from => {
                *expr = Linear { coefficients: substitution.to.clone() };
            }
            Quadratic { a, b, c } => {
                raw_substitution(a, substitution, field);
                *a = remove_zero_value_coefficients(std::mem::take(a));
                raw_substitution(b, substitution, field);
                *b = remove_zero_value_coefficients(std::mem::take(b));
                raw_substitution(c, substitution, field);
                *c = remove_zero_value_coefficients(std::mem::take(c));
            }
            _ => {}
        }
    }
    pub fn get_usize(expr: &ArithmeticExpression<C>) -> Option<usize> {
        use ArithmeticExpression::*;
        if let Number { value } = expr {
            value.to_usize()
        } else {
            Option::None
        }
    }
    pub fn is_number(&self) -> bool {
        matches!(self, ArithmeticExpression::Number { .. })
    }
    pub fn is_nonquadratic(&self) -> bool {
        matches!(self, ArithmeticExpression::NonQuadratic)
    }
    pub fn is_quadratic(&self) -> bool {
        matches!(self, ArithmeticExpression::Quadratic { .. })
    }
    pub fn is_linear(&self) -> bool {
        matches!(self, ArithmeticExpression::Linear { .. })
    }

    pub fn hashmap_into_arith(mut map: HashMap<C, BigInt>) -> ArithmeticExpression<C> {
        let c: C = ArithmeticExpression::constant_coefficient();
        let expr = if HashMap::len(&map) == 1 && HashMap::contains_key(&map, &c) {
            let value = HashMap::remove(&mut map, &c).unwrap();
            ArithmeticExpression::Number { value }
        } else if HashMap::len(&map) == 1 {
            let mut values: Vec<_> = map.values().cloned().collect();
            let mut symbols: Vec<_> = map.keys().cloned().collect();
            let symbol = symbols.pop().unwrap();
            let value = values.pop().unwrap();
            if value == BigInt::from(1) {
                ArithmeticExpression::Signal { symbol }
            } else {
                ArithmeticExpression::initialize_hashmap_for_expression(&mut map);
                ArithmeticExpression::Linear { coefficients: map }
            }
        } else {
            ArithmeticExpression::initialize_hashmap_for_expression(&mut map);
            ArithmeticExpression::Linear { coefficients: map }
        };
        expr
    }
}

impl<C: Default + Clone + Display + Hash + Eq + PartialOrd + Ord> ArithmeticExpression<C> {

    // constraint generation utils
    // transforms constraints into a constraint, None if the expression was non-quadratic
    pub fn transform_expression_to_air_constraint_form(
        arithmetic_expression: ArithmeticExpression<C>,
        field: &BigInt,
    ) -> Option<AIRConstraint<C>> {
        use ArithmeticExpression::*;
        let mut linear = HashMap::new();
        let muls = HashMap::new();

        ArithmeticExpression::initialize_hashmap_for_expression(&mut linear);
        match arithmetic_expression {
            NonQuadratic => {
                return Option::None;
            }
            Quadratic { a: _old_a, b: _old_b, c: _old_c } => {
                //TODO
                unreachable!();
            }
            Number { value } => {
                linear.insert(ArithmeticExpression::constant_coefficient(), value);
            }
            Signal { symbol } => {
                linear.insert(symbol, BigInt::from(1));
            }
            Linear { coefficients } => {
                linear = coefficients;
            }
        }
        ArithmeticExpression::multiply_coefficients_by_constant(&BigInt::from(-1), &mut linear, field);
        Option::Some(AIRConstraint::new(muls, linear))
    }
}

// ******************************** Constraint Definition ********************************

/*
    Wrapper for linear expression that will be used as a substitution
*/

#[derive(Clone)]
pub struct Substitution<C>
where
    C: Hash + Eq,
{
    pub(crate) from: C,
    pub(crate) to: HashMap<C, BigInt>,
}
impl<C: Default + Clone + Display + Hash + Eq> Substitution<C> {
    // Substitution public utils
    pub fn new(from: C, to: ArithmeticExpression<C>) -> Option<Substitution<C>> {
        use ArithmeticExpression::*;
        match to {
            Number { value } => {
                let mut to = HashMap::new();
                to.insert(ArithmeticExpression::constant_coefficient(), value);
                Option::Some(Substitution { from, to })
            }
            Signal { symbol } => {
                let mut to = HashMap::new();
                to.insert(symbol, BigInt::from(1));
                Option::Some(Substitution { from, to })
            }
            Linear { coefficients: to } if !to.contains_key(&from) => {
                Option::Some(Substitution { from, to })
            }
            _ => Option::None,
        }
    }

    pub fn apply_correspondence_and_drop<K>(
        substitution: Substitution<C>,
        symbol_correspondence: &HashMap<C, K>,
    ) -> Substitution<K>
    where
        K: Default + Clone + Display + Hash + Eq,
    {
        Substitution::apply_correspondence(&substitution, symbol_correspondence)
    }

    pub fn constant_coefficient() -> C {
        ArithmeticExpression::constant_coefficient()
    }

    pub fn apply_correspondence<K>(
        substitution: &Substitution<C>,
        symbol_correspondence: &HashMap<C, K>,
    ) -> Substitution<K>
    where
        K: Default + Clone + Display + Hash + Eq,
    {
        let from = symbol_correspondence.get(&substitution.from).unwrap().clone();
        let to = apply_raw_correspondence(&substitution.to, symbol_correspondence);
        Substitution { to, from }
    }

    pub fn apply_substitution(src: &mut Substitution<C>, change: &Substitution<C>, field: &BigInt) {
        raw_substitution(&mut src.to, change, field);
    }

    pub fn substitution_into_constraint(
        substitution: Substitution<C>,
        field: &BigInt,
    ) -> Constraint<C> {
        let symbol = substitution.from;
        let mut coefficients = substitution.to;
        ArithmeticExpression::initialize_hashmap_for_expression(&mut coefficients);
        coefficients.insert(symbol, BigInt::from(-1 % field));
        let arith = ArithmeticExpression::Linear { coefficients };
        ArithmeticExpression::transform_expression_to_constraint_form(arith, field).unwrap()
    }

    pub fn decompose(substitution: Substitution<C>) -> (C, ArithmeticExpression<C>) {
        let c: C = ArithmeticExpression::constant_coefficient();
        let mut to = substitution.to;
        let right = if HashMap::len(&to) == 1 && HashMap::contains_key(&to, &c) {
            let value = HashMap::remove(&mut to, &c).unwrap();
            ArithmeticExpression::Number { value }
        } else if HashMap::len(&to) == 1 {
            let mut values: Vec<_> = to.values().cloned().collect();
            let mut symbols: Vec<_> = to.keys().cloned().collect();
            let symbol = symbols.pop().unwrap();
            let value = values.pop().unwrap();
            if value == BigInt::from(1) {
                ArithmeticExpression::Signal { symbol }
            } else {
                ArithmeticExpression::initialize_hashmap_for_expression(&mut to);
                ArithmeticExpression::Linear { coefficients: to }
            }
        } else {
            ArithmeticExpression::initialize_hashmap_for_expression(&mut to);
            ArithmeticExpression::Linear { coefficients: to }
        };
        (substitution.from, right)
    }

    pub fn map_into_arith_expr(
        substitution: Substitution<C>,
        field: &BigInt,
    ) -> ArithmeticExpression<C> {
        let (left, right) = Substitution::decompose(substitution);
        let left = ArithmeticExpression::Signal { symbol: left };
        ArithmeticExpression::sub(&right, &left, field)
    }

    pub fn from(&self) -> &C {
        &self.from
    }

    pub fn to(&self) -> &HashMap<C, BigInt> {
        &self.to
    }

    pub fn take_cloned_signals(&self) -> HashSet<C> {
        let cq: C = ArithmeticExpression::constant_coefficient();
        let mut signals = HashSet::new();
        for s in self.to.keys() {
            if cq != *s {
                signals.insert(s.clone());
            }
        }
        signals
    }

    pub fn take_signals(&self) -> HashSet<&C> {
        let cq: C = ArithmeticExpression::constant_coefficient();
        let mut signals = HashSet::new();
        for s in self.to.keys() {
            if cq != *s {
                signals.insert(s);
            }
        }
        signals
    }

    pub fn rmv_zero_coefficients(substitution: &mut Substitution<C>) {
        substitution.to = remove_zero_value_coefficients(std::mem::take(&mut substitution.to))
    }

    pub fn is_valid_plonk_substitution(&self) -> bool{
        let cq: C = ArithmeticExpression::constant_coefficient();
        self.to.keys().len() < 2 || (self.to.keys().len() == 2 && self.to.contains_key(&cq))
    }

    pub fn print_pretty_substitution(&self){
        println!("Substitution: from {} to ", self.from);
            for (s, coef) in self.to(){
                println!("--- {} * {}", coef, s);
            }
    }
}

impl<C: Default + Clone + Display + Hash + Eq + std::cmp::Ord> Substitution<C> {
    pub fn take_cloned_signals_ordered(&self) -> BTreeSet<C> {
        let cq: C = ArithmeticExpression::constant_coefficient();
        let mut signals = BTreeSet::new();
        for s in self.to.keys() {
            if cq != *s {
                signals.insert(s.clone());
            }
        }
        signals
    }
}

impl Substitution<usize> {
    pub fn apply_offset(&self, offset: usize) -> Substitution<usize> {
        let constant: usize = Substitution::constant_coefficient();
        debug_assert_ne!(self.from, constant);
        let from = self.from + offset;
        let to = apply_raw_offset(&self.to, offset);
        Substitution { from, to }
    }
}

/*
    Represents a constraint of the form: A*B - C = 0
    where A,B and C are linear expression.
*/
#[derive(Clone, Debug)]
pub struct Constraint<C>
where
    C: Hash + Eq,
{
    pub(crate) a: HashMap<C, BigInt>,
    pub(crate) b: HashMap<C, BigInt>,
    pub(crate) c: HashMap<C, BigInt>,
}

impl<C: Default + Clone + Display + Hash + Eq> Constraint<C> {
    pub fn new(a: HashMap<C, BigInt>, b: HashMap<C, BigInt>, c: HashMap<C, BigInt>) -> Constraint<C> {
        Constraint { a, b, c }
    }

    pub fn empty() -> Constraint<C> {
        Constraint::new(
            HashMap::with_capacity(0),
            HashMap::with_capacity(0),
            HashMap::with_capacity(0),
        )
    }

    pub fn constant_coefficient() -> C {
        ArithmeticExpression::constant_coefficient()
    }
    pub fn apply_correspondence_and_drop<K>(
        constraint: Constraint<C>,
        symbol_correspondence: &HashMap<C, K>,
    ) -> Constraint<K>
    where
        K: Default + Clone + Display + Hash + Eq,
    {
        Constraint::apply_correspondence(&constraint, symbol_correspondence)
    }

    pub fn apply_correspondence<K>(
        constraint: &Constraint<C>,
        symbol_correspondence: &HashMap<C, K>,
    ) -> Constraint<K>
    where
        K: Default + Clone + Display + Hash + Eq,
    {
        let a = apply_raw_correspondence(&constraint.a, symbol_correspondence);
        let b = apply_raw_correspondence(&constraint.b, symbol_correspondence);
        let c = apply_raw_correspondence(&constraint.c, symbol_correspondence);
        Constraint::new(a, b, c)
    }

    // Constraint simplifications

    pub fn is_linear(constraint: &Constraint<C>) -> bool {
        constraint.a.is_empty() && constraint.b.is_empty()
    }

    pub fn clear_signal_from_linear(
        constraint: Constraint<C>,
        signal: &C,
        field: &BigInt,
    ) -> Substitution<C> {
        debug_assert!(Constraint::is_linear(&constraint));
        debug_assert!(constraint.c.contains_key(signal));
        let raw_expression = Constraint::clear_signal(constraint.c, &signal, field);
        Substitution { from: signal.clone(), to: raw_expression }
    }

    pub fn clear_signal_from_linear_not_normalized(
        constraint: Constraint<C>,
        signal: &C,
        field: &BigInt,
    ) -> (BigInt, Substitution<C>) {
        debug_assert!(Constraint::is_linear(&constraint));
        debug_assert!(constraint.c.contains_key(signal));
        let (coefficient, raw_expression) = Constraint::clear_signal_not_normalized(constraint.c, &signal, field);
        (coefficient, Substitution {from: signal.clone(), to: raw_expression})
    }

    pub fn take_cloned_signals(&self) -> HashSet<C> {
        let mut signals = HashSet::new();
        for signal in self.a().keys() {
            signals.insert(signal.clone());
        }
        for signal in self.b().keys() {
            signals.insert(signal.clone());
        }
        for signal in self.c().keys() {
            signals.insert(signal.clone());
        }
        signals.remove(&Constraint::constant_coefficient());
        signals
    }
    pub fn take_signals(&self) -> HashSet<&C> {
        let cc: C = Constraint::constant_coefficient();
        let mut signals = HashSet::new();
        for signal in self.a().keys() {
            signals.insert(signal);
        }
        for signal in self.b().keys() {
            signals.insert(signal);
        }
        for signal in self.c().keys() {
            signals.insert(signal);
        }
        HashSet::remove(&mut signals, &cc);
        signals
    }

    fn clear_signal(
        mut symbols: HashMap<C, BigInt>,
        key: &C,
        field: &BigInt,
    ) -> HashMap<C, BigInt> {
        let key_value = symbols.remove(&key).unwrap();
        assert!(!key_value.is_zero());
        let value_to_the_right = modular_arithmetic::mul(&key_value, &BigInt::from(-1), field);
        ArithmeticExpression::initialize_hashmap_for_expression(&mut symbols);
        let arithmetic_result = ArithmeticExpression::divide_coefficients_by_constant(
            &value_to_the_right,
            &mut symbols,
            field,
        );
        assert!(arithmetic_result.is_ok());
        remove_zero_value_coefficients(symbols)
    }

    fn clear_signal_not_normalized(
        mut symbols: HashMap<C, BigInt>,
        key: &C,
        field: &BigInt,
    ) -> (BigInt, HashMap<C, BigInt>) {
        let key_value = symbols.remove(&key).unwrap();
        assert!(!key_value.is_zero());
        let value_to_the_right = modular_arithmetic::mul(&key_value, &BigInt::from(-1), field);
        ArithmeticExpression::initialize_hashmap_for_expression(&mut symbols);
        (value_to_the_right, symbols)
    }

    pub fn apply_substitution(
        constraint: &mut Constraint<C>,
        substitution: &Substitution<C>,
        field: &BigInt,
    ) {
        raw_substitution(&mut constraint.a, substitution, field);
        raw_substitution(&mut constraint.b, substitution, field);
        raw_substitution(&mut constraint.c, substitution, field);
        //Constraint::fix_constraint(constraint, field);
    }

    pub fn remove_zero_value_coefficients(constraint: &mut Constraint<C>) {
        constraint.a = remove_zero_value_coefficients(std::mem::take(&mut constraint.a));
        constraint.b = remove_zero_value_coefficients(std::mem::take(&mut constraint.b));
        constraint.c = remove_zero_value_coefficients(std::mem::take(&mut constraint.c));
    }

    pub fn fix_constraint(constraint: &mut Constraint<C>, field: &BigInt) {
        fix_raw_constraint(&mut constraint.a, &mut constraint.b, &mut constraint.c, field);
    }

    pub fn is_empty(&self) -> bool {
        self.a.is_empty() && self.b.is_empty() && self.c.is_empty()
    }

    pub fn has_constant_coefficient(&self) -> bool {
        self.a.contains_key(&Constraint::constant_coefficient())
            || self.b.contains_key(&Constraint::constant_coefficient())
            || self.a.contains_key(&Constraint::constant_coefficient())
    }

    pub fn a(&self) -> &HashMap<C, BigInt> {
        &self.a
    }
    pub fn b(&self) -> &HashMap<C, BigInt> {
        &self.b
    }

    pub fn c(&self) -> &HashMap<C, BigInt> {
        &self.c
    }

    pub fn is_equality(&self, field: &BigInt) -> bool {
        signal_equals_signal(&self.a, &self.b, &self.c, field)
    }

    pub fn is_constant_equality(&self) -> bool {
        signal_equals_constant(&self.a, &self.b, &self.c)
    }

    pub fn into_arithmetic_expressions(self) -> (ArithmeticExpression<C>, ArithmeticExpression<C>, ArithmeticExpression<C>) {
        (
            ArithmeticExpression::Linear { coefficients: self.a },
            ArithmeticExpression::Linear { coefficients: self.b },
            ArithmeticExpression::Linear { coefficients: self.c }
        )
    }

}

impl<C: Default + Clone + Display + Hash + Eq + std::cmp::Ord> Constraint<C> {
    pub fn take_cloned_signals_ordered(&self) -> BTreeSet<C> {
        let mut signals = BTreeSet::new();
        for signal in self.a().keys() {
            signals.insert(signal.clone());
        }
        for signal in self.b().keys() {
            signals.insert(signal.clone());
        }
        for signal in self.c().keys() {
            signals.insert(signal.clone());
        }
        signals.remove(&Constraint::constant_coefficient());
        signals
    }

}

impl Constraint<usize> {
    pub fn apply_offset(&self, offset: usize) -> Constraint<usize> {
        let a = apply_raw_offset(&self.a, offset);
        let b = apply_raw_offset(&self.b, offset);
        let c = apply_raw_offset(&self.c, offset);
        Constraint::new(a, b, c)
    }
    pub fn apply_witness(&self, witness: &Vec<usize>) -> Constraint<usize> {
        let a = apply_vectored_correspondence(&self.a, witness);
        let b = apply_vectored_correspondence(&self.b, witness);
        let c = apply_vectored_correspondence(&self.c, witness);
        Constraint::new(a, b, c)
    }
}

// model utils
type RawExpr<C> = HashMap<C, BigInt>;

fn apply_vectored_correspondence(
    symbols: &HashMap<usize, BigInt>,
    map: &Vec<usize>,
) -> HashMap<usize, BigInt> {
    let mut mapped = HashMap::new();
    for (s, v) in symbols {
        mapped.insert(map[*s], v.clone());
    }
    mapped
}

fn apply_raw_correspondence<C, K>(
    symbols: &HashMap<C, BigInt>,
    map: &HashMap<C, K>,
) -> HashMap<K, BigInt>
where
    K: Default + Clone + Display + Hash + Eq,
    C: Default + Clone + Display + Hash + Eq,
{
    let constant_coefficient: C = ArithmeticExpression::constant_coefficient();
    let mut coefficients_as_correspondence = HashMap::new();
    for (key, value) in symbols {
        let id = if key.eq(&constant_coefficient) {
            ArithmeticExpression::constant_coefficient()
        } else {
            map.get(&key).expect(&format!("Unknown signal: {}", key)).clone()
        };
        coefficients_as_correspondence.insert(id, value.clone());
    }
    coefficients_as_correspondence
}

fn apply_raw_offset(h: &HashMap<usize, BigInt>, offset: usize) -> HashMap<usize, BigInt> {
    let mut new = HashMap::new();
    let constant: usize = Constraint::constant_coefficient();
    for (k, v) in h {
        if *k == constant {
            new.insert(*k, v.clone());
        } else {
            new.insert(*k + offset, v.clone());
        }
    }
    new
}

fn raw_substitution<C>(
    change: &mut HashMap<C, BigInt>,
    substitution: &Substitution<C>,
    field: &BigInt,
) where
    C: Default + Clone + Display + Hash + Eq,
{
    ArithmeticExpression::initialize_hashmap_for_expression(change);
    if let Option::Some(val) = change.remove(&substitution.from) {
        let mut coefficients = substitution.to.clone();
        ArithmeticExpression::initialize_hashmap_for_expression(&mut coefficients);
        ArithmeticExpression::multiply_coefficients_by_constant(&val, &mut coefficients, field);
        ArithmeticExpression::add_coefficients_to_coefficients(&coefficients, change, field);
    }
    //*change = remove_zero_value_coefficients(std::mem::take(change));
}

fn raw_substitution_muls<C>(
    change: &mut HashMap<(C, C), BigInt>,
    substitution: &Substitution<C>,
    field: &BigInt,
) where
    C: Default + Clone + Display + Hash + Eq + PartialOrd,
{
    use std::mem::replace;
    // First check the first signal, then second
    let old_change = replace(change, HashMap::new());

    for ((signal_a, signal_b), coef) in old_change{
        if signal_a == substitution.from{
            // Change signal_a by the linear combination
            for (new_signal, value) in &substitution.to{
                let ord_signals = (new_signal.clone(), signal_b.clone());
                if change.contains_key(&ord_signals){
                    let prev_value = change.get(&ord_signals).unwrap();
                    change.insert(ord_signals,  modular_arithmetic::add(prev_value, &modular_arithmetic::mul(&coef, value, field), field));
                } else{
                    change.insert(ord_signals, modular_arithmetic::mul(&coef, value, field));
                }
            }
        } else{
            let ord_signals = (signal_a.clone(), signal_b.clone());
            if change.contains_key(&ord_signals){
                let prev_value = change.get(&ord_signals).unwrap();
                change.insert(ord_signals,  modular_arithmetic::add(prev_value, &coef, field));
            } else{
                change.insert(ord_signals, coef.clone());
            }
        }
    }

    // do the same with the second signal
    let old_change = replace(change, HashMap::new());

    for ((signal_a, signal_b), coef) in old_change{
        if signal_b == substitution.from{
            // Change signal_a by the linear combination
            for (new_signal, value) in &substitution.to{
                let ord_signals = (signal_a.clone(), new_signal.clone());
                if change.contains_key(&ord_signals){
                    let prev_value = change.get(&ord_signals).unwrap();
                    change.insert(ord_signals,   modular_arithmetic::add(prev_value, &modular_arithmetic::mul(&coef, value, field), field));
                } else{
                    change.insert(ord_signals, modular_arithmetic::mul(&coef, value, field));
                }
            }
        } else{
            let ord_signals = (signal_a.clone(), signal_b.clone());
            if change.contains_key(&ord_signals){
                let prev_value = change.get(&ord_signals).unwrap();
                change.insert(ord_signals,  modular_arithmetic::add(prev_value, &coef, field));
            } else{
                change.insert(ord_signals, coef.clone());
            }
        }
    }
    //*change = remove_zero_value_coefficients(std::mem::take(change));
}

fn remove_zero_value_coefficients<C>(raw_expression: HashMap<C, BigInt>) -> HashMap<C, BigInt>
where
    C: Default + Clone + Display + Hash + Eq,
{
    let mut clean_raw = HashMap::new();
    for (key, val) in raw_expression {
        if !val.is_zero() {
            clean_raw.insert(key, val);
        }
    }
    clean_raw
}

fn remove_zero_value_coefficients_muls<C>(raw_expression: HashMap<(C, C), BigInt>) -> HashMap<(C, C), BigInt>
where
    C: Default + Clone + Display + Hash + Eq,
{
    let mut clean_raw = HashMap::new();
    for (key, val) in raw_expression {
        if !val.is_zero() {
            clean_raw.insert(key, val);
        }
    }
    clean_raw
}


fn fix_raw_constraint<C>(a: &mut RawExpr<C>, b: &mut RawExpr<C>, c: &mut RawExpr<C>, field: &BigInt)
where
    C: Default + Clone + Display + Hash + Eq,
{
    *a = remove_zero_value_coefficients(std::mem::take(a));
    *b = remove_zero_value_coefficients(std::mem::take(b));
    *c = remove_zero_value_coefficients(std::mem::take(c));
    if HashMap::is_empty(a) || HashMap::is_empty(b) {
        HashMap::clear(a);
        HashMap::clear(b);
    } else if is_constant_expression(a) {
        constant_linear_linear_reduction(a, b, c, field);
    } else if is_constant_expression(b) {
        constant_linear_linear_reduction(b, a, c, field);
    }
}

fn fix_raw_air_constraint<C>(linear: &mut RawExpr<C>, muls: &mut HashMap<(C,C), BigInt>, field: &BigInt)
where
    C: Default + Clone + Display + Hash + Eq + PartialOrd + Ord,
{
    reorder_signals_muls(muls, field);

    *linear = remove_zero_value_coefficients(std::mem::take(linear));
    *muls = remove_zero_value_coefficients_muls(std::mem::take(muls));

    constant_muls_reduction(linear, muls, field);
}

fn constant_linear_linear_reduction<C>(
    a: &mut RawExpr<C>,
    b: &mut RawExpr<C>,
    c: &mut RawExpr<C>,
    field: &BigInt,
) where
    C: Default + Clone + Display + Hash + Eq,
{
    let cq: C = ArithmeticExpression::constant_coefficient();
    ArithmeticExpression::initialize_hashmap_for_expression(c);
    ArithmeticExpression::initialize_hashmap_for_expression(b);
    let constant = HashMap::remove(a, &cq).unwrap();
    ArithmeticExpression::multiply_coefficients_by_constant(&constant, b, field);
    ArithmeticExpression::multiply_coefficients_by_constant(&BigInt::from(-1), b, field);
    ArithmeticExpression::add_coefficients_to_coefficients(b, c, field);
    *c = remove_zero_value_coefficients(std::mem::take(c));
    HashMap::clear(a);
    HashMap::clear(b);
}

fn reorder_signals_muls<C>(
    muls: &mut HashMap<(C, C), BigInt>,
    field: &BigInt
) where 
C: Default + Clone + Display + Hash + Eq + PartialOrd + Ord,
{
    use std::mem;
    let old_muls = mem::replace(muls, HashMap::new());
    for ((signal1, signal2), coeff) in old_muls{
        if signal1 <= signal2{
            if muls.contains_key(&(signal1.clone(), signal2.clone())){
                let old_value = muls.get(&(signal1.clone(), signal2.clone())).unwrap();
                muls.insert((signal1.clone(), signal2.clone()), modular_arithmetic::add(old_value, &coeff, field));
            } else{
                muls.insert((signal1.clone(), signal2.clone()), coeff);
            }
        } else{
            if muls.contains_key(&(signal2.clone(), signal1.clone())){
                let old_value = muls.get(&(signal2.clone(), signal1.clone())).unwrap();
                muls.insert((signal2.clone(), signal1.clone()), modular_arithmetic::add(old_value, &coeff, field));
            } else{
                muls.insert((signal2.clone(), signal1.clone()), coeff);
            }
        }
    }
}


fn constant_muls_reduction<C>(
    linear: &mut HashMap<C, BigInt>,
    muls: &mut HashMap<(C, C), BigInt>,
    field: &BigInt
) where 
C: Default + Clone + Display + Hash + Eq + PartialOrd + Ord,
{
    use std::mem;
    let cq: C = ArithmeticExpression::constant_coefficient();
    let old_muls = mem::replace(muls, HashMap::new());
    for ((signal1, signal2), coeff) in old_muls{
        if signal1 == cq{
            if linear.contains_key(&signal2){
                let old_value = linear.get(&signal2).unwrap();
                linear.insert(signal2, modular_arithmetic::add(old_value, &coeff, field));
            } else{
                linear.insert(signal2, coeff);

            }
        } else{
            muls.insert((signal1, signal2), coeff);
        }
    }
}


fn signal_equals_signal<C>(a: &RawExpr<C>, b: &RawExpr<C>, c: &RawExpr<C>, field: &BigInt) -> bool
where
    C: Default + Clone + Display + Hash + Eq,
{
    let cq: C = ArithmeticExpression::constant_coefficient();
    if a.is_empty() && b.is_empty() && !HashMap::contains_key(c, &cq) && c.len() == 2 {
        let signals: Vec<_> = c.keys().cloned().collect();
        let c0 = HashMap::get(c, &signals[0]).unwrap();
        let c1 = HashMap::get(c, &signals[1]).unwrap();
        let c1_p = modular_arithmetic::mul(&BigInt::from(-1), c1, field);
        c1_p == *c0
    } else {
        false
    }
}

fn signal_equals_constant<C>(a: &RawExpr<C>, b: &RawExpr<C>, c: &RawExpr<C>) -> bool
where
    C: Default + Clone + Display + Hash + Eq,
{
    let cq: C = ArithmeticExpression::constant_coefficient();
    HashMap::is_empty(a)
        && HashMap::is_empty(b)
        && 
        	((HashMap::contains_key(c, &cq) && HashMap::len(c) == 2) ||
        	(!HashMap::contains_key(c, &cq) && HashMap::len(c) == 1))
}

fn is_constant_expression<C>(expr: &RawExpr<C>) -> bool
where
    C: Default + Clone + Display + Hash + Eq,
{
    let cq: C = ArithmeticExpression::constant_coefficient();
    HashMap::contains_key(expr, &cq) && HashMap::len(expr) == 1
}

pub fn normalize(c: Constraint<usize>, _field: &BigInt) -> Constraint<usize> {
    use std::collections::LinkedList;
    let _a: LinkedList<_> = c.a.iter().clone().collect();
    let _b: LinkedList<_> = c.b.iter().clone().collect();
    let _c: LinkedList<_> = c.c.iter().clone().collect();
    todo!()
}


/*
    Represents a quadratic constraint of AIR form: coef* signal1*signal2 + ... + linear = 0
*/
#[derive(Clone, Debug)]
pub struct AIRConstraint<C>
where
    C: Hash + Eq + PartialOrd,
{
    pub(crate) muls: HashMap<(C, C), BigInt>, // always C1 < C2 when defining the hashmap
    pub(crate) linear: HashMap<C, BigInt>,
}

impl<C: Default + Clone + Display + Hash + Eq + PartialOrd + Ord> AIRConstraint<C> {
    pub fn new(muls: HashMap<(C, C), BigInt>, linear: HashMap<C, BigInt>) -> AIRConstraint<C> {
        AIRConstraint { muls, linear }
    }

    pub fn empty() -> AIRConstraint<C> {
        AIRConstraint::new(
            HashMap::with_capacity(0),
            HashMap::with_capacity(0),
        )
    }

    pub fn muls(&self) -> &HashMap<(C, C), BigInt> {
        &self.muls
    }
    pub fn linear(&self) -> &HashMap<C, BigInt> {
        &self.linear
    }


    pub fn is_empty(&self) -> bool {
        self.muls.is_empty() && self.linear.is_empty()
    }

    pub fn clear_signal_from_linear_not_normalized(
        constraint: AIRConstraint<C>,
        signal: &C,
        field: &BigInt,
    ) -> (BigInt, Substitution<C>) {
        debug_assert!(AIRConstraint::is_linear(&constraint));
        debug_assert!(constraint.linear.contains_key(signal));
        let (coefficient, raw_expression) = AIRConstraint::clear_signal_not_normalized(constraint.linear, &signal, field);
        (coefficient, Substitution {from: signal.clone(), to: raw_expression})
    }

    pub fn clear_signal_from_non_linear(
        constraint: AIRConstraint<C>,
        signal: &C,
        field: &BigInt,
    ) -> AIRSubstitution<C> {
        debug_assert!(constraint.linear.contains_key(signal));
        let (coefficient, raw_expression) = AIRConstraint::clear_signal_not_normalized(constraint.linear, &signal, field);
        let arith_sub = ArithmeticExpression::hashmap_into_arith(raw_expression);
        let div_linear_sub = match ArithmeticExpression::div(
            &arith_sub, 
            &ArithmeticExpression::Number {value : coefficient.clone()}, 
            field
        ){
            Ok(v) => v,
            _ => unreachable!()
        };
        

        let mut new_muls = HashMap::new();
        for ((s1, s2), coef) in constraint.muls{
            let div_coef = modular_arithmetic::div(&coef, &coefficient, field);
            let div_coef = match div_coef{
                Err(_) => unreachable!(),
                Ok(v) => v
            };
            new_muls.insert((s1, s2), div_coef);
        }
        
        AIRSubstitution::new(signal.clone(), div_linear_sub, new_muls).unwrap()
    }

    pub fn remove_zero_value_coefficients(constraint: &mut AIRConstraint<C>) {
        constraint.linear = remove_zero_value_coefficients(std::mem::take(&mut constraint.linear));
        constraint.muls = remove_zero_value_coefficients_muls(std::mem::take(&mut constraint.muls));
    }

    pub fn take_cloned_signals(&self) -> HashSet<C> {
        let mut signals = HashSet::new();
        for (signal_a, signal_b) in self.muls().keys() {
            signals.insert(signal_a.clone());
            signals.insert(signal_b.clone());
        }
        for signal in self.linear().keys() {
            signals.insert(signal.clone());
        }
        signals.remove(&AIRConstraint::constant_coefficient());
        signals
    }

    pub fn take_cloned_linear_signals(&self) -> HashSet<C> {
        let mut signals = HashSet::new();
        for signal in self.linear().keys() {
            signals.insert(signal.clone());
        }
        signals.remove(&AIRConstraint::constant_coefficient());
        signals
    }

    pub fn take_cloned_non_linear_signals(&self) -> HashSet<C> {
        let mut signals = HashSet::new();
        for (signal_a, signal_b) in self.muls().keys() {
            signals.insert(signal_a.clone());
            signals.insert(signal_b.clone());
        }
        signals.remove(&AIRConstraint::constant_coefficient());
        signals
    }

    pub fn take_cloned_signals_ordered(&self) -> BTreeSet<C> {
        let mut signals = BTreeSet::new();
        for signal in self.linear().keys() {
            signals.insert(signal.clone());
        }
        for (signal_a, signal_b) in self.muls().keys() {
            signals.insert(signal_a.clone());
            signals.insert(signal_b.clone());
        }

        signals.remove(&Constraint::constant_coefficient());
        signals
    }
    

    pub fn apply_substitution(
        constraint: &mut AIRConstraint<C>,
        substitution: &Substitution<C>,
        field: &BigInt,
    ) {
        raw_substitution_muls(&mut constraint.muls, substitution, field);
        raw_substitution(&mut constraint.linear, substitution, field);
        //Constraint::fix_constraint(constraint, field);
    }

    pub fn apply_air_substitution(
        constraint: &mut AIRConstraint<C>,
        substitution: &AIRSubstitution<C>,
        field: &BigInt,
    ){

        // To ensure that the signal is not in the non linear part
        for (s1, s2) in constraint.muls().keys(){
            assert!(s1 != substitution.from());
            assert!(s2 != substitution.from());
        }


        let coefficient = if constraint.linear.contains_key(substitution.from()){
            constraint.linear.get(substitution.from()).unwrap().clone()
        } else{
            BigInt::from(0)
        };

        // We remove the eliminated value
        constraint.linear.remove(substitution.from());

        if coefficient != BigInt::from(0){
            
            // update the linear part
            for (s, value) in substitution.to_linear(){
                let coef = modular_arithmetic::mul(&coefficient, value, field);
                if constraint.linear.contains_key(s){
                    let prev_coef = constraint.linear.get_mut(s).unwrap();
                    *prev_coef = modular_arithmetic::add(&coef, prev_coef, field);
                } else{
                    constraint.linear.insert(s.clone(), coef);
                }
            }

            // update the non linear part
            for ((s1, s2), value) in substitution.to_muls(){
                let coef = modular_arithmetic::mul(&coefficient, value, field);
                let sigs = (s1.clone(), s2.clone());
                if constraint.muls.contains_key(&sigs){
                    let prev_coef = constraint.muls.get_mut(&sigs).unwrap();
                    *prev_coef = modular_arithmetic::add(&coef, prev_coef, field);
                } else{
                    constraint.muls.insert(sigs, coef);
                }
            }

        }
        
    }

    pub fn fix_constraint(constraint: &mut AIRConstraint<C>, field: &BigInt) {
        fix_raw_air_constraint(&mut constraint.linear, &mut constraint.muls, field);
    }
    

    // !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    // All the operations must ensure that the Hashmaps used
    // to construct Expressions contain the empty string
    // as key.
    // Therefore the function 'initialize_hashmap_for_expression'
    // is meant to be call each time a hashmap is going to be
    // part of a Expression
    // !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    pub fn constant_coefficient() -> C {
        C::default()
    }

    // Constraint simplifications

    pub fn is_linear(constraint: &AIRConstraint<C>) -> bool {
        constraint.muls.is_empty() 
    }

    pub fn clear_signal_from_linear(
        constraint: AIRConstraint<C>,
        signal: &C,
        field: &BigInt,
    ) -> Substitution<C> {
        debug_assert!(AIRConstraint::is_linear(&constraint));
        debug_assert!(constraint.linear.contains_key(signal));
        let raw_expression = AIRConstraint::clear_signal(constraint.linear, &signal, field);
        Substitution { from: signal.clone(), to: raw_expression }
    }

    fn clear_signal(
        mut symbols: HashMap<C, BigInt>,
        key: &C,
        field: &BigInt,
    ) -> HashMap<C, BigInt> {
        let key_value = symbols.remove(&key).unwrap();
        assert!(!key_value.is_zero());
        let value_to_the_right = modular_arithmetic::mul(&key_value, &BigInt::from(-1), field);
        ArithmeticExpression::initialize_hashmap_for_expression(&mut symbols);
        let arithmetic_result = ArithmeticExpression::divide_coefficients_by_constant(
            &value_to_the_right,
            &mut symbols,
            field,
        );
        assert!(arithmetic_result.is_ok());
        remove_zero_value_coefficients(symbols)
    }

    fn clear_signal_not_normalized(
        mut symbols: HashMap<C, BigInt>,
        key: &C,
        field: &BigInt,
    ) -> (BigInt, HashMap<C, BigInt>) {
        let key_value = symbols.remove(&key).unwrap();
        assert!(!key_value.is_zero());
        let value_to_the_right = modular_arithmetic::mul(&key_value, &BigInt::from(-1), field);
        ArithmeticExpression::initialize_hashmap_for_expression(&mut symbols);
        (value_to_the_right, symbols)
    }

    pub fn print_pretty_constraint(&self){
        println!("AIR Constraint: ");
        for (s, coef) in self.linear(){
            println!("--- {} * {}", coef, s);
        }
        for ((s1,s2), coef) in self.muls(){
            println!("--- {} * {} {}", coef, s1, s2);
        }
    }

    pub fn can_take_plonk_signal(&self) -> bool{
        let keys = self.linear().keys();
        let cq = ArithmeticExpression::constant_coefficient();
        keys.len() <= 2 || (keys.len() == 3 && self.linear().contains_key(&cq))
    }


}


#[derive(Clone)]
pub struct AIRSubstitution<C>
where
    C: Hash + Eq,
{
    pub(crate) from: C,
    pub(crate) to_linear: HashMap<C, BigInt>,
    pub(crate) to_muls: HashMap<(C, C), BigInt>
}
impl<C: Default + Clone + Display + Hash + Eq> AIRSubstitution<C> {
    // Substitution public utils
    pub fn new(from: C, to_linear: ArithmeticExpression<C>, to_muls: HashMap<(C, C), BigInt>) -> Option<AIRSubstitution<C>> {
        use ArithmeticExpression::*;
        
        // CHECK THAT MULS DOES NOT CONTAIN FROM
        for (m1, m2) in to_muls.keys(){
            if *m1 == from || *m2 == from{
                return None
            }
        }
        

        match to_linear {
            Number { value } => {
                let mut to_linear = HashMap::new();
                to_linear.insert(ArithmeticExpression::constant_coefficient(), value);
                Option::Some(AIRSubstitution { from, to_linear, to_muls })
            }
            Signal { symbol } => {
                let mut to_linear = HashMap::new();
                to_linear.insert(symbol, BigInt::from(1));
                Option::Some(AIRSubstitution { from, to_linear, to_muls })
            }
            Linear { coefficients: to_linear } if !to_linear.contains_key(&from) => {
                Option::Some(AIRSubstitution { from, to_linear, to_muls })
            }
            _ => Option::None,
        }
    }

    pub fn from(&self) -> &C {
        &self.from
    }

    pub fn to_linear(&self) -> &HashMap<C, BigInt> {
        &self.to_linear
    }

    pub fn to_muls(&self) -> &HashMap<(C, C), BigInt> {
        &self.to_muls
    }

    pub fn print_pretty_substitution(&self){
        println!("Substitution: from {} to ", self.from);
            for (s, coef) in self.to_linear(){
                println!("--- {} * {}", coef, s);
            }
            for ((s1,s2), coef) in self.to_muls(){
                println!("--- {} * {} {}", coef, s1, s2);
            }
    }
}
