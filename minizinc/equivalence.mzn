include "all_different.mzn";

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% CONSTS %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

int: nSignals;
int: nConstraints;

set of int: SIGNALS = 1..nSignals-1;
set of int: CONSTRAINTS = 1..nConstraints;

int: maxvars;

%% Assuming some preprocessing to handle easy cases, hard case requires equivalence between two constraints
%%   to save space, we build a 2d array of tuples where the second dimension is the sigs in a constraint
%%   this is typically far lower than total number of constraints (2d array not set for iterable)
%%   tuple is (sig, coef in A, coef in B, coef in C)
%   If larger examples prove to have limited high maxvars maybe split these ?
set of int: VARSET = 1..maxvars;

array[CONSTRAINTS, VARSET] of tuple(0..nSignals, int, int, int): circuit1;
array[CONSTRAINTS, VARSET] of tuple(0..nSignals, int, int, int): circuit2;

%% Two constraints rely on preprocessed information
%% these drastically reduce the domain of the signal and constraint bijections

array[SIGNALS] of set of SIGNALS: signal_restrictions;
array [_] of 1..nConstraints+1: classes;

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% VARS %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

array [SIGNALS] of var SIGNALS: signal_bijection;
array [CONSTRAINTS] of var CONSTRAINTS: constraint_bijection;

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% CONSTRAINTS %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% Handle bijection for signal/constraints
constraint alldifferent(signal_bijection);
constraint alldifferent(constraint_bijection);

% Handle domain restrictions for bijections
constraint forall( i in SIGNALS ) (signal_bijection[i] in signal_restrictions[i]);

constraint forall( i in index_set(classes) where has_index(i+1, classes) ) (
  forall(cons in classes[i]..classes[i+1]-1)(classes[i] <= constraint_bijection[cons] /\ constraint_bijection[cons] <= classes[i+1]-1)
);

% checks that bijection is correct (i.e. if the coefs agree)
constraint forall (i in CONSTRAINTS, X in circuit1[i, ..] where X.1 != 0) (
  let { var VARSET : j } in ( %% exists typically low domain size -- check with larger examples
    signal_bijection[X.1] == circuit2[constraint_bijection[i], j].1 /\ 
    X.2 == circuit2[constraint_bijection[i], j].2 /\ 
    X.3 == circuit2[constraint_bijection[i], j].3 /\ 
    X.4 == circuit2[constraint_bijection[i], j].4 )
);

solve satisfy;