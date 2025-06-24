import itertools
from typing import Set, List, Tuple, Hashable
from circuits_and_constraints.abstract_constraint import Constraint

from normalisation import divisionNorm
from r1cs_scripts.modular_operations import multiplyP, divideP

class R1CSConstraint(Constraint):
    def __init__(self, A, B, C, p):
        self.A = A,
        self.B = B,
        self.C = C,
        self.p = p
    
    def is_nonlinear(self) -> bool:
        return len(self.A) * len(self.B) > 0

    def signals(self) -> Set[int]:
        return set(filter(lambda k : k != 0, itertools.chain.from_iterable(map(lambda dict_ : dict_.keys(), [self.A, self.B, self.C]))))
    
    def normalisation_choices(self) -> List[Tuple[Tuple[int, int], int]]:
        choices_AB = []
        # first normalise the quadratic term if there is one

        if self.is_nonlinear():
            if 0 in self.A.keys():
                choices_A = [self.A[0]]
            else:
                choices_A = divisionNorm(list(self.A.values()), self.p, early_exit=True, select=True)

            if 0 in self.B.keys():
                choices_B = [self.B[0]]
            else:
                choices_B = divisionNorm(list(self.B.values()), self.p, early_exit=True, select=True)

            choices_AB = list(itertools.product(choices_A, choices_B))

        ## What to do now if len( choices_AB ) > 1 ?

        # current idea, do norm for each?
        if 0 in self.C.keys():
            choices_C = [self.C[0]]
            choices = list(itertools.product(choices_AB if choices_AB != [] else [(0, 0)], choices_C))
        else:
            choices = []

            if choices_AB == []:
                choices += list(itertools.product([(0, 0)], divisionNorm(list(self.C.values()), self.p, early_exit = True, select = True)))
            else:
                # normalise by quadratic term if no constant factor
                choices += list(zip(choices_AB, [itertools.multiplyP(a, b, self.p) for a, b in choices_AB]))
        
        return choices
    
    def normalise(self):
        choices = self.normalisation_choices()

        def normalise_with_choices(a, b, c) -> Constraint:
            res = R1CSConstraint(
                *sorted([{key: divideP(val, norm, self.p) for key, val in part.items()} for part, norm in zip( [self.A, self.B], [a,b])],
                        key = lambda part: sorted(part.values())),
                C = {key: divideP(self.C[key], c, self.p) for key in self.C.keys()},
                p = self.p
            )
            ## sorting
            res.A = {key: res.A[key] for key in sorted(res.A.keys(), key = lambda x : res.A[x])}
            res.B = {key: res.B[key] for key in sorted(res.B.keys(), key = lambda x : res.B[x])}
            res.C = {key: res.C[key] for key in sorted(res.C.keys(), key = lambda x : res.C[x])}
            
            return res

        return [
            normalise_with_choices(a, b, c) for (a, b), c in choices
        ]
    
    def fingerprint(self, signal_to_fingerprint: List[int]) -> Hashable:
        """
        Generates a fingerprint for a normalized constraint.

        Fingerprint norm is based on latest fingerprints of signals in norm sorted by characteristic of signal in self.

        Parameters
        ----------
        self : R1CSConstraint
            The constraint to fingerprint.
        signal_fingerprints : List[int]
            Fingerprint values of signals involved in the constraint.

        Returns
        -------
        Tuple
            Hashable fingerprint representation of the constraint.
        """
        is_ordered = not ( len(self.A) > 0 and len(self.B) > 0 and sorted(self.A.values()) == sorted(self.B.values()) )

        if is_ordered:
            fingerprint = tuple(map(lambda part : tuple(sorted(map(lambda sig : (signal_to_fingerprint[sig], part[sig]), part.keys()))), [self.A, self.B, self.C]))
        else:
            # set operations pretty slow ... better way of doing this? -- faster just to check each?
            lsignals, rsignals = self.A.keys(), self.B.keys()

            in_both = set(lsignals).intersection(rsignals)
            only_left, only_right = set(lsignals).difference(in_both), set(rsignals).difference(in_both)    

            fingerprint = (tuple(sorted(map(lambda sig : (signal_to_fingerprint[sig], tuple(sorted(map(lambda part : part[sig], [self.A, self.B])))), in_both))), # both parts
                        tuple(sorted(itertools.chain(*itertools.starmap(lambda part, signals : map(lambda sig : (signal_to_fingerprint[sig], part[sig]), signals) , [(self.A, only_left), (self.B, only_right)])))), 
                        tuple(sorted(map(lambda sig : (signal_to_fingerprint[sig], self.C[sig]), self.C.keys()))))

        return fingerprint
