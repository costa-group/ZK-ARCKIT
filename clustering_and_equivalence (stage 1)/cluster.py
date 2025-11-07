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
            options are: local, structural, total, none, naive
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

    --r1cs
        assumes input file is in the r1cs format
        : default
            this is default behaviour
    
    --acir
        assumes that the input format is in the acir format
        : default
            assumes r1cs by default
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
from circuits_and_constraints.r1cs.r1cs_circuit import R1CSCircuit
from circuits_and_constraints.acir.acir_circuit import ACIRCircuit
from testing_harness import time_limit

from structural_analysis.utilities.constraint_graph import shared_signal_graph
from structural_analysis.utilities.connected_preprocessing import componentwise_preprocessing, preclustering
from structural_analysis.clustering_methods.nonlinear_attract import nonlinear_attract_clustering
# from structural_analysis.clustering_methods.linear_coefficient import cluster_by_linear_coefficient #TODO: maybe refactor but not promising enough to spend time on
from structural_analysis.cluster_trees.dag_from_clusters import dag_from_partition, partition_from_partial_clustering, dag_to_nodes
from structural_analysis.cluster_trees.full_equivalency_partitions import subcircuit_fingerprinting_equivalency, subcircuit_fingerprint_with_structural_augmentation_equivalency, subcircuit_fingerprinting_equivalency_and_structural_augmentation_equivalency
from structural_analysis.utilities.graph_to_img import dag_graph_to_img
from structural_analysis.cluster_trees.dag_postprocessing import merge_passthrough, merge_only_nonlinear
from structural_analysis.clustering_methods.iterated_louvain import iterated_louvain
from maximal_equivalence.applied_maximal_equivalence import maximally_equivalent_classes
from structural_analysis.cluster_trees.dag_from_clusters import DAGNode

