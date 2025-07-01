"""
The file to call that handles all the sub-calls to cluster an R1CS circuit.

The following flags alter the behaviour of the file
    -f file_to_cluster.r1cs
        provides the location of the input file
        : default
            If the first argument is not a flag it is assumed to be the input file
        : alternative
        --file
    
    -o output_directory
        provides the output directory location and type
            note that this will determine the output behaviour of clustering
        : default 
            input file name
        : alternative 
            --outfile

    -c clustering_type
        defines the type of clustering method performed
            options are: nonlinear_attract, louvain
        : default
            louvain
        : alternative
            --clustering
    
    -e equivalence_type
        defines the type of equivalence method utilised
            options are: local, structural, total
        : default 
            structural
        : alternative
            --equivalence
    
    -m
        includes each mapping between equivalent clusters
        : default
            does not
        :alternative
            --include-mappings

    --return_img
        defines if the return type is an image or json file
        : default
            json file
        : alternative
            -i
    
    --timeout
        defines the timeout time for the program in seconds
        : default
            0 seconds (no timeout)
        : alternative
            -t

    --dont-undo-mapping
        doesn't undo the mapping from preprocessing
        : default
            signal/constraint indices as per original .r1cs
    
    --no-timing-information
        removes the timing breakdown from the JSON
        : default
            timing info is included in JSON

    --dont-automerge-passthrough
        doesn't recursively auto-merge clusters that have a signal both as an input and an output
        : default
            does merge

    --automerge-only-nonlinear
        auto-merges clusters that have no linear constraints to an adjacent cluster
        : default
            does not merge
"""
#TODO image subgraph selection??

from typing import Callable, Tuple, List
import sys
import warnings
import os
import json
import time
import itertools
import random

from circuits_and_constraints.abstract_circuit import Circuit
from networkx.algorithms.community import louvain_communities
from testing_harness import time_limit

from structural_analysis.utilities.constraint_graph import shared_signal_graph
from structural_analysis.utilities.connected_preprocessing import componentwise_preprocessing
from structural_analysis.clustering_methods.nonlinear_attract import nonlinear_attract_clustering
# from structural_analysis.clustering_methods.linear_coefficient import cluster_by_linear_coefficient #TODO: maybe refactor but not promising enough to spend time on
from structural_analysis.cluster_trees.dag_from_clusters import dag_from_partition, partition_from_partial_clustering, dag_to_nodes
from structural_analysis.cluster_trees.full_equivalency_partitions import subcircuit_fingerprinting_equivalency, subcircuit_fingerprint_with_structural_augmentation_equivalency, subcircuit_fingerprinting_equivalency_and_structural_augmentation_equivalency
from structural_analysis.utilities.graph_to_img import dag_graph_to_img
from structural_analysis.cluster_trees.dag_postprocessing import merge_passthrough, merge_only_nonlinear
from structural_analysis.clustering_methods.iterated_louvain import iterated_louvain
from maximal_equivalence.applied_maximal_equivalence import maximally_equivalent_classes

