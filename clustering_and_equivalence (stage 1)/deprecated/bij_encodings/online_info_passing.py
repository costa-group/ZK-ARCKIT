from typing import Dict, List, Tuple, Callable, Set
from pysat.formula import CNF

from r1cs_scripts.circuit_representation import Circuit
from deprecated.comparison.constraint_preprocessing import known_split
from utilities.assignment import Assignment
from deprecated.bij_encodings.encoder import Encoder
from normalisation import r1cs_norm
from utilities.utilities import getvars, count_ints

class OnlineInfoPassEncoder(Encoder):
    """Encoder that before encoding any constraint class attempts to rehash based on knowledge to reduce size"""

    def encode(
            self,
            in_pair: List[Tuple[str, Circuit]],
            classes: Dict[str, Dict[str, List[int]]],
            clusters: Dict[str, Dict[str, Dict[int, Set[int]]]],
            class_encoding: Callable,
            signal_encoding: Callable,
            return_signal_mapping: bool = False,
            return_constraint_mapping: bool = False,
            return_encoded_classes: bool = False, 
            debug: bool = False,
            formula: CNF = CNF(),
            mapp: Assignment = Assignment(),
            ckmapp: Assignment = None,
            assumptions: Set[int] = set([]),
            signal_info: Dict[str, Dict[int, int]] = None
        ) -> CNF:
        """
        The encode method for the OnlineInfoPassEncoder

        Given a method of class_encoding and signal_encoding this will iteratively encode the smallest unencoded class. Before
        each class encoding it will run just the `known_info` part of the constraint hashing to check if any knowledge has been
        gained from previous encodings to break down the class further, otherwise it will encode the class as is.

        Parameters
        ----------
            in_pair: List[Tuple[str, Circuit]]
                Pair of circuit/name pairs for the input circuits
            classes: Dict[str, Dict[str, List[int]]]
                The constraint classes, for each circuitt name, and class hash the list of constraint indices that belong to that hash
            cluster:
                deprecated -- TODO: remove
            class_encoding: Callable
                the method of encoding the individual constraint classes into a pysat.CNF formula
            signal_encoding: Callable
                the method of encoding the signal clauses into a pysat.CN
            return_signal_mapping: Bool
                flag to return the signal_mapping Assignment object
            return_constraint_mapping: Bool
                flag to return the constraint_mapping Assignment object
            debug: Bool
                flag to print progress updates
            formula: CNF
                If applicable a preexisting formula to append onto
            mapp: Assignment
                incoming signal_mapping Assignment object
            ckmapp: Assignment
                incoming constraint_mapping Assignment object
            assumptions: Set[int]
                incoming fixed pairs
            signal_info
                incoming knowledge about signal potential pairs
        
        Returns
        ---------
        (formula, assumptions [, signal_mapping, constraint_mapping])
            Types and semantics as with parameters of the same name
        """

        if ckmapp is None: ckmapp =  Assignment(assignees=3, link=mapp)
        if signal_info is None: signal_info = {
            name: {}
            for name, _ in in_pair
        }
            
        if return_encoded_classes: classes_encoded = []

        normalised_constraints = {
            name: list(map(r1cs_norm, circ.constraints))
            for name, circ in in_pair
        }

        left_coni_has_unordered_AB = [any(map(lambda norm : len(norm.A) > 0 and list(norm.A.values()) == list(norm.B.values()), norms))  
                for norms in normalised_constraints[in_pair[0][0]]]
        
        # Ordered 'queue' of classes. Since whenever we rehash necesarily any new classes are the now smallest we can use a simple list
        priorityq = sorted([
            (len(classes[in_pair[0][0]][key]), 
             len(getvars(in_pair[0][1].constraints[classes[in_pair[0][0]][key][0]])),
             i, {name: classes[name][key] for name, _ in in_pair})
            for i, key in enumerate(classes[in_pair[0][0]].keys())
        ], reverse = True)

        next_class = len(priorityq)

        # TODO: test memory saving
        del classes[in_pair[0][0]]
        del classes[in_pair[1][0]]

        while len(priorityq) > 0:
            length, num_signals, class_ind, class_ = priorityq.pop()

            # all norms of classes are the same, so if 1 has an unordered norm, they all do
            unordered_class = left_coni_has_unordered_AB[class_[in_pair[0][0]][0]]

            if length > 1:
                new_classes = {}

                # rehash and create new class
                for name, _ in in_pair:
                    for int_, coni in enumerate(class_[name]):
                        if debug : print(f"For circ {name}, re-hashing class {class_ind}: constraint {int_} of size {length} x {num_signals}", end='\r')
                        hash_ = known_split(normalised_constraints[name][coni], name, mapp, signal_info, unordered_class)
                        new_classes.setdefault(hash_, {name_: [] for name_, _ in in_pair})[name].append(coni)

                # if len classes > 1 then we have created at least 1 new class
                if len(new_classes) > 1:
                    if debug : print(f"Broken down class {class_ind} of size {length} into classes: {count_ints(map(lambda class_ : len(class_[in_pair[0][0]]), new_classes.values()))}", end="\r")

                    new_classes = sorted([
                        (len(class_[in_pair[0][0]]), 
                        len(getvars(in_pair[0][1].constraints[class_[in_pair[0][0]][0]])),
                        next_class + i, class_)
                        for i, class_ in enumerate(new_classes.values())
                    ], reverse = True)

                    next_class += len(new_classes)
                    
                    for _, _, _, new_class in new_classes:
                        assert all([name in new_class.keys() for name, _ in in_pair]) 
                        assert len(new_class[in_pair[0][0]]) == len(new_class[in_pair[1][0]]), f"New class had size {len(new_class[in_pair[0][0]])} in S1 and {len(new_class[in_pair[1][0]])} in S2"

                    # next smallest will always be one of the new classes 
                    length, num_signals, class_ind, class_ = new_classes.pop()
                    priorityq.extend(new_classes)


            if debug: print(f"{mapp.curr.val}: Encoding class {class_ind} of size {length} x {num_signals}                   ", end="\r")
            if return_encoded_classes: classes_encoded.append(length)

            class_encoding(
                class_, 
                {name: list(map(normalised_constraints[name].__getitem__, class_[name]))
                 for name, _ in in_pair}, 
                in_pair, mapp, ckmapp, formula, assumptions, signal_info, unordered_class
            )  
        # TODO: return some 'broken down' counter so we can better compare equivalent times.

        # if debug and return_encoded_classes: print("Total Cons Encoded: ", sum(classes_encoded), "                                                             ")
        # if debug and return_encoded_classes: print("Classes Encoded: ", count_ints(classes_encoded))
        if debug: print("Now encoding the signals          ", end='\r')
        signal_encoding(in_pair, mapp, formula, assumptions, signal_info)

        res = [formula, assumptions]

        if return_signal_mapping: res.append(mapp)
        if return_constraint_mapping: res.append(ckmapp)
        if return_encoded_classes: res.append(count_ints(classes_encoded))
        return res
