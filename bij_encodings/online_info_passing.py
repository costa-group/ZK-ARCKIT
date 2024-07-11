from typing import Dict, List, Tuple, Callable, Set, Iterable
from pysat.formula import CNF
import heapq as hp
from functools import reduce

from r1cs_scripts.circuit_representation import Circuit
from comparison.constraint_preprocessing import known_split
from bij_encodings.assignment import Assignment
from bij_encodings.encoder import Encoder
from normalisation import r1cs_norm

def count_ints(lints : Iterable[int]) -> Dict[int, int]:
    res = {}
    for i in lints:
        res[i] = res.setdefault(i, 0) + 1
    return sorted(res.items())

class OnlineInfoPassEncoder(Encoder):

    def encode(
            self,
            classes: Dict[str, Dict[str, List[int]]],
            in_pair: List[Tuple[str, Circuit]],
            class_encoding: Callable,
            signal_encoding: Callable,
            return_signal_mapping: bool = False,
            return_constraint_mapping = False, 
            debug: bool = False,
            formula: CNF = CNF(),
            mapp: Assignment = Assignment(),
            ckmapp: Assignment = None,
            assumptions: Set[int] = set([]),
            signal_info: Dict[str, Dict[int, int]] = None
        ) -> CNF:

        """
        destroys the classes dict (for memory)
        """

        if ckmapp is None: ckmapp =  Assignment(assignees=3, link=mapp)
        if signal_info is None: signal_info = {
            name: {}
            for name, _ in in_pair
        }
            
        if debug: classes_encoded = []
            
        priorityq = [
            (len(classes[in_pair[0][0]][key]), i, {name: classes[name][key] for name, _ in in_pair})
            for i, key in enumerate(classes[in_pair[0][0]].keys())
        ]
        next_class = len(priorityq)

        hp.heapify(priorityq)

        # TODO: test memory saving
        del classes[in_pair[0][0]]
        del classes[in_pair[1][0]]

        while len(priorityq) > 0:
            length, class_ind, class_ = hp.heappop(priorityq)

            if length > 1:
                new_classes = {}

                for name, circ in in_pair:
                    for coni in class_[name]:
                        hash_ = known_split(r1cs_norm(circ.constraints[coni]), name, mapp, signal_info)
                        new_classes.setdefault(hash_, {name_: [] for name_, _ in in_pair})[name].append(coni)

                if len(new_classes) > 1:
                    if debug: print(f"Broken down class {class_ind} of size {length} into classes: {count_ints(map(lambda class_ : len(class_[in_pair[0][0]]), new_classes.values()))}", end="\r")

                    for new_class in new_classes.values():

                        assert all([name in new_class.keys() for name, _ in in_pair]) 
                        assert all([len(new_class[name]) == len(new_class[in_pair[0][0]]) for name, _ in in_pair])

                        hp.heappush(priorityq, (len(new_class[in_pair[0][0]]), next_class, new_class))
                        next_class += 1
                    
                    continue
        
            if debug: print(f"Encoding class {class_ind} of size {length}                           ", end="\r")
            if debug: classes_encoded.append(length)

            class_encoding(
                class_, in_pair, mapp, ckmapp, formula, assumptions, signal_info
            )  
        
        if debug: print("Total Cons Encoded: ", sum(classes_encoded), "                                                             ")
        if debug: print("Classes Encoded: ", count_ints(classes_encoded))
        signal_encoding(in_pair, mapp, formula, assumptions, signal_info)

        res = [formula, assumptions]

        if return_signal_mapping: res.append(mapp)
        if return_constraint_mapping: res.append(ckmapp)
        return res
