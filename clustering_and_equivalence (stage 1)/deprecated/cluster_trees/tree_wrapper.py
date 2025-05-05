import json
from typing import Callable, Tuple, List
import itertools
from functools import reduce

from r1cs_scripts.circuit_representation import Circuit
from utilities.utilities import _signal_data_from_cons_list, getvars, UnionFind
from structural_analysis.clustering_methods.naive.signal_equivalence_clustering import naive_removal_clustering
from structural_analysis.clustering_methods.linear_coefficient import cluster_by_linear_coefficient
from deprecated.comparison.static_distance_preprocessing import _distances_to_signal_set

"""
DEPRECATED
"""

def O0_tree_clustering(
        circ: Circuit,
        clustering_method = cluster_by_linear_coefficient,
        outfile: str | None = None
    ) -> "Tree":
    """
    
    Json structure is to have smaller 'subcomponents' then putting them together into larger components
        Not sure how to do this in general? modularity maybe?
    
    """
    # TODO: fix public outputs not being placed correctly.
    counter = 0

    inputs = list(range(circ.nPubOut+1, circ.nPubOut + circ.nPrvIn + circ.nPubIn + 1))
    # outputs = list(range(1,circ.nPubOut+1))

    signal_to_coni = _signal_data_from_cons_list(circ.constraints)
    distance_to_input = _distances_to_signal_set(circ.constraints, inputs, signal_to_coni)
    # distance_to_output = _distances_to_signal_set(circ.constraints, outputs, signal_to_coni)

    clusters, _, removed = clustering_method(circ, calculate_adjacency=False)

    def make_node(key, cluster, subcomponents: List[dict] = []):

        # TODO: update external signal calc
        node = {
            "constraints": cluster,
            "node_id": key,
            "inputs": [],
            "outputs": [],
            "signals": list(reduce( # might be too slow -- do we want to exclude internal constraints?
                lambda acc, coni: acc.union(getvars(circ.constraints[coni])),
                cluster,
                set([])
            )),
            "subcomponents": subcomponents
        }

        # determine internal/external signals
        #   look at signal_to_coni and check for non_included constraints

        # TODO: check efficiency... maybe have some hidden variables?
        # TODO:     change to have some global array with - for each constraints - it's current (latest) layer repr
        #           can maybe replace coni_to_key thing -- makes this whole thing much faster
        def get_internal_constraints(node: dict) -> List[int]:
            return list(itertools.chain(node["constraints"], *map(get_internal_constraints, node["subcomponents"])))

        all_internal_constraints = get_internal_constraints(node)

        external_signals = [sig for sig in node["signals"]
            # likely faster option than this -- TODO
            if sig <= circ.nPubOut + circ.nPubIn + circ.nPrvIn or 
            len([coni for coni in signal_to_coni[sig] if coni not in all_internal_constraints]) > 0]
        
        # determing input/output signals?
        #   look at distance to circuit inputs/ distance to circuit outputs?
        #   still seems like we'll need to make some arbitrary decision...

        # for now just have minimum distance being inpu
        if external_signals != []:
            min_dist = min(map(distance_to_input.__getitem__, external_signals))
            for sig in external_signals: (node["inputs"] if distance_to_input[sig] == min_dist else node["outputs"]).append(sig)
        
        return node

    nodes = {}

    # seems the output JSON requires a tree not a DAG, so I'm gonna included the removed constraints into their parent nodes
    constraint_to_key = [None for _ in range(circ.nConstraints)]

    for cluster in clusters.values():

        for coni in cluster: constraint_to_key[coni] = counter
        nodes[counter] = make_node(counter, cluster)
        counter += 1

    # in --O0 we can try do more components based on 'removed' signals that don't have adjacencies to any others

    # IDEA: shift to pipe system instead of layers ... ?
        # super-components are arbitrarily defined on a layer-by-layer basis though...

    coni_to_adjacent_repr = lambda coni : set(
        map(constraint_to_key.__getitem__, 
        filter(lambda oconi : oconi != coni, 
            itertools.chain(*map(signal_to_coni.__getitem__, getvars(circ.constraints[coni]))))
        )
    )

    # TODO: need to have parent defined recursively and persistently
    parents_uf = UnionFind(representative_tracking=True)

    while len(removed) > 0: 
        
        # TODO: misses edges between nodes of the same layer.
        #   -- can merge nodes after keys are registered?
        #       -- could also move one down a layer (i.e. make one a subcomponent of the other) - seems a bit arbitrary - distance?
        #       -- good questions..
        #   -- as in, if a constraint links two clusters of the current layer, we wait until the higher to bridge, but this seems fine
        #       -- If we don't separate by layer then we can theoretically just call all removed a single cluster.

        # idea is for each iteration to add another layer, final iteration will add 'root' layer which is then returned

        # Look at 'removed' constraints
        #   - if they have no adjacent clusters (only None) - they should be ignored for this layer
        #   - if they have 2 adjacent clusters (non-None) - they should form a current layer cluster

        not_included = []
        parent_key_to_removed = {}  # this should be fine to reset, since it's only used in node creation
        repr_to_children = {}       #  ^^

        # TODO: look into linear clustering not providing a proper hierarchy
        #   I think this could happen with the other clustering (and might've with reveal)
        #   but I just didn't notice until now -- discuss how to deal with this

        for coni in removed:

            adjacent_repr = coni_to_adjacent_repr(coni)

            if len(adjacent_repr) == 1 and next(iter(adjacent_repr)) == None:
                not_included.append(coni)
            else:
                # TODO: how to detect new layer though --?
                parent_nodes = set(
                    map(parents_uf.find,
                    filter(lambda repr : repr is not None, adjacent_repr)
                ))

                if len(parent_nodes) == 0 and next(iter(parent_nodes)) in parent_key_to_removed.keys():
                    parent_key = next(iter(parent_nodes))
                    parent_key_to_removed[parent_key].append(coni)
                else:
                    parent_key = counter
                    counter += 1

                    parent_key_to_removed[parent_key] = [coni]
                    parents_uf.union(parent_key, *parent_nodes)

                repr_to_children.setdefault(parent_key, set([])).update(filter(lambda repr : repr is not None, adjacent_repr))

        unionfind_results = {}
        for key in parent_key_to_removed.keys():
            unionfind_results.setdefault(parents_uf.find(key), []).extend(parent_key_to_removed[key])

        for key, cluster in unionfind_results.items():
            nodes[key] = make_node(key, cluster, subcomponents = list(map(nodes.__getitem__, repr_to_children[key]))) #TODO: KeyError
            for coni in cluster: constraint_to_key[coni] = key
        
        removed = not_included

    print("\n")
    print(nodes.keys())
    print({key: nodes[key]["constraints"] for key in nodes.keys()})
    
    print(len(parents_uf.get_representatives()))
    from utilities.utilities import count_ints
    print(count_ints(map(len, [node["subcomponents"] for node in nodes.values()])))

    if outfile is not None:
        f = open(outfile, "w")
        json.dump({key: nodes[key] for key in parents_uf.get_representatives()}, f, indent=4)
        f.close()
    else:
        return nodes

