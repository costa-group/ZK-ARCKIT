
import json
import os
import itertools

from r1cs_scripts.read_r1cs import parse_r1cs
from r1cs_scripts.write_r1cs import write_r1cs
from r1cs_scripts.circuit_representation import Circuit

from structural_analysis.cluster_trees.dag_from_clusters import DAGNode

if __name__ == '__main__':
    ######################################################
    ### CAMBIA LO SEGUIDE PARA QUE HAGA LO QUE QUIERES ###
    ######################################################

    # the list of files and compilers -- invalid are skipped
    filenames = ["Poseidon", "Reveal", "Move", "Biomebase", "sha256_test512", "test_ecdsa", "circuit-1-2-1-8_"]
    compilers = ["O0", "O1"]

    testdir = "clustering_tests/picusbenchmarking"
    
    ##
    # looks for files of {testdir}/{filename}{compiler}_{clustering}_{equivalence}{suffixes} 
    ##
    # cambia lo de abajo si necesitas clustering/equivalence/suffixes differentes
    clustering = "louvain"
    equivalence = "structural"
    suffixes = "_maxequiv"

    ## Te dara en un archivo dentro de testdir que se llama r1cs
    #     dentro habra archivos con nombres que dentro tendran 0.r1cs, 0.sym, 1.r1cs, 1.sym, etc..
    #     cada uno es un cluster de cada classe de equivalence (estructural si puede)

    ######################################################
    ################## AQUI NO CAMBIAR ###################
    ######################################################

    dir_exists = os.path.exists(testdir + "/r1cs/")
    if not dir_exists: os.mkdir(testdir + "/r1cs/")
    for file, comp in itertools.product(filenames[:], compilers[:]):
        print(file, comp)

        r1cs = file + comp

        jsonfile = f"{testdir}/{r1cs}_{clustering}_{equivalence}{suffixes}.json"
        r1csfile = f"r1cs_files/{r1cs}.r1cs"
        output_directory = f"{testdir}/r1cs/{r1cs}_{clustering}_{equivalence}{suffixes}/"

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
        for class_ in jsondata["equivalence_local" if equivalence == 'local' else "equivalency_structural"]:
            id0 = class_[0]
            write_r1cs(subcircs[id0], output_directory + str(id0) + ".r1cs", sym=True)

        ## pass .r1cs files to picus and record result TODO