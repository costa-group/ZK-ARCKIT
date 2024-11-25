from typing import Dict, List, Tuple, Callable, Set, Iterable
from pysat.formula import CNF
import itertools

from bij_encodings.assignment import Assignment
from bij_encodings.encoder import Encoder
from bij_encodings.online_info_passing import count_ints

from r1cs_scripts.circuit_representation import Circuit

from comparison.constraint_preprocessing import known_split

from normalisation import r1cs_norm

## TODO: update so that unordered stuff is handled correctly
# TODO: add docstring/ refactor to get rid of reclustering

class BatchedInfoPassEncoder(Encoder):

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
            signal_info: Dict[str, Dict[int, int]] = None,
            batching_multiplier: int = 1
        ) -> CNF:
        """
        The encode method for the BatchedInfoPassEncoder

        This method encodes a set of classes in batches of the minimum size. It will encode all clusters of min size `k`, then 
        will apply the knowledge gained from encoding these classes to all remaining clusters, repeating this process until all clusters
        have been encoded.

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
        if debug: class_ind = 1

        # Instead of always doing the next one and redoing it, we recluster after every batch of the same size, then resort.
        k = 0
        while len(classes[in_pair[0][0]].values()) > 0:
            k += 1
            
            min_size = min(map(lambda class_ : len(class_), classes[in_pair[0][0]].values()))

            # get all classes of the minimum size (within multiplier bounds)
            current_batch = map(
                lambda key : {name: classes[name][key] for name, _ in in_pair},
                filter(
                    lambda key: len(classes[in_pair[0][0]][key]) <= batching_multiplier * min_size,
                    classes[in_pair[0][0]].keys()
                )
            )

            # encoded all the classes in the current batch
            for class_ in current_batch:
                
                length = len(class_[in_pair[0][0]])
                if debug: print(f"Encoding class {class_ind} of size {length}                           ", end="\r")
                if return_encoded_classes: classes_encoded.append(length)
                if debug: class_ind += 1

                class_encoding(class_, in_pair, mapp, ckmapp, formula, assumptions, signal_info)

            # consistency updates now to be done in class encoder (less checks required)
            # internal_consistency(in_pair, mapp, formula, assumptions, signal_info)

            if debug: print(f"Reclustering {len(classes[in_pair[0][0]].values())} classes, this is batch {k}                  ", end="\r")

            next_batches = map(
                lambda key : {name: classes[name][key] for name, _ in in_pair},
                filter(
                    lambda key: len(classes[in_pair[0][0]][key]) > batching_multiplier * min_size,
                    classes[in_pair[0][0]].keys()
                )
            )

            # re-encode remaining classes
            new_classes = {
                name: {} for
                name, _  in in_pair
            }

            hash_mapp = Assignment(assignees=1)

            for ind, class_ in enumerate(next_batches):
                for name, circ in in_pair:
                    for consi in class_[name]:
                        new_classes[name].setdefault(f"{ind}:{hash_mapp.get_assignment(known_split(r1cs_norm(circ.constraints[consi]), name, mapp, signal_info))}", []).append(consi)
        
            classes = new_classes
        
        signal_encoding(in_pair, mapp, formula, assumptions, signal_info)

        res = [formula, assumptions]

        if return_signal_mapping: res.append(mapp)
        if return_constraint_mapping: res.append(ckmapp)
        if return_encoded_classes: res.append(count_ints(classes_encoded))
        return res