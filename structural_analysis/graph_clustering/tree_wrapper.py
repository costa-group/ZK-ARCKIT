import json
from typing import Callable, Tuple, List
import itertools
from functools import reduce

from r1cs_scripts.circuit_representation import Circuit
from utilities import _signal_data_from_cons_list, getvars, UnionFind
from structural_analysis.graph_clustering.signal_equivalence_clustering import naive_removal_clustering
from comparison.static_distance_preprocessing import _distances_to_signal_set

def O0_tree_clustering(
        circ: Circuit,
        outfile: str | None = None
    ) -> "Tree":
    """
    
    Json structure is to have smaller 'subcomponents' then putting them together into larger components
        Not sure how to do this in general? modularity maybe?
    
    """
    counter = 0

    inputs = list(range(circ.nPubOut+1, circ.nPubOut + circ.nPrvIn + circ.nPubIn + 1))
    # outputs = list(range(1,circ.nPubOut+1))

    signal_to_coni = _signal_data_from_cons_list(circ.constraints)
    distance_to_input = _distances_to_signal_set(circ.constraints, inputs, signal_to_coni)
    # distance_to_output = _distances_to_signal_set(circ.constraints, outputs, signal_to_coni)

    clusters, _, removed = naive_removal_clustering(circ)

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

    while len(removed) > 0:
        # idea is for each iteration to add another layer, final iteration will add 'root' layer which is then returned

        # Look at 'removed' constraints
        #   - if they have 1 adjacent cluster (including None) - they should be in that cluster
        #   - if they have no adjacent clusters (only None) - they should be ignored for this layer
        #   - if they have 2 adjacent clusters (non-None) - they should form a current layer cluster

        not_included = []
        parents = {}
        parents_uf= UnionFind()
        parent_key_to_removed = {}
        repr_to_children = {}

        # UNION FIND?

        for coni in removed:

            adjacent_repr = set(
                map(constraint_to_key.__getitem__, 
                    itertools.chain(*map(signal_to_coni.__getitem__, getvars(circ.constraints[coni]))))
            )

            if len(adjacent_repr) == 1:
                adjacent_cluster = next(iter(adjacent_repr))

                if adjacent_cluster is None:
                    not_included.append(coni)
                else:
                    ## add to that cluster
                    nodes[adjacent_cluster]["constraints"].append(coni)
                    # TODO: maybe update the signals?
            else:   
                parent_nodes = set(
                    map(parents_uf.find,
                    filter(lambda repr: repr is not None,
                    map(lambda repr: parents.setdefault(repr, None), 
                        filter(lambda repr : repr is not None, adjacent_repr)
                ))))

                match len(parent_nodes):
                    case 0: 
                        parent_key = counter
                        counter += 1
                        parent_key_to_removed[parent_key] = [coni]
                        
                    case 1:
                        parent_key = next(iter(parent_nodes))
                        parent_key_to_removed[parent_key].append(coni)
                    case _: 
                        parent_key = counter
                        counter += 1

                        # print(coni, adjacent_repr, parent_nodes, parents, parent_key_to_removed)

                        parent_key_to_removed[parent_key] = [coni]
                        parents_uf.union(parent_key, *parent_nodes)

                        # TODO: fix not updating old parent keys being updated ...
                        # for key in parent_nodes: del parent_key_to_removed[key] # Maybe don't bother with this?
                
                parents_uf.find(parent_key)
                for repr in filter(lambda repr : repr is not None, adjacent_repr): parents[repr] = parent_key
                repr_to_children.setdefault(parent_key, set([])).update(filter(lambda repr : repr is not None, adjacent_repr))

        unionfind_results = {}
        for key in parents_uf.parent.keys():
            unionfind_results.setdefault(parents_uf.find(key), []).extend(parent_key_to_removed[key])
        
        for key, cluster in unionfind_results.items():
            nodes[key] = make_node(key, cluster, subcomponents = list(map(nodes.__getitem__, repr_to_children[key])))

        removed = not_included

    if outfile is not None:
        f = open(outfile, "w")
        json.dump({key: nodes[key] for key in unionfind_results.keys()}, f, indent=4)
        f.close()
    else:
        return nodes

