if __name__ == '__main__':
    import networkx as nx
    from r1cs_scripts.circuit_representation import Circuit
    from r1cs_scripts.read_r1cs import parse_r1cs
    from comparison.compare_circuits import get_classes
    from structural_analysis.signal_graph import *
    from structural_analysis.constraint_graph import *
    from structural_analysis.graph_clustering.HCS_clustering import HCS
    from structural_analysis.graph_clustering.nx_clustering_builtins import *

    circ = Circuit()
    
    filename = "r1cs_files/SudokuO1.r1cs"
    # filename = "r1cs_files/Poseidon.r1cs"
    # filename = "r1cs_files/MultiAND.r1cs"
    modifiers = ["clustering"]

    # graph_gen = abc_signal_graph    
    # graph_gen = negone_to_signal
    graph_gen = shared_signal_graph
    
    parse_r1cs(filename, circ)
    groups = get_classes(circ, circ, [("S1", circ), ("S2", circ)])

    g = graph_gen(
        circ.constraints,
    )

    g = Louvain(g)

    nx.nx_pydot.to_pydot(g).write_png(
        "structural_analysis" + filename[filename.index('/'):] + "_" * (len(modifiers) > 0) + "_".join(modifiers) +  ".png"
    )  