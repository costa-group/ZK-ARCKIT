import itertools

from utilities.utilities import _signal_data_from_cons_list, getvars
from r1cs_scripts.circuit_representation import Circuit
from deprecated.cluster_trees.r1cs_O0_rooting import TreeNode


def node_signals(circ: Circuit, R: TreeNode):

    signal_to_coni = _signal_data_from_cons_list(circ.constraints)
    inputs = list(range(circ.nPubOut+1, circ.nPubOut + circ.nPrvIn + circ.nPubIn + 1))

    stack = [R]
    seen = {sig: True for sig in inputs}

    while len(stack) > 0:
        node = stack.pop()

        node.signals = set(itertools.chain(*map(getvars, map(circ.constraints.__getitem__, node.constraints))))
        node.proven_external_signals = list(filter(lambda sig : seen.setdefault(sig, False), node.signals))
        for sig in node.signals : seen[sig] = True
        stack.extend(node.children)

    stack = [R]
    while len(stack) > 0:

        node = stack.pop()

        for child in node.children:
            req_for_child = child.proven_external_signals

            # recursive ?
            res_from_chil = set(child.signals).difference(child.proven_external_signals).intersection(node.signals)

            node.unproven_external_signals.append((
                req_for_child,
                list(res_from_chil)
            ))

        node.unproven_external_signals.append(list(filter(lambda sig : sig <= circ.nPubOut, node.signals)))
        stack.extend(node.children)    
    
    return R