def circuit_cluster(
        input_filename: str,
        fileformat: str,
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
        minimum_circuit_size: int = 100,
        output_automatic_clusters: bool = True,
        skip_preprocessing: bool = False,
        preclustering_file: str | None = None,
        leiden_iterations: int = -1,
        single_json: bool = False,
        debug: bool = False,
    ):
    """
    Manager function for handling the clustering methods, for a complete specification see `cluster.py'
    """

    if seed is None:
        seed = random.randint(0,25565)

    if debug:
        log = []
        debug_start_time = time.time()
        debug_last_time = debug_start_time

    match fileformat:
        case "r1cs": 
            if input_filename[len(input_filename) - input_filename[::-1].index("."):] != "r1cs": warnings.warn(f"File {input_filename} provided is not of type .r1cs")
            main_circ = R1CSCircuit()
        case "acir": main_circ = ACIRCircuit()
        case _:
            raise SyntaxError(f"fileformat provided is of unspecified type {fileformat}")

    main_circ.parse_file(input_filename)

    if debug:
        
        debug_parsing_time = time.time()
        logging_lines([f"File Parsed: {debug_parsing_time - debug_last_time}s"], [log])
        debug_last_time = debug_parsing_time

    if preclustering_file is not None:
        circs, minimum_size_clusterings, sig_inverse, coni_inverse = preclustering(main_circ, preclustering_file, minimum_circuit_size=minimum_circuit_size, output_automatic_clusters=output_automatic_clusters, debug=debug)

        if debug:
            debug_preclustering_time = time.time()
            logging_lines([str(len(circs)), f"File Preclustered: {debug_preclustering_time - debug_last_time}s"], [log])
            debug_last_time = debug_preclustering_time

        if not skip_preprocessing:
            iterable = zip(circs, sig_inverse, coni_inverse)
            circs = []
            sig_inverse = []
            coni_inverse = []

            for circ, sig_inv, coni_inv in iterable:
                circs_, minimum_size_clusterings_, sig_inverse_, coni_inverse_ = componentwise_preprocessing(circ, minimum_circuit_size=minimum_circuit_size, output_automatic_clusters=output_automatic_clusters, debug=False)
                circs.extend(circs_)
                minimum_size_clusterings.extend(minimum_size_clusterings_)
                sig_inverse.extend([{key: sig_inv[val] for key, val in sig_inv_.items()} for sig_inv_ in sig_inverse_])
                coni_inverse.extend([list(map(coni_inv.__getitem__, coni_inv_)) for coni_inv_ in coni_inverse_])

    elif not skip_preprocessing:
        circs, minimum_size_clusterings, sig_inverse, coni_inverse = componentwise_preprocessing(main_circ, minimum_circuit_size=minimum_circuit_size, output_automatic_clusters=output_automatic_clusters, debug=debug)
    else:
        undo_remapping = False
        circs = [main_circ]
        minimum_size_clusterings = []
    
    if not undo_remapping: sig_inverse, coni_inverse = None, None

    if main_circ.nOutputs == 0: warnings.warn("Your circuit has no outputs, this may cause undefined behaviour")
    if main_circ.nInputs == 0: warnings.warn("Your circuit has no inputs, this may cause undefined behaviour")

    # TODO: pass mapping data to output json
    # TODO: add timing information for utility/debugging

    if debug:
        debug_preprocessing_time = time.time()
        logging_lines([str(len(circs)), f"File Preprocessed: {debug_preprocessing_time - debug_last_time}s"], [log])
        debug_last_time = debug_preprocessing_time

    circuit_graph = None ## what's this?

    filename = input_filename[len(input_filename)-input_filename[::-1].index("/"):len(input_filename)-input_filename[::-1].index(".")-1]
    suffixes = [clustering_method, equivalence_method]
    
    if maxequiv: suffixes.append('maxequiv')
    match maxequiv_merge:
        case 1: suffixes.append('unsafe_linear')
        case 2: suffixes.append('single_linear')
        case _: pass
    
    would_output_single_file: bool = len(circs) == 0 or (len(circs) == 1 and ( len(minimum_size_clusterings) == 0 or not output_automatic_clusters )) 
    print(would_output_single_file)

    get_outfile =  lambda index, ftype : f"{output_directory}/{filename + ('_' if len(suffixes) > 0 else '') + '_'.join(suffixes)}{'' if would_output_single_file or single_json else ('/' + str(index))}.{ftype}"

    if len(circs) > 0 and (len(circs) > 1 or len(minimum_size_clusterings) != 0):
        try:
            output_path = get_outfile(0, "json")
            os.mkdir(output_path[:len(output_path) - output_path[::-1].index("/") - 1])
        except FileExistsError:
            pass

    if sanity_check:
        sanity_check_maintanence = {} if len(circs) == 0 else [{} for _ in range(len(circs))]
        add_sanity_check = lambda index, key, value : sanity_check_maintanence.__setitem__(key, value) if len(circs) == 0 else sanity_check_maintanence[index].__setitem__(key, value)
    
    index_offset = 0
    if single_json and not would_output_single_file:
        return_json = {
            "seed": seed,
            "timing": {},
            "data": {
                "seeds_list": [],
                "timings_list": [],
                "datas_list": []
            },
            "circuit_sizes": [],
            "nodes": []
        }

    if len(minimum_size_clusterings) > 0 and output_automatic_clusters:

        if debug: print("################### Dealing with Auto-Clusters ###################")
        
        start = time.time()
        equivalency = {}
        mappings = {}
        nodes = {index : DAGNode(main_circ, index, constraints, signals.intersection(main_circ.get_input_signals()), signals.intersection(main_circ.get_output_signals()))
            for index, constraints, signals in itertools.starmap(lambda index, cluster : (index, cluster, set(itertools.chain.from_iterable(map(lambda coni : main_circ.constraints[coni].signals(), cluster)))), enumerate(minimum_size_clusterings))}
        dagnode_conversion_time = time.time()

        # TODO: need to check input here
        if equivalence_method == 'naive':
            equivalency = { 'local': [[nkey] for nkey in nodes.keys()] }
            mappings = { 'local': [[] for _ in nodes] }

        elif equivalence_method != "none":
            equivalency_list, mappings_list = subcircuit_fingerprinting_equivalency(nodes)
            equivalency, mappings = {}, {}
            if equivalence_method in ['local', 'total']:
                equivalency['local'] = equivalency_list
                mappings['local'] = mappings_list
            if equivalence_method in ['structural', 'total']:
                equivalency['structural'] = equivalency_list
                mappings['structural'] = mappings_list
        equivalency_timing = time.time()

        timing = {"format_conversion_time": dagnode_conversion_time - start, "equivalency_time": equivalency_timing - dagnode_conversion_time, "total": equivalency_timing - start}
        nodes_to_dict_iterator = map(lambda n : n.to_dict(inverse_mapping = None), nodes.values())

        if single_json:
            index_offset += len(nodes)
            return_json["circuit_sizes"].append(len(nodes))

            return_json["data"]["seeds_list"].append(None)
            return_json["data"]["timings_list"].append(timing)
            return_json["data"]["datas_list"].append(f"The first {len(nodes)} nodes in this are automatically clustered isolated connected components, due to having less than {minimum_circuit_size} constraints")
            return_json["nodes"].extend(nodes_to_dict_iterator)
            if equivalency != {}: 
                for equiv in equivalency: return_json.setdefault(f"equivalency_{equiv}", []).extend(equivalency[equiv])
            if mappings != {} and include_mappings: 
                for equiv in mappings: return_json.setdefault(f"equiv_mapping_{equiv}", []).extend(mappings[equiv])
        else:

            return_json = {
                "seed": seed,
                "timing": timing,
                "data": {"note": "the following connected components were clustered automatically due to having too small a size"},
                "nodes": list(nodes_to_dict_iterator)
            }

            if equivalency != {}: 
                for equiv in equivalency: return_json[f"equivalency_{equiv}"] = equivalency[equiv]
            if mappings != {} and include_mappings: 
                for equiv in mappings: return_json[f"equiv_mapping_{equiv}"] = mappings[equiv]

            if debug: print("------------------- Writing Auto-Clusters To File -------------------")

            f = open(get_outfile("automatic", "json"), "w")
            json.dump(return_json, f, indent=4)
            f.close()

        minimum_size_clusterings = None

    for index, circ in enumerate(circs):

        if index > 0:
            seed = random.Random(seed).randint(0,25565)

        timing = {}
        data = {}

        start = time.time()
        last_time = start
    
        if debug:
            logging_lines([f"################################# clustering {index} #################################", f"nConstraints {circ.nConstraints}, nWires {circ.nWires}"], [log])
            circuit_log = []

        match clustering_method:
            # This is mostly merging various output types, we could probably reformat everything to make this better

            case "nonlinear_attract":
                clusters, _, remaining = nonlinear_attract_clustering(circ, pre_merge = automerge_only_nonlinear)
                partition = partition_from_partial_clustering(circ, clusters.values(), remaining=remaining)

            case "louvain":
                random.seed(seed)
                circuit_graph = shared_signal_graph(circ)
                if debug: logging_lines([f"Graph Created in: {time.time() - last_time}"], [log, circuit_log])
                partition = circuit_graph.community_leiden(
                        objective_function = 'modularity',
                        resolution = circ.nConstraints ** 0.5,
                        n_iterations = leiden_iterations
                    )
                if debug: logging_lines([f"Modularity: {partition.modularity}"], [log, circuit_log])

            case "iterated_louvain":
                circuit_graph = shared_signal_graph(circ)
                partition, resolution = iterated_louvain(circuit_graph, init_resolution=circ.nConstraints ** 0.5, seed=seed)
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

        if not return_img: circuit_graph = None
        timing['clustering'] = time.time() - last_time
        last_time = time.time()

        if debug: logging_lines([f"File Clustered: {timing['clustering']}s", f"Num Clusters: {len(partition)}"], [log, circuit_log])

        partition, arcs = dag_from_partition(circ, partition)
        nodes = dag_to_nodes(circ, partition, arcs, index_offset=index_offset)
        partition = None

        if single_json: index_offset += len(nodes)

        timing['dag_construction'] = time.time() - last_time
        last_time = time.time()

        if debug: logging_lines([f"Dag Consructed: {timing['dag_construction']}s"], [log, circuit_log])

        if sanity_check:
            # calculate which coni are not included in the partition
            removed_coni = list(map(coni_inverse[index].__getitem__, set(range(circ.nConstraints)).difference(itertools.chain.from_iterable(map(lambda node : node.constraints, nodes.values())))))
            add_sanity_check(index, "post_dag_conversion", removed_coni)

        if automerge_passthrough: 
            nodes = merge_passthrough(circ, nodes)
            timing['passthrough_merge'] = time.time() - last_time
            last_time = time.time()
            if debug: logging_lines([f"Passthrough Merging Done: {timing['passthrough_merge']}s", f"Num Nodes: {len(nodes)}"], [log, circuit_log])
                

        if automerge_only_nonlinear: 
            nodes = merge_only_nonlinear(circ, nodes)
            timing['nonlinear_merge'] = time.time() - last_time
            last_time = time.time()
            if debug: logging_lines([f"Only Nonlinear Merging Done: {timing['nonlinear_merge']}s", f"Num Nodes: {len(nodes)}"], [log, circuit_log])

        if sanity_check:
            # calculate which coni are not included in the partition
            removed_coni = list(map(coni_inverse[index].__getitem__, set(range(circ.nConstraints)).difference(itertools.chain.from_iterable(map(lambda node : node.constraints, nodes.values())))))
            add_sanity_check(index, "post_merge_postprocessing", removed_coni)

        if return_img:
            if circuit_graph is None: circuit_graph = shared_signal_graph(circ)
            dag_graph_to_img(circ, circuit_graph, nodes, get_outfile(index, clustering_method, "png"))

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

            case "naive":
                equivalency = {"local": [[nkey] for nkey in nodes.keys()]}
                mappings = {"local": [[] for _ in nodes]}

            case "none":
                pass

            case _ :
                raise SyntaxError(f"{equivalence_method} is not a valid equivalence method")

        timing['equivalency'] = time.time() - last_time
        last_time = time.time()

        if equivalence_method != "none" and debug: logging_lines([f"Equivalency Done: {timing['equivalency']}s", f"Number of Classes: {','.join(str(len(equiv)) for equiv in equivalency.values())}"], [log, circuit_log])

        if maxequiv:

            if equivalence_method == "none":
                raise AssertionError("Can't do maxequiv without an equivalency method")

            nodes, equivalency, mappings = maximally_equivalent_classes(nodes, 
                                                                        equivalency['structural'] if equivalence_method == 'structural' else equivalency['local'], 
                                                                        mappings['structural'] if equivalence_method == 'structural' else mappings['local'], 
                                                                        tol = maxequiv_tol, solver_timeout=maxequiv_timeout, return_json=False, 
                                                                        postprocessing_merge = maxequiv_merge, equivalence_method=equivalence_method)

            timing["maxequiv"] = time.time() - last_time
            last_time = time.time()

            if debug: logging_lines([f"Equivalency Done: {timing['equivalency']}s", f"Num Nodes: {len(nodes)}", f"Number of Classes: {','.join(str(len(equiv)) for equiv in equivalency.values())}"], [log, circuit_log])
            if sanity_check:
                # calculate which coni are not included in the partition
                removed_coni = list(map(coni_inverse[index].__getitem__, set(range(circ.nConstraints)).difference(itertools.chain.from_iterable(map(lambda node : node.constraints, nodes.values())))))
                add_sanity_check(index, "post_maxequiv", removed_coni)

        timing['total'] = time.time() - start

        ### FINAL STEPS TO WRITE TO FILE ###

        if single_json and not would_output_single_file:

            for timeslot, timeval in timing.items():
                return_json["timing"][timeslot] = return_json["timing"].get(timeslot, 0) + timeval
            
            return_json["data"]["seeds_list"].append(seed)
            return_json["data"]["timings_list"].append(timing)
            return_json["circuit_sizes"].append(len(nodes))
            if data != {}: return_json["data"]["datas_list"].append(data)

            return_json["nodes"].extend(map(lambda n : n.to_dict(inverse_mapping = (coni_inverse[index], sig_inverse[index]) if undo_remapping else None ), nodes.values()))
            if equivalence_method != "none":
                for equiv in equivalency:
                    return_json.setdefault(f"equivalency_{equiv}", []).extend(equivalency[equiv])
                if include_mappings: 
                    for equiv in mappings:
                        return_json.setdefault(f"equiv_mapping_{equiv}", []).extend(mappings[equiv])
                

        else:
            return_json = {
                "seed": seed,
                "timing": timing,
                "data": data,
                "nodes": list(map(lambda n : n.to_dict(inverse_mapping = (coni_inverse[index], sig_inverse[index]) if undo_remapping else None ), nodes.values()))
            }

            if debug: data["log"] = circuit_log
            if equivalence_method != "none":
                for equiv in equivalency:
                    return_json[f"equivalency_{equiv}"] = equivalency[equiv]

                if include_mappings: 
                    for equiv in mappings:
                        return_json[f"equiv_mapping_{equiv}"] = mappings[equiv]

            if sanity_check: return_json["sanity_check"] = sanity_check_maintanence

            with open(get_outfile(index, "json"), "w") as f: json.dump(return_json, f, indent=4)

    if single_json and not would_output_single_file:
        with open(get_outfile(index, "json"), "w") as f: json.dump(return_json, f, indent=4)

    if debug:
        f = open(get_outfile("log", "txt"), "w")
        f.writelines(f"{line}\n" for line in log)
        f.close()

