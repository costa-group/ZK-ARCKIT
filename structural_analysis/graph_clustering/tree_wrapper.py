import json
from typing import Callable, Tuple
import itertools
from functools import reduce

from r1cs_scripts.circuit_representation import Circuit
from utilities import _signal_data_from_cons_list, getvars
from structural_analysis.graph_clustering.signal_equivalence_clustering import naive_removal_clustering
from comparison.static_distance_preprocessing import _distances_to_signal_set

def tree_clustering(
        circ: Circuit,
        clustering_method: Callable[[Circuit], Tuple["Clusters", "Adjacency", "Removed"]] = naive_removal_clustering,
        outfile: str | None = None
    ) -> "Tree":
    """
    
    Json structure is to have smaller 'subcomponents' then putting them together into larger components
        Not sure how to do this in general? modularity maybe?
    
    """

    inputs = list(range(circ.nPubOut+1, circ.nPubOut + circ.nPrvIn + circ.nPubIn + 1))
    # outputs = list(range(1,circ.nPubOut+1))

    signal_to_coni = _signal_data_from_cons_list(circ.constraints)
    distance_to_input = _distances_to_signal_set(circ.constraints, inputs, signal_to_coni)
    # distance_to_output = _distances_to_signal_set(circ.constraints, outputs, signal_to_coni)

    clusters, adjacency, removed = clustering_method(circ)

    nodes = []

    # seems the output JSON requires a tree not a DAG, so I'm gonna included the removed constraints into their parent nodes

    for key, cluster in clusters.items():

        node = {
            "constraints": cluster,
            "node_id": key,
            "inputs": [],
            "outputs": [],
            "signals": list(reduce(
                lambda acc, coni: acc.union(getvars(circ.constraints[coni])),
                cluster,
                set([])
            )),
            "subcomponents": []
        }

        # determine internal/external signals
        #   look at signal_to_coni and check for non_included constraints

        external_signals = [sig for sig in node["signals"]
            # likely faster option than this -- TODO
            if len([coni for coni in signal_to_coni[sig] if coni not in cluster]) > 0]

        # determing input/output signals?
        #   look at distance to circuit inputs/ distance to circuit outputs?
        #   still seems like we'll need to make some arbitrary decision...

        # for now just have minimum distance being input
        min_dist = min(map(distance_to_input.__getitem__, external_signals))
        for sig in external_signals: (node["inputs"] if distance_to_input[sig] == min_dist else node["outputs"]).append(sig)

        nodes.append(node)

    # in --O0 we can try do more components based on 'removed' signals that don't have adjacencies to any others

    # while len(removed) > 0:
        # idea is for each iteration to add another layer, final iteration will add 'root' layer which is then returned

    if outfile is not None:
        f = open(outfile, "w")
        json.dump(nodes, f, indent=4)
        f.close()
    else:
        return nodes