def r1cs_cluster(
        input_filename: str,
        output_directory: str,
        clustering_method: str,
        equivalence_method: str,
        return_img: bool = False,
        automerge_passthrough: bool = False,
        automerge_only_nonlinear: bool = False,
        timing: bool = True,
        undo_remapping: bool = True,
        include_mappings: bool = False,
        maxequiv: bool=False,
        maxequiv_timeout: int | None = None,
        maxequiv_tol: float | None = None,
        maxequiv_merge: int = 0,
        sanity_check: bool = False,
        seed = None,
    ):
    """
    Manager function for handling the clustering methods, for a complete specification see `cluster.py'
    """

    if seed is None:
        seed = random.randint(0,25565)
    
    

    main_circ = Circuit()
    main_circ.parse_file(input_filename)

    circs, sig_mapping, con_mapping = componentwise_preprocessing(main_circ) #NOTE: UPDATED SO NOW WON'T PUT (0,0) FOR R1CSCircuit
    
    if main_circ.nOutputs == 0: warnings.warn("Your circuit has no outputs, this may cause undefined behaviour")
    if main_circ.nInputs == 0: warnings.warn("Your circuit has no inputs, this may cause undefined behaviour")

    # TODO: pass mapping data to output json
    # TODO: add timing information for utility/debugging

    if undo_remapping:
        coni_inverse, sig_inverse = [[None for _ in range(circ.nConstraints)] for circ in circs], [[None for _ in range(circ.nWires)] for circ in circs]
        for mapping, inverse in zip([sig_mapping, con_mapping], [sig_inverse, coni_inverse]):
            for val_index, value in enumerate(mapping):
                if value is None: continue
                circ_index, new_val_index = value
                inverse[circ_index][new_val_index] = val_index

    g = None

    filename = input_filename[len(input_filename)-input_filename[::-1].index("/"):len(input_filename)-input_filename[::-1].index(".")-1]

    if len(circs) > 1:
        try:
            os.mkdir(f"{output_directory}/{filename}")
        except FileExistsError:
            pass

    if sanity_check:
        sanity_check_maintanence = {} if len(circs) == 0 else [{} for _ in range(len(circs))]
        add_sanity_check = lambda index, key, value : sanity_check_maintanence.__setitem__(key, value) if len(circs) == 0 else sanity_check_maintanence[index].__setitem__(key, value)
        
    get_outfile =  lambda index, suffixes, ftype : f"{output_directory}/{filename if len(circs) == 1 else (filename + '/' + str(index))}{('_' if len(suffixes) > 0 else '') + '_'.join(suffixes)}.{ftype}"

    for index, circ in enumerate(circs):

        timing = {}
        data = {}

        start = time.time()
        last_time = start

        match clustering_method:
            # This is mostly merging various output types, we could probably reformat everything to make this better

            case "nonlinear_attract":
                clusters, _, remaining = nonlinear_attract_clustering(circ, pre_merge = automerge_only_nonlinear)
                partition = partition_from_partial_clustering(circ, clusters.values(), remaining=remaining)

            case "louvain":
                g = shared_signal_graph(circ.constraints)
                partition = list(map(list, louvain_communities(g, resolution=circ.nConstraints ** 0.5, seed=seed)))

            case "iterated_louvain":
                g = shared_signal_graph(circ.constraints)
                partition, resolution = iterated_louvain(g, init_resolution=circ.nConstraints ** 0.5, seed=seed)
                partition = list(map(list, partition))
                data["final_resolution"] = resolution
            
            # case "linear_coefficient":
            #     clusters, _, remaining = cluster_by_linear_coefficient(circ, coefs=[-1])
            #     partition = partition_from_partial_clustering(circ, clusters.values(), remaining=remaining)

            case _ :
                raise SyntaxError(f"{clustering_method} is not a valid clustering_method")

        if sanity_check:
            # calculate which coni are not included in the partition
            removed_coni = list(map(coni_inverse[index].__getitem__, set(range(circ.nConstraints)).difference(itertools.chain(*partition))))
            add_sanity_check(index, "post_clustering_removed", removed_coni)

        timing['clustering'] = time.time() - last_time
        last_time = time.time()      

        partition, arcs = dag_from_partition(circ, partition)
        nodes = dag_to_nodes(circ, partition, arcs)

        timing['dag_construction'] = time.time() - last_time
        last_time = time.time()

        if sanity_check:
            # calculate which coni are not included in the partition
            removed_coni = list(map(coni_inverse[index].__getitem__, set(range(circ.nConstraints)).difference(itertools.chain(*map(lambda node : node.constraints, nodes.values())))))
            add_sanity_check(index, "post_dag_conversion", removed_coni)

        if automerge_passthrough: 
            nodes = merge_passthrough(circ, nodes)
            timing['passthrough_merge'] = time.time() - last_time
            last_time = time.time()
        if automerge_only_nonlinear: 
            nodes = merge_only_nonlinear(circ, nodes)
            timing['nonlinear_merge'] = time.time() - last_time
            last_time = time.time()

        if sanity_check:
            # calculate which coni are not included in the partition
            removed_coni = list(map(coni_inverse[index].__getitem__, set(range(circ.nConstraints)).difference(itertools.chain(*map(lambda node : node.constraints, nodes.values())))))
            add_sanity_check(index, "post_merge_postprocessing", removed_coni)

        if return_img:
            if g is None: g = shared_signal_graph(circ.constraints)
            dag_graph_to_img(circ, g, nodes, get_outfile(index, clustering_method, "png"))

        match equivalence_method:

            case "local":
                equivalency = {}
                mappings = {}
                local_equivalency, local_mapping = subcircuit_fingerprinting_equivalency(nodes)
                equivalency["local"] = local_equivalency
                mappings["local"] = local_mapping


            case "structural":
                equivalency = {}
                structural_equivalency, structural_mapping = subcircuit_fingerprint_with_structural_augmentation_equivalency(nodes)
                equivalency["structural"] = structural_equivalency
                mappings = {}
                mappings["structural"] = structural_mapping
            
            case "total":
                local_equiv, local_mapp, full_equiv, full_mapp = subcircuit_fingerprinting_equivalency_and_structural_augmentation_equivalency(nodes)

                equivalency = {
                    "local": local_equiv,
                    "structural": full_equiv
                }
                mappings = {
                    "local": local_mapp,
                    "structural": full_mapp
                }

            case _ :
                raise SyntaxError(f"{equivalence_method} is not a valid equivalence method")

        timing['equivalency'] = time.time() - last_time
        last_time = time.time()

        if maxequiv:
            nodes, equivalency, mappings = maximally_equivalent_classes(nodes, 
                                                                        equivalency['structural'] if equivalence_method == 'structural' else equivalency['local'], 
                                                                        mappings['structural'] if equivalence_method == 'structural' else mappings['local'], 
                                                                        tol = maxequiv_tol, solver_timeout=maxequiv_timeout, return_json=False, 
                                                                        postprocessing_merge = maxequiv_merge, equivalence_method=equivalence_method)

            timing["maxequiv"] = time.time() - last_time
            last_time = time.time()

            if sanity_check:
                # calculate which coni are not included in the partition
                removed_coni = list(map(coni_inverse[index].__getitem__, set(range(circ.nConstraints)).difference(itertools.chain(*map(lambda node : node.constraints, nodes.values())))))
                add_sanity_check(index, "post_maxequiv", removed_coni)

        timing['total'] = time.time() - start

        return_json = {
            "seed": seed,
            "timing": timing,
            "data": data,
            "nodes": list(map(lambda n : n.to_dict(inverse_mapping = (coni_inverse[index], sig_inverse[index]) if undo_remapping else None ), nodes.values())) ,
            
        }
        for equiv in equivalency:
            return_json[f"equivalency_{equiv}"] = equivalency[equiv]

        if include_mappings: 
            for m in mappings:
                return_json[f"equiv_mapping_{equiv}"] = mappings[m]

        if sanity_check: return_json["sanity_check"] = sanity_check_maintanence


        suffixes = [clustering_method, equivalence_method]
        if maxequiv: suffixes.append('maxequiv')
        match maxequiv_merge:
            case 1: suffixes.append('unsafe_linear')
            case 2: suffixes.append('single_linear')
            case _: pass

        f = open(get_outfile(index, suffixes, "json"), "w")
        json.dump(return_json, f, indent=4)
        f.close()



