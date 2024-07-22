import time
import json

from comparison_testing import get_circuits

from comparison.compare_circuits import circuit_equivalence

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
        **encoder_kwargs
    ):

    circ, circs = get_circuits(filename, seed = seed, 
        const_factor=True, shuffle_sig=True, shuffle_const=True, 
        return_mapping=False, return_cmapping=False)

    start = time.time()
    try:
        test_data = circuit_equivalence(
            circ, circs,
            info_preprocessing,
            cons_clustering,
            cons_grouping,
            cons_preprocessing,
            encoder,
            debug = debug,
            **encoder_kwargs
        )
    except Exception as e:
        print(e)
        test_data = {
            "result": "Error",
            "result_explanation": repr(e),
            "timing": {"error_time": time.time() - start}
        }

    test_data["seed"] = seed
    test_data["test_type"] = "Affirmative"

    # TODO: check result?
    
    f = open(out_filename, "w")
    json.dump(test_data, f, indent=4)
    f.close()