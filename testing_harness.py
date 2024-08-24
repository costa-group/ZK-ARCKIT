import time
import json

from r1cs_scripts.circuit_representation import Circuit

from comparison_testing import get_circuits

from comparison.compare_circuits import circuit_equivalence
from bij_encodings.preprocessing.iterated_adj_reclassing import iterated_adjacency_reclassing

def exception_catcher(
    in_pair,
    info_preprocessing,
    cons_clustering,
    cons_grouping,
    cons_preprocessing,
    encoder,
    debug: bool = False,
    clustering_kwargs: dict = {},
    encoder_kwargs: dict = {}
    ):   

    start = time.time()
    try:
        test_data = circuit_equivalence(
            in_pair,
            info_preprocessing,
            cons_clustering,
            cons_grouping,
            cons_preprocessing,
            encoder,
            debug,
            clustering_kwargs,
            encoder_kwargs
        )
    except Exception as e:
        raise e
        print(e)
        test_data = {
            "result": "Error",
            "result_explanation": repr(e),
            "timing": {"error_time": time.time() - start}
        }
    test_data["test_type"] = "Affirmative"

    return test_data
    

def run_affirmative_test(
        filename: str,
        out_filename: str,
        seed: int,
        info_preprocessing,
        cons_clustering,
        cons_grouping,
        cons_preprocessing,
        encoder,
        debug: bool = False,
        clustering_kwargs: dict = {},
        encoder_kwargs: dict = {}
    ):

    in_pair = get_circuits(filename, seed = seed, 
        const_factor=True, shuffle_sig=True, shuffle_const=True)

    test_data = exception_catcher(
        in_pair,
        info_preprocessing,
        cons_clustering,
        cons_grouping,
        cons_preprocessing,
        encoder,
        debug,
        clustering_kwargs,
        encoder_kwargs
    )

    test_data["seed"] = seed

    # TODO: check result?

    f = open(out_filename, "w")
    json.dump(test_data, f, indent=4)
    f.close()

## current best imports

from r1cs_scripts.read_r1cs import parse_r1cs

from structural_analysis.graph_clustering.degree_clustering import twice_average_degree
from structural_analysis.graph_clustering.signal_equivalence_clustering import naive_removal_clustering
from comparison.cluster_preprocessing import groups_from_clusters
from bij_encodings.online_info_passing import OnlineInfoPassEncoder
from bij_encodings.reduced_encoding.red_class_encoder import reduced_encoding_class
from bij_encodings.reduced_encoding.red_pseudoboolean_encoding import pseudoboolean_signal_encoder

def run_current_best_test(
    lfilename: str,
    rfilename: str,
    outfile: str,
    compiler: str
    ):

    circ, circs = Circuit(), Circuit()

    parse_r1cs(lfilename, circ)
    parse_r1cs(rfilename, circs)

    in_pair = [("S1", circ), ("S2", circs)]

    if compiler == "O0": clustering = naive_removal_clustering
    else: clustering = twice_average_degree

    test_data = exception_catcher(
        in_pair,
        None,
        clustering,
        groups_from_clusters,
        iterated_adjacency_reclassing,
        OnlineInfoPassEncoder,
        encoder_kwargs= {
            "class_encoding" : reduced_encoding_class,
            "signal_encoding" : pseudoboolean_signal_encoder
        },
        debug=True
    )

    f = open(outfile, "w")
    json.dump(test_data, f, indent=4)
    f.close()
    