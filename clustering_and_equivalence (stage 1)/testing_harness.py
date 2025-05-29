from typing import Tuple

import time
import json
import signal # NOTE: use of signal as a timeout handler requires unix
from contextlib import contextmanager
from typing import Dict

from r1cs_scripts.circuit_representation import Circuit

from circuit_shuffle import get_circuits
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
    test_data: Dict[str, any] = {},
    debug: bool = False,
    time_limit_seconds: int = 0, # 0 means no limit
    **kwargs
    ):   

    start = time.time()
    try:
        with time_limit(time_limit_seconds):
            circuit_equivalence(
                in_pair,
                test_data,
                debug=debug,
                **kwargs
            )
    except Exception as e:
        # print(e)
        test_data["result"] = False
        test_data["result_explanation"] = repr(e)
        test_data["timing"]["error_time"] = time.time() - start

    return test_data
    

def run_affirmative_test(
        filename: str,
        out_filename: str,
        seed: int,
        debug: bool = False,
        time_limit: int = 0,
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
        test_data,
        debug,
        time_limit,
        **kwargs
    )

    # TODO: check result?

    f = open(out_filename, "w")
    json.dump(test_data, f, indent=4)
    f.close()

## current best imports

from r1cs_scripts.read_r1cs import parse_r1cs

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
        debug=debug,
        time_limit_seconds=time_limit
    )

    f = open(outfile, "w")
    json.dump(test_data, f, indent=4)
    f.close()
    