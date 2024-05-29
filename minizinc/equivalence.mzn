include "all_different.mzn";

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% CONSTS %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

int: nSignals;
int: nConstraints;

set of int: SIGNALS = 1..nSignals-1;
set of int: CONSTRAINTS = 1..nConstraints;

% NOTE: simple but not very scalable, improve this.
% TODO: able to handle multiple norms
% TODO: classes
int: maxvars;

array[SIGNALS] of set of SIGNALS: signal_restrictions;

set of int: VARSET = 1..maxvars;

array[CONSTRAINTS, VARSET] of tuple(0..nSignals, int, int, int): circuit1;
array[CONSTRAINTS, VARSET] of tuple(0..nSignals, int, int, int): circuit2;

% constraints are preprocessed to be sorted by class
array [_] of 1..nConstraints+1: classes;

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% VARS %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

array [SIGNALS] of var SIGNALS: signal_bijection;
array [CONSTRAINTS] of var CONSTRAINTS: constraint_bijection;

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% CONSTRAINTS %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

constraint alldifferent(signal_bijection);
constraint alldifferent(constraint_bijection);

constraint forall( i in SIGNALS ) (signal_bijection[i] in signal_restrictions[i]);

constraint forall( i in index_set(classes) where has_index(i+1, classes) ) (
  forall(cons in classes[i]..classes[i+1]-1)(classes[i] <= constraint_bijection[cons] /\ constraint_bijection[cons] <= classes[i+1]-1)
);

constraint forall (i in CONSTRAINTS, X in circuit1[i, ..] where X.1 != 0) (
  exists ( j in VARSET ) ( 
    signal_bijection[X.1] == circuit2[constraint_bijection[i], j].1 /\ 
    X.2 == circuit2[constraint_bijection[i], j].2 /\ 
    X.3 == circuit2[constraint_bijection[i], j].3 /\ 
    X.4 == circuit2[constraint_bijection[i], j].4 )
);

solve satisfy;