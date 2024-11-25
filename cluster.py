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
            nonlinear_attract
        : alternative
            --clustering
    
    --return_img
        defines if the return type is an image or json file
        : default
            json file
        : alternative
            -i

    --automerge-passthrough
        recursively auto-merges clusters that have a signal both as an input and an output
        : default
            does not merge

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

from r1cs_scripts.circuit_representation import Circuit
from r1cs_scripts.read_r1cs import parse_r1cs
from networkx.algorithms.community import louvain_communities

from structural_analysis.utilities.constraint_graph import shared_signal_graph
from structural_analysis.utilities.connected_preprocessing import componentwise_preprocessing
from structural_analysis.clustering_methods.nonlinear_attract import nonlinear_attract_clustering
from structural_analysis.cluster_trees.dag_from_clusters import dag_from_partition, partition_from_partial_clustering, dag_to_nodes, nodes_to_json
from structural_analysis.cluster_trees.equivalent_partitions import easy_fingerprint_then_equivalence
from structural_analysis.utilities.graph_to_img import dag_graph_to_img
from structural_analysis.cluster_trees.dag_postprocessing import merge_passthrough, merge_only_nonlinear

def r1cs_cluster(
        input_filename: str,
        output_directory: str,
        clustering_method: str,
        return_img: bool = False,
        automerge_passthrough: bool = False,
        automerge_only_nonlinear: bool = False
    ):
    """
    Manager function for handling the clustering methods, for a complete specification see `cluster.py'
    """
    
    circ = Circuit()
    parse_r1cs(input_filename, circ)

    circs, sig_mapping, con_mapping = componentwise_preprocessing(circ)
    # TODO: pass mapping data to output json
    # TODO: add timing information for utility/debugging

    g = None

    filename = input_filename[len(input_filename)-input_filename[::-1].index("/"):len(input_filename)-input_filename[::-1].index(".")-1]

    if len(circs) > 1:
        try:
            os.mkdir(f"{output_directory}/{filename}")
        except FileExistsError:
            pass
        
    get_outfile =  lambda index, suffix, ftype : f"{output_directory}/{filename if len(circs) == 1 else (filename + '/' + index)}{('_' + suffix) if suffix is not None else ''}.{ftype}"

    for index, circ in enumerate(circs):

        match clustering_method:
            # This is mostly merging various output types, we could probably reformat everything to make this better

            case "nonlinear_attract":
                clusters, _, remaining = nonlinear_attract_clustering(circ)
                partition = partition_from_partial_clustering(circ, clusters.values(), remaining=remaining)

            case "louvain":
                g = shared_signal_graph(circ.constraints)
                partition = list(map(list, louvain_communities(g, resolution=circ.nConstraints ** (0.5))))

            case _ :
                raise SyntaxError(f"{clustering_method} is not a valid clustering_method")

        partition, arcs = dag_from_partition(circ, partition)

        nodes = dag_to_nodes(circ, partition, arcs)

        if automerge_passthrough: nodes = merge_passthrough(circ, nodes)
        if automerge_only_nonlinear: nodes = merge_only_nonlinear(circ, nodes)

        equivalency = easy_fingerprint_then_equivalence(nodes)

        return_json = {
            "nodes": list(map(lambda n : n.to_dict(), nodes.values())) ,
            "equivalency": equivalency
        }

        # TODO: implement flag behaviour

        if return_img:
            if g is None: g = shared_signal_graph(circ.constraints)
            dag_graph_to_img(circ, g, nodes, get_outfile(index, clustering_method, "png"))

        else:
            f = open(get_outfile(index, clustering_method, "json"), "w")
            json.dump(return_json, f, indent=4)
            f.close()



if __name__ == '__main__':

    req_args = [None, None, None]
    automerge_passthrough, automerge_only_nonlinear, return_img = False, False, False

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
            case "-i": return_img, i = True, i + 1
            case "--return_img": return_img, i = True, i + 1
            case "--automerge-passthrough": automerge_passthrough, i = True, i + 1
            case "--automerge-only-nonlinear": automerge_only_nonlinear, i = True, i + 1
            case _: warnings.warn(f"Invalid argument '{arg}' ignored", SyntaxWarning)


    if req_args[0] is None: raise SyntaxError("No input file given")
    if req_args[1] is None: req_args[1] = req_args[0][:req_args[0].index(".")]
    if req_args[2] is None: req_args[2] = "nonlinear_attract"

    r1cs_cluster(*req_args, automerge_passthrough=automerge_passthrough, automerge_only_nonlinear=automerge_only_nonlinear, return_img=return_img)

    # python3 cluster.py r1cs_files/binsub_test.r1cs -o structural_analysis/clustered_graphs -i