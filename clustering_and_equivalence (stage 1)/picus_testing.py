
import json
import os
import itertools

from r1cs_scripts.read_r1cs import parse_r1cs
from r1cs_scripts.write_r1cs import write_r1cs
from r1cs_scripts.circuit_representation import Circuit

from structural_analysis.cluster_trees.dag_from_clusters import DAGNode

if __name__ == '__main__':
    filenames = ["Poseidon", "Reveal", "Move", "Biomebase", "sha256_test512", "test_ecdsa", "circuit-1-2-1-8_"]
    compilers = ["O0", "O1"]

    ## get json files and load .r1cs
    r1cs = "RevealO0"
    
    clustering = "louvain"
    equivalence = "structural"
    suffixes = "_maxequiv"

    testdir = "picusbenchmarking"

    for file, comp in itertools.product(filenames[:], compilers[:]):
        print(file, comp)

        r1cs = file + comp

        jsonfile = f"clustering_tests/{testdir}/{r1cs}_{clustering}_{equivalence}{suffixes}.json"
        r1csfile = f"r1cs_files/{r1cs}.r1cs"
        output_directory = f"clustering_tests/{testdir}/r1cs/{r1cs}_{clustering}_{equivalence}{suffixes}/"

        try:
            circ = Circuit()
            parse_r1cs(r1csfile, circ)

            fp = open(jsonfile, 'r')
            jsondata = json.load(fp)
            fp.close()
        except FileNotFoundError:
            continue

        ## convert json files to Circuit

        nodes = jsondata["nodes"]

        dagnodes = []
        for node in nodes:
            dagnode = DAGNode(circ, node["node_id"], node["constraints"], set(node["input_signals"]), set(node["output_signals"]))
            dagnode.successors = node["successors"]
            dagnodes.append(dagnode)

        subcircs = { dagnode.id : dagnode.get_subcircuit() for dagnode in dagnodes}

        ## Circuit to .r1cs files
        dir_exists = os.path.exists(output_directory)
        if not dir_exists: os.mkdir(output_directory)
        for class_ in jsondata[f"equivalency_{equivalence}"]:
            id0 = class_[0]
            write_r1cs(subcircs[id0], output_directory + str(id0) + ".r1cs", sym=True)

        ## pass .r1cs files to picus and record result TODO