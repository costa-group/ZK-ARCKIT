from typing import Dict, List, Tuple, Callable, Set, Iterable
from pysat.formula import CNF

from bij_encodings.assignment import Assignment
from bij_encodings.encoder import Encoder
from bij_encodings.online_info_passing import count_ints

from r1cs_scripts.circuit_representation import Circuit

from comparison.constraint_preprocessing import known_split

from normalisation import r1cs_norm

class BatchedInfoPassEncoder(Encoder):

    def encode(
            self,
            classes: Dict[str, Dict[str, List[int]]],
            in_pair: List[Tuple[str, Circuit]],
            clusters: Dict[str, List[List[int]]] = None,
            class_encoding: Callable = None,
            signal_encoding: Callable = None,
            return_signal_mapping: bool = False,
            return_constraint_mapping = False, 
            debug: bool = False,
            formula: CNF = CNF(),
            mapp: Assignment = Assignment(),
            ckmapp: Assignment = None,
            assumptions: Set[int] = set([]),
            signal_info: Dict[str, Dict[int, int]] = None
        ) -> CNF:

        if ckmapp is None: ckmapp =  Assignment(assignees=3, link=mapp)
        if signal_info is None: signal_info = {
            name: {}
            for name, _ in in_pair
        }
            
        if debug: classes_encoded, class_ind = [], 1
            
        def get_next_min_batch(input: Dict[str, Dict[str, List[int]]]) -> Iterable[Dict[str, List[int]]]:
            # can be done in one pass but slower because python
            
            min_size = min(map(lambda class_ : len(class_)), input[in_pair[0][0]].values())
            return map(
                lambda key : {name: input[name][key] for name, _ in in_pair},
                filter(
                    lambda key: len(input[in_pair[0][0]][key]) == min_size,
                    input[in_pair[0][0]].keys()
                )
            )

        # Instead of always doing the next one and redoing it, we recluster after every batch of the same size, then resort.

        while len(classes[in_pair[0][0]].values()) > 0:
            
            min_size = min(map(lambda class_ : len(class_), classes[in_pair[0][0]].values()))

            current_batch = map(
                lambda key : {name: classes[name][key] for name, _ in in_pair},
                filter(
                    lambda key: len(classes[in_pair[0][0]][key]) == min_size,
                    classes[in_pair[0][0]].keys()
                )
            )

            for class_ in current_batch:
                
                if debug: 
                    length = len(class_[in_pair[0][0]])
                    print(f"Encoding class {class_ind} of size {length}                           ", end="\r")
                    classes_encoded.append(length)
                    class_ind += 1

                class_encoding(class_, in_pair, mapp, ckmapp, formula, assumptions, signal_info)

            next_batches = map(
                lambda key : {name: classes[name][key] for name, _ in in_pair},
                filter(
                    lambda key: len(classes[in_pair[0][0]][key]) != min_size,
                    classes[in_pair[0][0]].keys()
                )
            )

            if clusters is None:
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
            else:
                classes = recluster(in_pair, next_batches, clusters, mapp, signal_info)
        
        if debug: print("Total Cons Encoded: ", sum(classes_encoded), "                                                             ")
        if debug: print("Classes Encoded: ", count_ints(classes_encoded))
        signal_encoding(in_pair, mapp, formula, assumptions, signal_info)

        res = [formula, assumptions]

        if return_signal_mapping: res.append(mapp)
        if return_constraint_mapping: res.append(ckmapp)
        return res


def recluster(
        in_pair: List[Tuple[str, Circuit]],
        classes: List[Dict[str, List[int]]],
        clusters: Dict[str, Dict[str, Dict[int, List[int]]]],
        mapp: Assignment, signal_info: Dict[str, Dict[int, Set[int]]]
) -> Dict[str, Dict[str, List[int]]]:
    
    # need the groups of cluster
    hash_mapp = Assignment(assignees=1)
    cluster_hash_mapp = Assignment(assignees=1)
    re_cluster_hashmapp = Assignment(assignees=1)

    # redo the known_split hash only for each internal constraint + adjacency?
    clusters_to_hash = {name: {} for name, _ in in_pair}
    constraint_to_hash = {name: {} for name, _ in in_pair}

    for name, circ in in_pair:

        # Clusters information
        for cluster_ind, hash_ in clusters[name]["clusters_to_hash"].items():
            known_split_cluster_hash = {}

            for consi in clusters[name]["clusters"][cluster_ind]:
                constraint_to_hash[name][consi] = hash_mapp.get_assignment(known_split(r1cs_norm(circ.constraints[consi]), name, mapp, signal_info))

                known_split_cluster_hash[constraint_to_hash[name][consi]] = known_split_cluster_hash.setdefault(constraint_to_hash[name][consi], 0) + 1
            
            cluster_hash_ = f"{hash_}:{cluster_hash_mapp.get_assignment(str(sorted(known_split_cluster_hash.items())))}"
            clusters_to_hash[name][cluster_ind] = cluster_hash_

        # Adjacency information
        if clusters[in_pair[0][0]]["adjacency"] != {}:
            for cluster_ind in clusters[name]["clusters"].keys():

                new_hash_ = re_cluster_hashmapp.get_assignment(f"{clusters_to_hash[name][cluster_ind]}:{sorted([clusters_to_hash[name][adj] for adj in clusters[name]['adjacency'].setdefault(cluster_ind, [])])}")

                for consi in clusters[name]["clusters"][cluster_ind]:
                    constraint_to_hash[name][consi] = f"{new_hash_}:{constraint_to_hash[name][consi]}"
        
        # Removed constraints information
        for consi in clusters[name]["removed"]:
            constraint_to_hash[name][consi] = f"*{hash_mapp.get_assignment(known_split(r1cs_norm(circ.constraints[consi]), name, mapp, signal_info))}"

    # use this to further split the clusters that haven't yet been solved
    new_classes = {
        name: {}
        for name, _ in in_pair
    }
    
    for ind, class_ in enumerate(classes):
        for name, _ in in_pair:
            for consi in class_[name]:
                new_classes[name].setdefault(f"{ind}:{constraint_to_hash[name][consi]}", []).append(consi)

    # pass these back to the main function
    return new_classes