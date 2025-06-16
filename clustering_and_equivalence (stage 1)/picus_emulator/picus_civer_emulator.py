## NEED: 
#  main file
#  picus output parser
#  dagnode merger


## STEPS
# Per class
#   call picus w/ some timeout
#       if pass -> mark all local class and continue
#       otherwise extend a layer of children repeat until pass or no more children -- early exit process on timeout
#           if pass -> mark all structural class and continue
#   if we can't solve with this then we add the parent nodes and repeat the above process
#       -> at this point we only mark the individual node

from typing import Dict, List
import json
import subprocess
from collections import deque
import itertools

from r1cs_scripts.write_r1cs import write_r1cs
from structural_analysis.cluster_trees.dag_from_clusters import DAGNode
from utilities.utilities import _signal_data_from_cons_list

PICUS_DIR_LOCATION = "../../Picus/"

PICUS_PROVEN_MSG  = "The circuit is properly constrained"
PICUS_UNKNOWN_MSG = "Cannot determine whether the circuit is properly constrained"

PICUS_PROVEN_CODE = 8
PICUS_UNKNOWN_CODE = 0

def extend_dagnode(node: DAGNode, nodes: Dict[int, DAGNode], sig_to_coni: List[List[int]], coni_to_node: Dict[int, int], extendup: bool = False) -> DAGNode:
    to_extend = node.predecessors if extendup else node.successors
    init_predecessors = [] if extendup else node.predecessors
    init_successors = node.successors if extendup else []
    init_input_signals = set([]) if extendup else set(node.input_signals)
    init_output_signals = set(node.output_signals) if extendup else set([])

    newnode = DAGNode(node.circ, node.id, node.constraints.copy(), init_input_signals, init_output_signals)
    newnode.constraints.extend(itertools.chain(*map(lambda id: nodes[id].constraints, node.successors)))
    newnode.predecessors = list(set(itertools.chain(init_predecessors, *map(lambda id: nodes[id].predecessors, to_extend))).difference([node.id] + to_extend))
    newnode.successors = list(set(itertools.chain(init_successors, *map(lambda id: nodes[id].successors, to_extend))).difference([node.id] + to_extend))
    
    circ = newnode.circ
    newnode.input_signals.update(filter(
        lambda sig : circ.nPubOut < sig <= circ.nPubOut + circ.nPrvIn + circ.nPubIn or any(map(lambda coni : coni_to_node[coni] in newnode.predecessors, sig_to_coni[sig])),
        itertools.chain(*map(lambda id: nodes[id].input_signals, to_extend))
    ))
    newnode.output_signals.update(filter(
        lambda sig : 0 < sig <= circ.nPubOut or any(map(lambda coni : coni_to_node[coni] in newnode.successors, sig_to_coni[sig])),
        itertools.chain(*map(lambda id: nodes[id].output_signals, to_extend)
    )))

    return newnode

def verify_extending_downwards(
        node: DAGNode, 
        nodes: Dict[int, DAGNode], 
        sig_to_coni: List[List[int]], 
        coni_to_node: Dict[int, int],
        timeout: int) -> int:
    
    working_node = node

    r1cs = working_node.get_subcircuit()
    write_r1cs(r1cs, "picus_emulator_temp.r1cs")
    output = subprocess.run([PICUS_DIR_LOCATION + "run-picus", "--timeout", str(timeout), "--solver", "z3", "--truncate", "off", "picus_emulator_temp.r1cs"], capture_output=True)

    while output.returncode != PICUS_PROVEN_CODE and len(working_node.successors) > 0:
        working_node = extend_dagnode(working_node, nodes, sig_to_coni, coni_to_node)

        r1cs = working_node.get_subcircuit()
        write_r1cs(r1cs, "picus_emulator_temp.r1cs")
        output = subprocess.run([PICUS_DIR_LOCATION + "run-picus", "--timeout", str(timeout), "--solver", "z3", "--truncate", "off", "picus_emulator_temp.r1cs"], capture_output=True)

    ## clean up and return
    subprocess.run(["rm", "picus_emulator_temp.r1cs"])
    return output.returncode

def verify_node(
        node: DAGNode, 
        nodes: Dict[int, DAGNode], 
        sig_to_coni: List[List[int]], 
        coni_to_node: Dict[int, int],
        timeout: int):
    #TODO: pass number extension information, etc.

    working_node = node
    
    returncode = verify_extending_downwards(working_node, nodes, sig_to_coni, coni_to_node, timeout)

    while returncode != PICUS_PROVEN_CODE and len(working_node.predecessors) > 0:

        working_node = extend_dagnode(working_node, nodes, sig_to_coni, coni_to_node, extendup=True)
        returncode = verify_extending_downwards(working_node, nodes, sig_to_coni, coni_to_node, timeout)

    return working_node

def picus_civer_emulator(
        nodes: Dict[int, DAGNode], 
        equivalence_local: List[List[int]] | None, 
        equivalence_structural: List[List[int]] | None,
        timeout : int = 5000
        ) -> Dict[str, int]:
    # TODO: handle not having one of the above
    circ = next(iter(nodes.values())).circ

    node_to_local_class = {}
    node_to_structural_class = {}
    coni_to_node = {}

    deque(maxlen = 0, iterable = itertools.starmap(lambda i, x : node_to_local_class.__setitem__(x, i), itertools.chain(*itertools.starmap(lambda i, class_ : itertools.product([i], class_), enumerate(equivalence_local)))))
    deque(maxlen = 0, iterable = itertools.starmap(lambda i, x : node_to_structural_class.__setitem__(x, i), itertools.chain(*itertools.starmap(lambda i, class_ : itertools.product([i], class_), enumerate(equivalence_structural)))))
    deque(maxlen = 0, iterable = itertools.starmap(lambda i, x : coni_to_node.__setitem__(x, i), itertools.chain(*itertools.starmap(lambda id, node : itertools.product([id], node.constraints), nodes.items()))))

    sig_to_coni = _signal_data_from_cons_list(circ.constraints)
    
    # nodeid = next(iter(nodes.keys()))
    # verify_node(nodes[nodeid], nodes, sig_to_coni, coni_to_node, timeout)