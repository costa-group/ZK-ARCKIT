"""
Clustering based around the fact that almost always a template being called is connected via a single constraint-constraint edge.
"""

import networkx as nx
from typing import List
import itertools
from functools import reduce

from r1cs_scripts.constraint import Constraint
from structural_analysis.signal_graph import shared_constraint_graph
from structural_analysis.constraint_graph import shared_signal_graph, getvars
from normalisation import r1cs_norm

def is_signal_equivalence_constraint(con: Constraint) -> bool:
        return len(con.A) + len(con.B) == 0 and len(con.C) == 2 and sorted(r1cs_norm(con)[0].C.values()) == [1, con.p - 1]

def naive_all_removal(cons: List[Constraint]) -> nx.Graph:

    #TODO: why did this version not drop constraints?

    g = shared_signal_graph(cons)

    to_remove = [i for i, con in enumerate(cons) if is_signal_equivalence_constraint(con)]

    g.remove_nodes_from(to_remove)

    return list(nx.connected_components(g)) + [[i] for i in to_remove]

def naive_removal_clustering(cons: List[Constraint]) -> List[List[int]]:

    # going through nx is likely very expensive
    # surely there's some online dijkstra's we can do
    # TODO: look up when we have internet

    next = 0
    signal_to_cluster = {}
    clusters = {}
    removed_clusters = []

    for i, con in enumerate(cons):

        if is_signal_equivalence_constraint(con):
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
                
    clusters = list(clusters.values()) + removed_clusters

    return clusters 

