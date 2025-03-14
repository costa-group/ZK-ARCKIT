from typing import Tuple

import time
import json
import signal # NOTE: use of signal as a timeout handler requires unix
from contextlib import contextmanager
from typing import Dict

from r1cs_scripts.circuit_representation import Circuit

from comparison_testing import get_circuits

# from comparison.compare_circuits import circuit_equivalence
from comparison.constraint_preprocessing import constraint_classes
from bij_encodings.preprocessing.iterated_adj_reclassing import iterated_adjacency_reclassing

from comparison_v2.compare_circuits_v2 import circuit_equivalence

class TimeoutException(Exception): pass

@contextmanager
def time_limit(seconds):
    def signal_handler(signum, frame):
        raise TimeoutException(f"Timed Out after {seconds} seconds")
    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)

def exception_catcher(
    in_pair,
    info_preprocessing,
    cons_grouping,
    cons_preprocessing,
    encoder,
    test_data: Dict[str, any] = {},
    debug: bool = False,
    time_limit_seconds: int = 0, # 0 means no limit
    encoder_kwargs: dict = {},
    **kwargs
    ):   

    start = time.time()
    try:
        with time_limit(time_limit_seconds):
            circuit_equivalence(
                in_pair,
                info_preprocessing,
                cons_grouping,
                cons_preprocessing,
                encoder,
                test_data,
                debug,
                encoder_kwargs,
                **kwargs
            )
    except Exception as e:
        # print(e)
        test_data["result"] = "Error"
        test_data["result_explanation"] = repr(e)
        test_data["timing"]["error_time"] = time.time() - start

    return test_data
    

def run_affirmative_test(
        filename: str,
        out_filename: str,
        seed: int,
        info_preprocessing,
        cons_grouping,
        cons_preprocessing,
        encoder,
        debug: bool = False,
        time_limit: int = 0,
        encoder_kwargs: dict = {},
        **kwargs
    ):

    in_pair = get_circuits(filename, seed = seed, 
        const_factor=True, shuffle_sig=True, shuffle_const=True)

    test_data = {
        "test_type": "affirmative",
        "seed": seed
    }

    exception_catcher(
        in_pair,
        info_preprocessing,
        cons_grouping,
        cons_preprocessing,
        encoder,
        test_data,
        debug,
        time_limit,
        encoder_kwargs,
        **kwargs
    )

    # TODO: check result?

    f = open(out_filename, "w")
    json.dump(test_data, f, indent=4)
    f.close()

## current best imports

from r1cs_scripts.read_r1cs import parse_r1cs

from structural_analysis.clustering_methods.naive.degree_clustering import twice_average_degree
from structural_analysis.clustering_methods.naive.signal_equivalence_clustering import naive_removal_clustering
from bij_encodings.online_info_passing import OnlineInfoPassEncoder
from bij_encodings.reduced_encoding.red_class_encoder import reduced_encoding_class
from bij_encodings.reduced_encoding.red_pseudoboolean_encoding import pseudoboolean_signal_encoder

def quick_compare(
    lpair: Tuple[str, Circuit],
    rpair: Tuple[str, Circuit],
    time_limit_seconds: int = 0,
    debug: bool = False,
    **kwargs
) -> bool:
    try:
        with time_limit(time_limit_seconds):
            data = circuit_equivalence(
                [lpair, rpair],
                None,
                constraint_classes,
                iterated_adjacency_reclassing,
                OnlineInfoPassEncoder,
                encoder_kwargs= {
                    "class_encoding" : reduced_encoding_class,
                    "signal_encoding" : pseudoboolean_signal_encoder
                },
                debug=debug,
                **kwargs
            )
    except TimeoutException:
        return False
    return data["result"]
    

def run_current_best_test(
    lfilename: str,
    rfilename: str,
    outfile: str,
    time_limit: int = 0,
    debug: bool = True
    ):

    circ, circs = Circuit(), Circuit()

    parse_r1cs(lfilename, circ)
    parse_r1cs(rfilename, circs)

    in_pair = [("S1", circ), ("S2", circs)]

    test_data = exception_catcher(
        in_pair,
        None,
        constraint_classes,
        iterated_adjacency_reclassing,
        OnlineInfoPassEncoder,
        encoder_kwargs= {
            "class_encoding" : reduced_encoding_class,
            "signal_encoding" : pseudoboolean_signal_encoder
        },
        debug=debug,
        time_limit_seconds=time_limit
    )

    f = open(outfile, "w")
    json.dump(test_data, f, indent=4)
    f.close()
    