import itertools
import warnings
from functools import reduce
from typing import Iterable, List, Dict, Tuple, Hashable

from circuits_and_constraints.abstract_circuit import Circuit
from circuits_and_constraints.r1cs.r1cs_constraint import R1CSConstraint
from circuits_and_constraints.r1cs.parse_r1cs import parse_r1cs
from circuits_and_constraints.r1cs.write_r1cs import write_r1cs

from utilities.assignment import Assignment
from utilities.single_cons_options import _compare_norms_with_ordered_parts, _compare_norms_with_unordered_parts

class R1CSCircuit(Circuit):

    def __init__(self):
        self._constraints = []
        self._normalised_constraints = []
        self._normi_to_coni = []

        self.field_size = None
        self._prime_number = None
        self._nWires = None
        self.nPubOut = None
        self.nPubIn = None
        self.nPrvIn = None
        self.nLabels = None
        self._nConstraints = None
    
    def update_header(self, field_size, prime_number, nWires, nPubOut, nPubIn, nPrvIn, nLabels, nConstraints):
        self.field_size = field_size
        self.prime_number = prime_number
        self._nWires = nWires
        self.nPubOut = nPubOut
        self.nPubIn = nPubIn
        self.nPrvIn = nPrvIn
        self.nLabels = nLabels
        self._nConstraints = nConstraints

    def add_constraint(self, con: R1CSConstraint) -> None:
        self.constraints.append(con)
    
    def signal_is_input(self, signal: int) -> bool:
        return self.nPubOut < signal <= self.nPrvIn + self.nPubIn + self.nPubOut
    
    def signal_is_output(self, signal: int) -> bool:
        return 0 < signal <= self.nPubOut
    
    def get_signals(self) -> Iterable[int]:
        return range(1, self.nWires)

    def get_input_signals(self) -> Iterable[int]: 
        return range(self.nPubOut+1, self.nPrvIn + self.nPubIn+self.nPubOut+1)

    def get_output_signals(self) -> Iterable[int]:
        return range(1, self.nPubOut+1)
    
    def parse_file(self, file: str) -> None:
        parse_r1cs(file, self)

    def write_file(self, file: str) -> None:
        write_r1cs(self, file, sym=False)

    def take_subcircuit(self, constraint_subset: List[int], input_signals: List[int] | None = None, output_signals: List[int] | None = None, signal_map: Dict[int, int] | None = None, return_signal_mapping: bool = False):

        if (input_signals is None and output_signals is not None) or (input_signals is not None and output_signals is None):
            raise AssertionError("Gave only 1 of input and output signals to take_subcircuit")

        subcircuit = R1CSCircuit()

        if signal_map is None:
            
            if len(set(output_signals).intersection(input_signals)) > 0:
                warnings.warn(f"Input and outputs of proposed subcircuit overlap: {input_signals}, {output_signals}")

            output_signals = set(output_signals).difference(input_signals) # Assumed that inputs/outputs do not crossover, but doing this

            # not correct for R1CS but maintains consistency with how signal_map works
            ordered_signals = list(itertools.chain(
                output_signals, 
                input_signals,
                set(itertools.chain.from_iterable(map(lambda con : con.signals(), map(self.constraints.__getitem__, constraint_subset)))).difference(itertools.chain(output_signals, input_signals))
            ))

            signal_map = dict(zip(
                ordered_signals,
                range(len(ordered_signals))
            ))

            nInputs = len(input_signals)
            nOutputs = len(output_signals)
        
        else: # Can turn off error checking if causing performance problems
            if signal_map.get(0, None) is not None: raise AssertionError(f"Mapping given to R1CS take_circuit maps constant signal 0. This is handled within the function so simply pass a valid (0,nWires-1) mapping to this method")
            if input_signals is not None:
                if any(sig not in signal_map.keys() for sig in itertools.chain(input_signals, output_signals)):
                    raise AssertionError(f"Proposed inputs/outputs not in given signal_map")
                elif sorted(map(signal_map.__getitem__, output_signals)) != list(range(0,len(output_signals))):
                    raise AssertionError(f"Proposed signal mapping does match R1CS values given proposed output signals")
                elif sorted(map(signal_map.__getitem__, input_signals)) != list(range(len(output_signals),len(output_signals)+len(input_signals))):
                    raise AssertionError(f"Proposed signal mapping does match R1CS values given proposed output and input signals")
            else:
                nInputs = sum(1 for _ in filter(lambda sig : signal_map.get(sig, None) is not None, self.get_input_signals()))
                nOutputs = sum(1 for _ in filter(lambda sig : signal_map.get(sig, None) is not None, self.get_output_signals()))

        subcircuit._constraints = list(map(lambda con : 
            R1CSConstraint(
                *[{0 if sig == 0 else signal_map[sig]+1:val for sig, val in dict_.items()} for dict_ in [con.A, con.B, con.C]],
                con.p
            ),
            map(self.constraints.__getitem__, constraint_subset)))
        
        subcircuit.update_header(
            self.field_size,
            self.prime_number,
            len(signal_map)+1,
            nOutputs,
            nInputs,
            0, # prv in doesn't matter
            None,
            len(constraint_subset)
        )

        return ( subcircuit, {sig: 0 if sig == 0 else signal_map[sig]+1 for sig in itertools.chain([0], signal_map.keys())} ) if return_signal_mapping else subcircuit

    def fingerprint_signal(self, signal: int, constraints_to_fingerprint: List[R1CSConstraint], normalised_constraint_fingerprints: List[int], prev_signal_to_fingerprint: Dict[int, Hashable], signal_to_normi: List[List[int]]) -> Hashable:
        """
        Computes a fingerprint for a signal based on associated constraints and their fingerprints.

        Signal hashable is list of fingerprints of constraint norms that signal is in sorted by its characterstic in that norm.

        Parameters
        ----------
        signal : int
            Signal identifier.
        constraint_fingerprints : List[int]
            List of fingerprints for constraints.
        signal_to_normi : List[List[int]]
            Mapping from signals to constraints they appear in.
        norms : List[Constraint]
            List of all normalized constraints.

        Returns
        -------
        Tuple
            Hashable fingerprint for the signal.
        """
    
        fingerprint = []

        for normi in signal_to_normi[signal]:

            norm = constraints_to_fingerprint[normi]
            is_ordered = sorted(norm.A.values()) != sorted(norm.B.values()) ## mayne have ordered lookup (more memory usage ...)

            if is_ordered:       
                Aval, Bval, Cval = [0 if signal not in part.keys() else part[signal] for part in [norm.A, norm.B, norm.C]]
                                                # weird structure here so comparable to unordered
                fingerprint.append((normalised_constraint_fingerprints[normi], ((Aval, 0), Bval, Cval)))
            else:
                inA, inB, inC = tuple(map(lambda part : signal in part.keys(), [norm.A, norm.B, norm.C]))
                cVal = 0 if not inC else norm.C[signal]

                if inA and inB:
                    fingerprint.append((normalised_constraint_fingerprints[normi], (tuple(sorted([norm.A[signal], norm.B[signal]])), 0, cVal)))
                else:
                    fingerprint.append((normalised_constraint_fingerprints[normi], ((0, 0), norm.A[signal] if inA else (norm.B[signal] if inB else 0), cVal)))

        return tuple(sorted(fingerprint))
    
    @staticmethod
    def encode_single_norm_pair(
        names: List[str],
        norms: List[R1CSConstraint],
        is_ordered: bool,
        signal_pair_encoder: Assignment,
        signal_to_fingerprint: Dict[str, List[int]],
        fingerprint_to_signals: Dict[str, Dict[int, List[int]]],
        is_singular_class: bool = False
    ):
        """
        SAT encoder for a single norm pair

        Determines for a single norm pair the 'viable' signal pairs and builds a structure into the format for pysat. Signals
        are considered to be viable pairs if they have the same coefficient in every ordered part, or if the same linear coefficient
        and the same multiset of nonlinear coefficients if parts are unordered.

        If pair is nonviable due to at least one signal having no viable signal pairs then empty clauses are returned.

        Parameters
        -----------
            names: List[str]
                Top-level index set for following dicts.
            norms: List[Constraint]
                The pair of constraints.
            is_ordered: bool
                Flag indicating that the norms have ordered linear parts.
            signal_pair_encoder: Assignment
                Assigment dict wrapper for signal_pairs
            signal_to_fingerprint: Dict[str, List[int]]
                For each circuit, signal to signal figerprint mapping. Assumed to be consistent with fingerprint_to_signals
            fingerprint_to_signals: Dict[str, Dict[int, List[int]]]
                For each circuit, the partition of signals into classes, indexed by the encoded fingerprint label. Assumed to be consistent with fingerprint_to_signals.
        
        Return
        ---------
        List[List[int]]
            CNF formula where each clause is an at-least-one cardinality constraint for a mappings from each signal in each constraints to the viable signals in other constraint.
        """

        ## version from single_cons_options adapted to new signal fingerprints

        ## this restriction is necessary:
        #       e.g. two signals are in 'class' 3 that gives characteristics (6,4,0) and (2,4,6) for norms with class 5
        #              when encoding class 5 we need to restrict choices for (6,4,0) <-> (6,4,0) and (6,4,0) <-> (2,4,6)

        dicts = list(map(lambda norm : [norm.A, norm.B, norm.C], norms))
        allkeys = [norm.signals() for norm in norms]
        
        app, inv = (_compare_norms_with_ordered_parts if is_ordered else _compare_norms_with_unordered_parts)(dicts, allkeys)

        for j in range(3):
            if len( set(inv[0][j].keys()).symmetric_difference(inv[1][j].keys()) ) != 0:
                # These are not equivalent constraints, hence the option is inviable

                return []

        clauses = []

        def _get_values_for_key(i, j, key) -> int | Tuple[int, int]:
            if is_ordered or j == 2: return dicts[i][j][key]
            if j == 0: return tuple(sorted(map(lambda j : dicts[i][j][key], range(2))))
            return next(iter([dicts[i][j][key] for j in range(2) if key in dicts[i][j].keys()]))
        
        for i, name in enumerate(names):
            for key in allkeys[i]:

                # ensures consistency amongst potential pairs
                oset = reduce(
                    lambda x, y : x.intersection(y),
                    [ inv[1-i][j][_get_values_for_key(i, j, key)] for j in app[i][key] ], 
                    allkeys[1-i]
                )

                oset.intersection_update(fingerprint_to_signals[names[1-i]].setdefault(signal_to_fingerprint[names[i]][key], []))

                if len(oset) == 0: return []

                clauses.append(list(map(
                    lambda pair : signal_pair_encoder.get_assignment(*((key, pair) if i == 0 else (pair, key))),
                    oset
                )))
        
        return clauses
    
    @staticmethod
    def singular_class_requires_additional_constraints(): return False

    @property
    def prime(self) -> int:
        return self._prime_number

    @property
    def nConstraints(self) -> int:
        return self._nConstraints

    @property
    def nWires(self) -> int:
        return self._nWires

    @property
    def constraints(self) -> List[R1CSConstraint]:
        return self._constraints
    
    @property
    def normalised_constraints(self) -> List[R1CSConstraint]:
        return self._normalised_constraints
    
    @property
    def normi_to_coni(self) -> List[int]:
        return self._normi_to_coni

    @property
    def nInputs(self) -> int:
        return self.nPrvIn + self.nPubIn

    @property
    def nOutputs(self) -> int:
        return self.nPubOut

    
    