if __name__ == '__main__':

    req_args = [None, None, None, None]
    timeout = 0
    automerge_passthrough, automerge_only_nonlinear, return_img , timing, undo_remapping, include_mappings = True, False, False, True, True, False
    maxequiv, maxequiv_timeout, maxequiv_tol, maxequiv_merge, sanity_check, seed = False, 5, 0.8, 0, False, None

    def set_file(index: int, filename: str):
        if filename[0] == '-': raise SyntaxError(f"Invalid {'input' if not index else 'outout'} filename {filename}")
        if req_args[index] is None: req_args[index] = filename
        else: warnings.warn(f"Invalid file set: already set {'input' if not index else 'outout'} file to {req_args[index]}", SyntaxError)

    if len(sys.argv) == 1:
        raise SyntaxError("No File Provided")

    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]

        if arg[0] != "-":
            if i == 1:  req_args[0], i = arg, i + 1
            else: warnings.warn(f"Invalid argument '{arg}' ignored", SyntaxWarning)
            continue
        
        match arg:
            case "-f": 
                set_file(0, sys.argv[i+1])
                i += 2
            case "--file": 
                set_file(0, sys.argv[i+1])
                i += 2
            case "-o": 
                set_file(1, sys.argv[i+1])
                i += 2
            case "--outfile": 
                set_file(1, sys.argv[i+1])
                i += 2
            case "-c": 
                set_file(2, sys.argv[i+1])
                i += 2
            case "--clustering": 
                set_file(2, sys.argv[i+1])
                i += 2
            case "-e": 
                set_file(3, sys.argv[i+1])
                i += 2
            case "--equivalence": 
                set_file(3, sys.argv[i+1])
                i += 2
            case "-t":
                if sys.argv[i+1][0] == '-': raise SyntaxError(f"Invalid timeout value {sys.argv[i+1]}")
                timeout = int(sys.argv[i+1])
                i += 2
            case "--timeout":
                if sys.argv[i+1][0] == '-': raise SyntaxError(f"Invalid timeout value {sys.argv[i+1]}")
                timeout = int(sys.argv[i+1])
                i += 2
            case "-s":
                if sys.argv[i+1][0] == '-': raise SyntaxError(f"Invalid seed value {sys.argv[i+1]}")
                seed = int(sys.argv[i+1])
                i += 2
            case "--seed":
                if sys.argv[i+1][0] == '-': raise SyntaxError(f"Invalid seed value {sys.argv[i+1]}")
                seed = int(sys.argv[i+1])
                i += 2
            case "-i": return_img, i = True, i + 1
            case "-m": include_mappings, i = True, i+1
            case "--include-mappings": include_mappings, i = True, i+1
            case "--dont-undo-mapping": undo_remapping, i = True, i+1
            case "--return_img": return_img, i = True, i + 1
            case "--dont-automerge-passthrough": automerge_passthrough, i = False, i + 1
            case "--automerge-only-nonlinear": automerge_only_nonlinear, i = True, i + 1
            case "--no-timing-information": timing, i = False, i+1
            case "--maximal-equivalence": maxequiv, i = True, i+1
            case "--sanity-check": sanity_check, i = True, i+1
            case "-M": maxequiv, i = True, i+1
            case "--maxequiv-timeout": 
                if sys.argv[i+1][0] == '-': raise SyntaxError(f"Invalid timeout value {sys.argv[i+1]}")
                maxequiv_timeout, i = int(sys.argv[i+1]), i+2
            case "--maxequiv-tolerance": 
                if sys.argv[i+1][0] == '-': raise SyntaxError(f"Invalid timeout value {sys.argv[i+1]}")
                maxequiv_tol, i = float(sys.argv[i+1]), i+2
            case "--maxequiv-merge": 
                if sys.argv[i+1][0] == '-': raise SyntaxError(f"Invalid timeout value {sys.argv[i+1]}")
                maxequiv_merge, i = int(sys.argv[i+1]), i+2
            case _: warnings.warn(f"Invalid argument '{arg}' ignored", SyntaxWarning)


    if req_args[0] is None: raise SyntaxError("No input file given")
    if req_args[1] is None: req_args[1] = req_args[0][:req_args[0].index(".")]
    if req_args[2] is None: req_args[2] = "louvain"
    if req_args[3] is None: req_args[3] = "structural"

    with time_limit(timeout):
        r1cs_cluster(*req_args, automerge_passthrough=automerge_passthrough, automerge_only_nonlinear=automerge_only_nonlinear, return_img=return_img, timing=timing, undo_remapping = undo_remapping, include_mappings=include_mappings, 
            maxequiv=maxequiv, maxequiv_tol=maxequiv_tol, maxequiv_timeout=maxequiv_timeout, maxequiv_merge=maxequiv_merge, sanity_check=sanity_check, seed = seed)

    # python3 cluster.py r1cs_files/binsub_test.r1cs -o clustering_tests -e structural