def logging_lines(lines: List[str], logs: List[List[str]]) -> None:
    for line in lines:
        for log in logs: log.append(line)
        print(line)



if __name__ == '__main__':

    req_args = [None, None, None, None, None]
    timeout = 0
    automerge_passthrough, automerge_only_nonlinear, return_img , timing, undo_remapping, include_mappings = True, False, False, True, True, False
    maxequiv, maxequiv_timeout, maxequiv_tol, maxequiv_merge, sanity_check, seed, debug, minimum_circuit_size = False, 5, 0.8, 0, False, None, False, 100
    output_automatic_clusters, skip_preprocessing, preclustering_file, leiden_iterations, single_json = True, False, None, -1, False

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
                set_file(2, sys.argv[i+1])
                i += 2
            case "--outfile": 
                set_file(2, sys.argv[i+1])
                i += 2
            case "-c": 
                set_file(3, sys.argv[i+1])
                i += 2
            case "--clustering": 
                set_file(3, sys.argv[i+1])
                i += 2
            case "-e": 
                set_file(4, sys.argv[i+1])
                i += 2
            case "--equivalence": 
                set_file(4, sys.argv[i+1])
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
            case "-p":
                if sys.argv[i+1][0] == '-': raise SyntaxError(f"Invalid preclustering value {sys.argv[i+1]}")
                preclustering_file = sys.argv[i+1]
                i += 2
            case "-preclustering":
                if sys.argv[i+1][0] == '-': raise SyntaxError(f"Invalid preclustering value {sys.argv[i+1]}")
                preclustering_file = sys.argv[i+1]
                i += 2
            case "--minimum-circuit-size":
                if sys.argv[i+1][0] == '-': raise SyntaxError(f"Invalid minimum circuit size value value {sys.argv[i+1]}")
                minimum_circuit_size = int(sys.argv[i+1])
                i += 2
            case "--leiden-iterations":
                if sys.argv[i+1][0] == '-': raise SyntaxError(f"Invalid minimum circuit size value value {sys.argv[i+1]}")
                leiden_iterations = int(sys.argv[i+1])
                i += 2
            case "-i": return_img, i = True, i + 1
            case "-m": include_mappings, i = True, i+1
            case "--include-mappings": include_mappings, i = True, i+1
            case "--dont-undo-mapping": undo_remapping, i = False, i+1
            case "--single-json": single_json, i = True, i+1
            case "--return_img": return_img, i = True, i + 1
            case "--dont-automerge-passthrough": automerge_passthrough, i = False, i + 1
            case "--automerge-only-nonlinear": automerge_only_nonlinear, i = True, i + 1
            case "--dont-output-automatic-clusters": output_automatic_clusters, i = False, i + 1,
            case "--skip-preprocessing": skip_preprocessing, i = True, i + 1,
            case "--no-timing-information": timing, i = False, i+1
            case "--maximal-equivalence": maxequiv, i = True, i+1
            case "--sanity-check": sanity_check, i = True, i+1
            case "--debug": debug, i = True, i+1
            case "-d": debug, i = True, i+1
            case "-M": maxequiv, i = True, i+1
            case "--maxequiv-timeout": 
                if sys.argv[i+1][0] == '-': raise SyntaxError(f"Invalid timeout value {sys.argv[i+1]}")
                maxequiv_timeout, i = int(sys.argv[i+1]), i+2
            case "--maxequiv-tolerance": 
                if sys.argv[i+1][0] == '-': raise SyntaxError(f"Invalid tolerance value {sys.argv[i+1]}")
                maxequiv_tol, i = float(sys.argv[i+1]), i+2
            case "--maxequiv-merge": 
                if sys.argv[i+1][0] == '-': raise SyntaxError(f"Invalid merge value {sys.argv[i+1]}")
                maxequiv_merge, i = int(sys.argv[i+1]), i+2
            case "--r1cs": req_args[1], i = "r1cs", i+1
            case "--acir": req_args[1], i = "acir", i+1
            case _: warnings.warn(f"Invalid argument '{arg}' ignored", SyntaxWarning)


    if req_args[0] is None: raise SyntaxError("No input file given")
    if req_args[1] is None: req_args[1] = "r1cs"
    if req_args[2] is None: req_args[2] = req_args[0][:req_args[0].index(".")]
    if req_args[3] is None: req_args[3] = "louvain"
    if req_args[4] is None: req_args[4] = "structural"

    with time_limit(timeout):
        circuit_cluster(*req_args, automerge_passthrough=automerge_passthrough, automerge_only_nonlinear=automerge_only_nonlinear, return_img=return_img, timing=timing, undo_remapping = undo_remapping, include_mappings=include_mappings, 
            maxequiv=maxequiv, maxequiv_tol=maxequiv_tol, maxequiv_timeout=maxequiv_timeout, maxequiv_merge=maxequiv_merge, sanity_check=sanity_check, seed = seed, minimum_circuit_size=minimum_circuit_size, 
            output_automatic_clusters=output_automatic_clusters, skip_preprocessing=skip_preprocessing, preclustering_file=preclustering_file, leiden_iterations=leiden_iterations, single_json=single_json, debug=debug)

    # python3 cluster.py r1cs_files/binsub_test.r1cs -o clustering_tests -e structural