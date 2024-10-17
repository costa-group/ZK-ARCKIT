import itertools

from utilities import _signal_data_from_cons_list, getvars
from r1cs_scripts.circuit_representation import Circuit
from structural_analysis.cluster_trees.r1cs_O0_rooting import TreeNode


def node_signals(circ: Circuit, R: TreeNode):

    signal_to_coni = _signal_data_from_cons_list(circ.constraints)
    inputs = list(range(circ.nPubOut+1, circ.nPubOut + circ.nPrvIn + circ.nPubIn + 1))

    stack = [R]
    seen = {sig: True for sig in inputs}

    while len(stack) > 0:
        node = stack.pop()

        # a signal is external if it appears only once in amongst the listed constraints of the subcomponents
        #   only true if every subcomponent passoff has an x = ... constraint
        #   results in a lot of leaf subcomponents having only input signals, (doesn't make sense for input signals to be external)
        # instead should be, appears in constraint not in node

        signals = set(itertools.chain(*map(getvars, map(circ.constraints.__getitem__, node.constraints))))

        node.proven_external_signals = list(filter(lambda sig : seen.setdefault(sig, False), signals))
        node.unproven_external_signals = list(filter(
            lambda sig : not seen[sig] and len(set(signal_to_coni[sig]).difference(node.constraints)) > 0,
            signals
        ))

        for sig in node.unproven_external_signals: seen[sig] = True

        # external_signals = filter(
        #     lambda sig : sum(map(lambda coni: coni in node.constraints, signal_to_coni[sig])) == 1,
            
        # )

        # for sig in external_signals:
        #     if seen.setdefault(sig, False): 
        #         node.proven_external_signals.append(sig)
        #     else: 
        #         seen[sig] = True
        #         node.unproven_external_signals.append(sig)
        
        stack.extend(node.children)
    
    return R

