from typing import Dict, List, Tuple, Callable, Set, Iterable
from pysat.formula import CNF
import itertools

from bij_encodings.assignment import Assignment
from bij_encodings.encoder import Encoder
from bij_encodings.online_info_passing import count_ints

from bij_encodings.reduced_encoding.red_natural_encoding import internal_consistency

from r1cs_scripts.circuit_representation import Circuit

from comparison.constraint_preprocessing import known_split

from normalisation import r1cs_norm

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

        if ckmapp is None: ckmapp =  Assignment(assignees=3, link=mapp)
        if signal_info is None: signal_info = {
            name: {}
            for name, _ in in_pair
        }
            
        if return_encoded_classes: classes_encoded = []
        if debug: class_ind = 1

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

        k = 0
        while len(classes[in_pair[0][0]].values()) > 0:
            k += 1
            
            min_size = min(map(lambda class_ : len(class_), classes[in_pair[0][0]].values()))

            current_batch = map(
                lambda key : {name: classes[name][key] for name, _ in in_pair},
                filter(
                    lambda key: len(classes[in_pair[0][0]][key]) <= batching_multiplier * min_size,
                    classes[in_pair[0][0]].keys()
                )
            )

            for class_ in current_batch:
                
                length = len(class_[in_pair[0][0]])
                if debug: print(f"Encoding class {class_ind} of size {length}                           ", end="\r")
                if return_encoded_classes: classes_encoded.append(length)
                if debug: class_ind += 1

                class_encoding(class_, in_pair, mapp, ckmapp, formula, assumptions, signal_info)

            internal_consistency(in_pair, mapp, formula, assumptions, signal_info)

            if debug: print(f"Reclustering {len(classes[in_pair[0][0]].values())} classes, this is batch {k}                  ", end="\r")

            next_batches = map(
                lambda key : {name: classes[name][key] for name, _ in in_pair},
                filter(
                    lambda key: len(classes[in_pair[0][0]][key]) > batching_multiplier * min_size,
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
        
        # if debug and return_encoded_classes: print("Total Cons Encoded: ", sum(classes_encoded), "                                                             ")
        # if debug and return_encoded_classes: print("Classes Encoded: ", count_ints(classes_encoded))
        signal_encoding(in_pair, mapp, formula, assumptions, signal_info)

        res = [formula, assumptions]

        if return_signal_mapping: res.append(mapp)
        if return_constraint_mapping: res.append(ckmapp)
        if return_encoded_classes: res.append(count_ints(classes_encoded))
        return res


def recluster(
        in_pair: List[Tuple[str, Circuit]],
        classes: Iterable[Dict[str, List[int]]],
        clusters: Dict[str, Dict[str, Dict[int, List[int]]]],
        mapp: Assignment, signal_info: Dict[str, Dict[int, Set[int]]]
) -> Dict[str, Dict[str, List[int]]]:
    
    # reduce clusters numbers to hash
    classes, it2 = itertools.tee(classes)

    rehash_keys = {name: set([]) for name, _ in in_pair}

    for class_ in it2:
        for name, _ in in_pair:
            for coni in class_[name]:
                rehash_keys[name].update(
                    clusters[name]["coni_to_cluster"][coni] if coni in clusters[name]["coni_to_cluster"].keys() else []
               )

    # need the groups of cluster
    hash_mapp = Assignment(assignees=1)
    cluster_hashmapp = Assignment(assignees=1)
    re_cluster_hashmapp = Assignment(assignees=1)

    # redo the known_split hash only for each internal constraint + adjacency?
    clusters_to_hash = {name: {} for name, _ in in_pair}
    constraint_to_hash = {name: {} for name, _ in in_pair}

    def hash_cluster(name: str, circ: Circuit, key: int):
        known_split_cluster_hash = {}
        old_hash = clusters[name]["clusters_to_hash"][key]

        for consi in clusters[name]["clusters"][key]:

            # refactored to avoid expensive setdefault
            consi_hash = constraint_to_hash[name].setdefault(consi, None)
            if consi_hash is None:
                constraint_to_hash[name][consi] = hash_mapp.get_assignment(known_split(r1cs_norm(circ.constraints[consi]), name, mapp, signal_info))
                consi_hash = constraint_to_hash[name][consi]

            known_split_cluster_hash[consi_hash] = known_split_cluster_hash.setdefault(consi_hash, 0) + 1
    

        cluster_hash_ = f"{cluster_hashmapp.get_assignment(str(sorted(known_split_cluster_hash.items())))}:{old_hash}"


        return cluster_hash_

    for name, circ in in_pair:

        # Clusters information
        for cluster_ind in rehash_keys[name]:
            clusters_to_hash[name][cluster_ind] = hash_cluster(name, circ, cluster_ind)

        # Adjacency information
        if clusters[in_pair[0][0]]["adjacency"] != {}:
            for cluster_ind in rehash_keys[name]:

                # refactored since setdefault always evaluates default
                adjacent = clusters[name]['adjacency'][cluster_ind] if cluster_ind in clusters[name]['adjacency'].keys() else []
                
                [clusters_to_hash[name].setdefault(adj, None) for adj in adjacent]
                
                for adj in adjacent: 
                    if clusters_to_hash[name][adj] is None:
                        clusters_to_hash[name][adj] = hash_cluster(name, circ, adj)

                adj_hashes = sorted([clusters_to_hash[name][adj] for adj in adjacent])

                new_hash_ = re_cluster_hashmapp.get_assignment(f"{clusters_to_hash[name][cluster_ind]}:{adj_hashes}")

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

    # debugging errors
    # differences = set(new_classes["S1"].keys()).symmetric_difference(new_classes["S2"].keys())

    # if len(differences) > 1:
    #     print(list(map(len, new_classes.values())))

    #     for i, (name, _) in enumerate(in_pair):
    #         oname = in_pair[1 - i][0]
    #         for lvar in signal_info[name].keys():
    #             if len(signal_info[name][lvar]) == 1:
    #                 nset = next(iter(signal_info[name][lvar]))

    #                 rvar = mapp.get_inv_assignment(nset)[1-i]

    #                 if signal_info[oname][rvar] != signal_info[name][lvar]:
    #                     print(name, (lvar, rvar), signal_info[name][lvar], signal_info[oname][rvar])
        
    #     key_to_names = {"10": [], "01": [], "11":[]}
    #     for key in set(new_classes["S1"].keys()).union(new_classes["S2"].keys()):
    #         hash_ = f"{int(key in new_classes['S1'].keys())}{int(key in new_classes['S2'].keys())}"
    #         key_to_names[hash_].append(key)
        
    #     print(key_to_names)

    # pass these back to the main function
    return new_classes