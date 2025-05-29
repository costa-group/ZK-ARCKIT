from typing import List, Tuple, Dict
from itertools import product, chain
from functools import reduce
from collections import defaultdict

from utilities.assignment import Assignment
from r1cs_scripts.circuit_representation import Circuit


class ConsBijConstraint():
    """
        This represents the signal clauses for a bijection between some constraints i, j.
        i.e. for every norm in i, j.

        Since all the at most 1 logic is handled in the encoding itself all we care is the at least 1 logic,
            for i, j at least 1 of the k norm forms must be happy with the given encoding.

        The programming logic behind the propagator is relatively straight forward but what clause do we return to justify it,


    """

    def __init__(self, Options: List[dict], mapp: Assignment, in_pair: List[Tuple[str, Circuit]]) -> None:

        self.K = range(len(Options))

        self.in_pair = in_pair

        self.norm_options = Options

        self.mapp = mapp

        self.vset = reduce(
            lambda acc, x : acc.union(x),
            chain( *[self.norm_options[k][name].values() for name, _ in self.in_pair for k in self.K] ),
            set([])
        )

        self.expl = {
            v: None
            for v in self.vset
        }

        self.assignment = None # will copy the assignment of the Engine
        self.fmod = None # will store falsified model for when falsified

    def attach_values(self, values) -> None:
        self.assignment = values

    def register_watched(self, to_watch) -> None:
        for var in self.vset:
            to_watch[-var].append(self)
        
    def _is_norm_valid(self, k) -> bool:

        return all([ 
            map(
                lambda signal : len(self._get_signal_options(k, name, signal)) > 0,
                self.norm_options[k][name].keys()
            ) for name, _ in self.in_pair
        ])

    def _get_signal_options(self, k, name, signal):
        return [v for v in self.norm_options[k][name][signal] if self.assignment[v] != -v]

    def propagate(self, lit: int = None) -> List[int]:
        propagated = []
        expl = [v for v in self.vset if self.assignment[v] == -v]
        name = self.in_pair[0][0]

        if lit == None:
            
            # check each signal (on left) to see if it has only 1 option left
            curr_options = defaultdict(lambda : set([]))

            for k in [k for k in self.K if self._is_norm_valid(k)]:

                for signal in self.norm_options[k][name].keys():

                    curr_options[name][signal].update(self._get_signal_options(k, name, signal))

            for name, _ in self.in_pair:
                for signal in curr_options[name].keys():

                    if len(curr_options[name][signal]) == 1:
                        p = next(iter(curr_options[name][signal]))

                        propagated.append( p )

                        # Builds LHS of implication about if (curr relevant assignment) -> p
                            #   TODO: think to improve by choosing smaller set
                        self.expl[p] = expl

        elif lit < 0:
            var = abs(lit)
            signal, _ = self.mapp.get_inv_assignment(var)

            opts = set([])

            for k in self.K:
                if var not in self.norm_options[k][name][signal]:
                    continue

                current_options = self._get_signal_options(k, name, signal)
                if self._is_norm_valid(k): opts.update(current_options)
        
            if len(opts) == 1:
                
                p = next(iter(opts))
                propagated.append( p )

                # Builds LHS of implication about if (curr relevant assignment) -> p
                #   TODO: think to improve by choosing smaller set
                self.expl[p] = expl

        return propagated        

    def justify(self, lit) -> List[int]:
        return self.expl[abs(lit)] # propagator will never negate a variable but just in case take abs

    def abandon(self, lit) -> List[int]:
        self.expl[abs(lit)].clear() # propagator will never negate a variable but just in case take abs
    
    def falsified_by(self, model: Dict[int, int]):
        """
        Logic for:
            At least 1 norm is true.
        """
        st = any(map(
            lambda k : all([
                any( map(lambda var : model[var] is not None and model[var] > 0, self.norm_options[k][name][signal] ) )
                for name, _ in self.in_pair for signal in self.norm_options[k][name].keys()
            ]),
            self.K
        ))

        if not st:
            self.fmod = [-lit for lit in model if abs(lit) in self.vset] 
        
        return st

    def explain_failure(self):
        return self.fmod