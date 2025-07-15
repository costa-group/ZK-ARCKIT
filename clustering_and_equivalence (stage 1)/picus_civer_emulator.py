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
import time

from circuits_and_constraints.r1cs.r1cs_circuit import R1CSCircuit
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
    newnode.constraints.extend(itertools.chain.from_iterable(map(lambda id: nodes[id].constraints, node.successors)))
    newnode.predecessors = list(set(itertools.chain.from_iterable([init_predecessors, itertools.chain.from_iterable(map(lambda id: nodes[id].predecessors, to_extend))])).difference(itertools.chain([node.id], to_extend)))
    newnode.successors = list(set(itertools.chain.from_iterable([init_successors, itertools.chain.from_iterable(map(lambda id: nodes[id].successors, to_extend))])).difference(itertools.chain([node.id], to_extend)))
    
    circ = newnode.circ
    newnode.input_signals.update(filter(
        lambda sig : circ.signal_is_input(sig) or any(map(lambda coni : coni_to_node[coni] in newnode.predecessors, sig_to_coni[sig])),
        itertools.chain.from_iterable(map(lambda id: nodes[id].input_signals, to_extend))
    ))
    newnode.output_signals.update(filter(
        lambda sig : circ.signal_is_output(sig) or any(map(lambda coni : coni_to_node[coni] in newnode.successors, sig_to_coni[sig])),
        itertools.chain.from_iterable(map(lambda id: nodes[id].output_signals, to_extend)
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
    r1cs.write_file("picus_emulator_temp.r1cs")
    output = subprocess.run([PICUS_DIR_LOCATION + "run-picus", "--timeout", str(timeout), "--solver", "z3", "--truncate", "off", "picus_emulator_temp.r1cs"], capture_output=True)

    nrounds = 0

    while output.returncode != PICUS_PROVEN_CODE and len(working_node.successors) > 0:
        working_node = extend_dagnode(working_node, nodes, sig_to_coni, coni_to_node)
        nrounds += 1

        r1cs = working_node.get_subcircuit()
        r1cs.write_file("picus_emulator_temp.r1cs")
        output = subprocess.run([PICUS_DIR_LOCATION + "run-picus", "--timeout", str(timeout), "--solver", "z3", "--truncate", "off", "picus_emulator_temp.r1cs"], capture_output=True)

    ## clean up and return
    subprocess.run(["rm", "picus_emulator_temp.r1cs"])
    return (output.returncode, nrounds)

def verify_node(
        node: DAGNode, 
        nodes: Dict[int, DAGNode], 
        sig_to_coni: List[List[int]], 
        coni_to_node: Dict[int, int],
        timeout: int):
    #TODO: pass number extension information, etc.

    working_node = node
    
    (returncode, downrounds) = verify_extending_downwards(working_node, nodes, sig_to_coni, coni_to_node, timeout)
    uprounds = 0

    while returncode != PICUS_PROVEN_CODE and len(working_node.predecessors) > 0:

        working_node = extend_dagnode(working_node, nodes, sig_to_coni, coni_to_node, extendup=True)
        uprounds += 1

        (returncode, more_downrounds) = verify_extending_downwards(working_node, nodes, sig_to_coni, coni_to_node, timeout)
        downrounds += more_downrounds

    return working_node, returncode, uprounds, downrounds

def picus_civer_emulator(
        nodes: Dict[int, DAGNode], 
        equivalence_local: List[List[int]] | None, 
        equivalence_structural: List[List[int]] | None,
        timeout : int = 5000
        ) -> Dict[str, int]:
    
    # TODO: handle not having one of the above

    ## Preprocessing
    node_to_local_class = {}
    node_to_structural_class = {}
    coni_to_node = {}

    deque(maxlen = 0, iterable = itertools.starmap(lambda i, x : node_to_local_class.__setitem__(x, i)     , itertools.chain.from_iterable(itertools.starmap(lambda i, class_ : itertools.product([i], class_), enumerate(equivalence_local)))))
    deque(maxlen = 0, iterable = itertools.starmap(lambda i, x : node_to_structural_class.__setitem__(x, i), itertools.chain.from_iterable(itertools.starmap(lambda i, class_ : itertools.product([i], class_), enumerate(equivalence_structural)))))
    deque(maxlen = 0, iterable = itertools.starmap(lambda i, x : coni_to_node.__setitem__(x, i)            , itertools.chain.from_iterable(itertools.starmap(lambda id, node  : itertools.product([id], node.constraints), nodes.items()))))
    sig_to_coni = _signal_data_from_cons_list(next(iter(nodes.values())).circ.constraints)

    ## Data to maintain
    aux_data = {
        type_: {"total_duration": 0, "total_child_depth": 0, "total_size": 0, "total_parent_depth": 0}
        for type_ in ["verified", "failed", "unknown", "verified_with_parent"]
    }

    # TODO: hacer esto de manera menos tonto.
    data = {
        "Number of equivalence classes": len(equivalence_structural),
        "Number of verified equivalence classes": 0,
        "Number of local equivalence classes verified": 0,
        "Total duration of l-verified equivalence classes": 0,
        "Total number of l-verified nodes": 0,
        "Maximum size of l-verified equivalence classes": 0,
        "Maximum duration of l-verified equivalence classes": 0,
        "Number of structural equivalence classes verified": 0,
        "Total duration of s-verified equivalence classes": 0,
        "Total number of s-verified nodes": 0,
        "Maximum size of s-verified equivalence classes": 0,
        "Maximum duration of s-verified equivalence classes": 0,
        "Number of total nodes": len(nodes),
        "Number of remaining nodes": 0,
        "Number of verified nodes": 0,
        "Mean duration of verified nodes": 0,
        "Mean rounds of verified nodes": 0,
        "Mean size of verified nodes": 0,
        "Mean number of predecessors of verified nodes": 0, # Given we're keeping them disjoint isn't this always 0?
        "Maximum size of verified nodes": 0,
        "Maximum duration of verified nodes": 0,
        "Maximum number of children verified nodes": 0,
        "Maximum number of predecessors of verified nodes": 0, # Given we're keeping them disjoint isn't this always 0?
        "Number of failed nodes": 0,
        "Mean duration of failed nodes": 0,
        "Mean rounds of failed nodes": 0,
        "Mean size of failed nodes": 0,
        "Mean number of predecessors of failed nodes": 0,
        "Maximum size of failed nodes": 0,
        "Maximum duration of failed nodes": 0,
        "Maximum number of children failed nodes": 0,
        "Maximum number of predecessors of failed nodes": 0,
        "Number of unknown nodes": 0,
        "Mean duration of unknown nodes": 0,
        "Mean rounds of unknown nodes": 0,
        "Mean size of unknown nodes": 0,
        "Mean number of predecessors of unknown nodes": 0,
        "Maximum size of unknown nodes": 0,
        "Maximum duration of unknown nodes": 0,
        "Maximum number of children unknown nodes": 0,
        "Maximum number of predecessors of unknown nodes": 0,
        "Number of verified nodes with parent": 0,
        "Mean duration of verified with parent nodes": 0,
        "Mean rounds of verified with parent nodes": 0,
        "Mean size of verified with parent nodes": 0,
        "Mean number of predecessors of verified with parent nodes": 0,
        "Maximum size of verified with parent nodes": 0,
        "Maximum duration of verified with parent nodes": 0,
        "Maximum number of children verified with parent nodes": 0,
        "Maximum number of predecessors of verified with parent nodes": 0
    }

    verified = {}
    for id, node in nodes.items():
        if verified.get(id, False): continue

        start = time.time()
        working_node, returncode, uprounds, downrounds = verify_node(node, nodes, sig_to_coni, coni_to_node, timeout)
        time_taken = time.time() - start

        if returncode == PICUS_PROVEN_CODE:
            
            if uprounds == 0 and downrounds == 0:
                ## Locally Equivalent Proven
                class_ = equivalence_local[node_to_local_class[id]]

                for node_id in class_: verified[node_id] = True
                data["Number of verified equivalence classes"] += 1
                data["Number of verified nodes"] += len(class_)
                data["Number of local equivalence classes verified"] += 1
                data["Total number of l-verified nodes"] += len(class_)
                data["Total duration of l-verified equivalence classes"] += time_taken
                data["Maximum size of l-verified equivalence classes"] = max(len(class_), data["Maximum size of l-verified equivalence classes"])
                data["Maximum duration of l-verified equivalence classes"] = max(time_taken, data["Maximum duration of l-verified equivalence classes"])
            
                data["Maximum size of verified nodes"] = max(len(working_node.constraints), data["Maximum size of verified nodes"])

                aux_data["verified"]["total_duration"] += time_taken * len(class_)
                aux_data["verified"]["total_size"] += len(working_node.constraints) * len(class_)

            elif uprounds == 0:
                ## Structurally Equivalent Proven
                class_ = equivalence_structural[node_to_structural_class[id]]

                for node_id in class_: verified[node_id] = True
                data["Number of verified equivalence classes"] += 1
                data["Number of verified nodes"] += len(class_)
                data["Number of structural equivalence classes verified"] += 1
                data["Total number of s-verified nodes"] += len(class_)
                data["Total duration of s-verified equivalence classes"] += time_taken
                data["Maximum size of s-verified equivalence classes"] = max(len(class_), data["Maximum size of s-verified equivalence classes"])
                data["Maximum duration of s-verified equivalence classes"] = max(time_taken, data["Maximum duration of s-verified equivalence classes"])
                
                data["Maximum size of verified nodes"] = max(len(working_node.constraints), data["Maximum size of verified nodes"])
                data["Maximum number of children verified nodes"] = max(downrounds, data["Maximum number of children verified nodes"])

                aux_data["verified"]["total_duration"] += time_taken * len(class_)
                aux_data["verified"]["total_child_depth"] += downrounds * len(class_)
                aux_data["verified"]["total_size"] += len(working_node.constraints) * len(class_)
            
            else:
                ## Just verified solo node:
                
                # data["Number of verified nodes"] += 1
                data["Number of verified nodes with parent"] += 1
                data["Maximum size of verified with parent nodes"] = max(len(working_node.constraints), data["Maximum size of verified with parent nodes"])
                data["Maximum duration of verified with parent nodes"] = max(time_taken, data["Maximum duration of verified with parent nodes"])
                data["Maximum number of children verified with parent nodes"] = max(downrounds, data["Maximum number of children verified with parent nodes"])
                data["Maximum number of predecessors of verified with parent nodes"] = max(uprounds, data["Maximum number of predecessors of verified with parent nodes"])

                aux_data["verified_with_parent"]["total_duration"] += time_taken * len(class_)
                aux_data["verified_with_parent"]["total_child_depth"] += downrounds * len(class_)
                aux_data["verified_with_parent"]["total_parent_depth"] += uprounds * len(class_)
                aux_data["verified_with_parent"]["total_size"] += len(working_node.constraints) * len(class_)
        
        elif returncode == PICUS_UNKNOWN_CODE:
            
            data["Number of unknown nodes"] += 1
            data["Maximum size of unknown nodes"] += max(len(working_node.constraints), data["Maximum size of unknown nodes"])
            data["Maximum duration of unknown nodes"] = max(time_taken, data["Maximum duration of unknown nodes"])

            data["Maximum number of children unknown nodes"] = max(downrounds, data["Maximum number of children unknown nodes"])
            data["Maximum number of predecessors of unknown nodes"] = max(uprounds, data["Maximum number of predecessors of unknown nodes"])

            aux_data["unknown"]["total_duration"] += time_taken * len(class_)
            aux_data["unknown"]["total_child_depth"] += downrounds * len(class_)
            aux_data["unknown"]["total_parent_depth"] += uprounds * len(class_)
            aux_data["unknown"]["total_size"] += len(working_node.constraints) * len(class_)

        else:
            raise ValueError(f"Unknown returncode: {returncode}")
    
    means = ["Mean duration of verified nodes", "Mean rounds of verified nodes", "Mean number of predecessors of verified nodes", "Mean size of verified nodes"]
    totals = itertools.product(["verified", "unknown", "failed", "verified_with_parent"], ["total_duration", "total_child_depth", "total_parent_depth", "total_size"])
    divisors = itertools.chain.from_iterable(map( lambda x : itertools.repeat(x, 4), ["Number of verified nodes", "Number of unknown nodes", "Number of verified nodes with parent", "Number of failed nodes"]))

    for lkey, (tkey, rkey), divisor in zip(means, totals, divisors):
        data[lkey] = None if data[divisor] == 0 else aux_data[tkey][rkey] / data[divisor]

    return data

def picus_civer_manager(r1csfile: str, jsonfile: str, outfile: str) -> None:

    fp = open(jsonfile, 'r')
    clustering = json.load(fp)
    fp.close()

    circ = R1CSCircuit()
    circ.parse_file(r1csfile)

    nodes = clustering["nodes"]

    def to_dagnode(node):
        dagnode = DAGNode(circ, node["node_id"], constraints=node["constraints"], input_signals=set(node["input_signals"]), output_signals=set(node["output_signals"]))
        dagnode.successors = node["successors"]
        dagnode.predecessors = []
        return dagnode

    dagnodes = list(map(to_dagnode, nodes))
    dagnodes = {node.id : node for node in dagnodes}

    for node in dagnodes.values():
        for oid in node.successors:
            dagnodes[oid].predecessors.append(node.id)

    if "equivalency_local" not in clustering.keys() or "equivalency_structural" not in clustering.keys():
        raise AssertionError("JSON must be a total clustering, try running clustering.py with the -e total flag")

    equivalence_local = clustering["equivalency_local"]
    equivalence_structural = clustering["equivalency_structural"]
    data = picus_civer_emulator(dagnodes, equivalence_local, equivalence_structural)

    fp = open(outfile, 'w')
    json.dump(data, fp, indent = 2)
    fp.close()
    
if __name__ == '__main__':
    import sys

    if len(sys.argv) != 4:
        raise SyntaxError("Callstyle is: python3 picus_civer_emulator.py <r1csfile> <jsonfile> <outfile>")
    
    picus_civer_manager(*sys.argv[1:])