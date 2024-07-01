
from typing import List, Tuple, Dict, Callable
from functools import reduce

from r1cs_scripts.constraint import Constraint


def getvars(con) -> set:
    return set(con.A.keys()).union(con.B.keys()).union(con.C.keys()).difference(set([0]))

def cluster_from_list(cons: List[Constraint], to_ignore: List[int] = None, ignore_func: Callable[[Constraint], bool] = None) -> List[List[int]]:

    assert to_ignore is not None or ignore_func is not None, "no removal method given"
    use_function = ignore_func is not None

    # going through nx is likely very expensive
    # surely there's some online dijkstra's we can do
    # TODO: look up when we have internet

    next = 0
    signal_to_cluster = {}
    clusters = {}
    removed_clusters = []

    for i, con in enumerate(cons):

        if (use_function and ignore_func(con)) or (i in to_ignore):
            removed_clusters.append([i])
            continue

        member_of_clusters = set([])

        for signal in getvars(con):
            if signal_to_cluster.setdefault(signal, None) is not None:
                member_of_clusters.add( signal_to_cluster[signal] )

        if len(member_of_clusters) == 0:

            member_of_clusters.add(next)
            clusters[next] = []
            next += 1
        
        member_of_clusters = list(member_of_clusters)
        
        if len(member_of_clusters) == 1:
            
            cluster = member_of_clusters[0]
            clusters[cluster].append(i)

            for signal in getvars(con):
                signal_to_cluster[signal] = cluster
        
        elif len(member_of_clusters) > 1:
            
            # merge all clusters in member_of_clusters into new cluster
            cluster = member_of_clusters[0]

            clusters[cluster] = reduce(lambda acc, x : acc + x, 
                                       map(lambda ind : clusters[ind], member_of_clusters[1:]), 
                                       clusters[cluster])
            
            clusters[cluster].append(i)

            for ind in member_of_clusters[1:]:
                del clusters[ind]

            # change all signals associated with cluster
            for ind in clusters[cluster]:
                con_ = cons[ind]
                for signal in getvars(con_):
                    signal_to_cluster[signal] = cluster
                
    return list(clusters.values()) + removed_clusters