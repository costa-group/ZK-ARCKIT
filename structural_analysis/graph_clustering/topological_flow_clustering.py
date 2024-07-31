"""

We know that r1cs circuits have a sense of 'flow'. That is that from the inputs various constraints eventually 

    -- clustering in DAGs: https://www.emis.de/journals/AMEN/2021/AMEN-200819.pdf 
        -- the above is the same paper...

The above paper proposes a method for clustering a directed acyclic graph under a topological ordering (given by the graph).

It does this by calculting some best partitioning r_{k+1} for the set of ordered vertices x_{k+1}...x_n
    and then deiciding which of the [x_k, ..., x_k+i] + r_{k+i+1} partitions is best.

Some notes on the paper:

    the calculation at every step is really whether the delta Q is better if the 
    "next" went in it's own thing or went up to all the previous
    can we improve this?

    each include/exclude decision is purely made on a binary yes/no
        each include of a vertex u in the neighbourhood of i add 1/m
        each include of a vertex u adds [ out(i) * in(u) + in(i) * out(u) ] / m^2
            i.e. it's m > out(i) * in_sum(u) + in(i) * out_sum(u)
            otherwise its solo.

    so really we should be going forward with a memo array to vastly reduce calculation steps.
    
    However, after analysing the algorithm the clusters are order dependent:
        Consider a DAG rooted of two diamonds, the left of size 2, the right of size n. i.e
                           ------------   1 ----------------------
                         /           /               \ \ ... \ ... \
                        2           3                5 6 ... 5+i ... 5+n-1
                        \         /                   \ \    |      /
                            4                            5+n   5+n+1  

        With topological order 5+n+1 < 5+n < 4 < 3 < 5 < 6 < ... < 5+n-1 < 2 < 1
        note than when considered vertex 4 and 2 are in the same cluster then
        => m > out(4) * in_[sum u](u) + in(4) * out_[sum u](u) 
        => m > 2 * out_[sum u](u) 

        note that m = 3 * n + 4 and each 5,6...5+n-1 has out degree 2, and 3 has out degree 1

        => 3n + 4 > 2 * (2 * n + 1)
        => 3n + 4 > 4n + 2
        which is false for n >= 2, but for many other orderings (notably) 4, 3, 2 ... the 4 and 2 are in the same cluster.
        

This one deals with the order somewhat but at a skim read seems too slow 
    (essentially does the above and then loops over all clusters checking if merging improves value)

https://www.grad.hr/crocodays/proc_ccd2/antunovic_final.pdf


"""
from typing import Iterable, List


from r1cs_scripts.circuit_representation import Circuit

def constraint_dag(C: Circuit):
    """
    turns a circuit into a networkx directed acyclic graph

    NOTE:
        -- historical use of nx for this makes it really slow...
        -- can I do the calculations that avoid nx entirely
    """

def dag_community_detection(circ: Circuit, topological_order: List[int], in_neighbours: List[List[int]], out_neighbours: List[List[int]]):
    """
    Algorithm takes O(nm) time
    Algorithm (hopefully) takes O(n^2) memory
    """

    # initial labels for all constraints

    # coni_to_label[k][coni] = label of coni for optimal k
    coni_to_label = [[None for _ in range(circ.nConstraints)]]
    for i in range(len(topological_order)): coni_to_label[0][topological_order[i]] = i

    for coni in range(circ.nConstraints-1, -1, -1):
        pass

        # the calculation at every step is really whether the delta Q is better if the 
        #   "next" went in it's own thing or went up to all the previous
        #   can we improve this?

        # each include/exclude decision is purely made on a binary yes/no
            # each include of a vertex u in the neighbourhood of i add 1/m
            # each include of a vertex u adds [ out(i) * in(u) + in(i) * out(u) ] / m^2
                #i.e. it's m > out(i) * in_sum(u) + in(i) * out_sum(u)
                # otherwise its solo.
        
        # so really, we should do a memo array.
            # but clearly this is order dependent... so it doesn't matter.



