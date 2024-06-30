if __name__ == '__main__':
    import networkx as nx
    from r1cs_scripts.circuit_representation import Circuit
    from r1cs_scripts.read_r1cs import parse_r1cs
    from comparison.compare_circuits import constraint_classes
    from structural_analysis.signal_graph import *
    from structural_analysis.constraint_graph import *
    from structural_analysis.graph_clustering.HCS_clustering import HCS
    from structural_analysis.graph_clustering.nx_clustering_builtins import *
    from structural_analysis.graph_clustering.stepped_girvan_newman import stepped_girvan_newman
    from structural_analysis.graph_clustering.signal_equivalence_clustering import naive_all_removal

    circ = Circuit()
    
    # filename = "r1cs_files/SudokuO1.r1cs"
    filename = "r1cs_files/PoseidonO0.r1cs"
    # filename = "r1cs_files/MultiAND.r1cs"
    modifiers = ["nar"]

    # graph_gen = abc_signal_graph    
    # graph_gen = negone_to_signal
    # graph_gen = shared_signal_graph
    graph_gen = naive_all_removal
    
    parse_r1cs(filename, circ)
    # groups = constraint_classes(circ, circ, [("S1", circ), ("S2", circ)])

    g = graph_gen(
        circ.constraints,
    )

    # g = induce_on_partitions(g, stepped_girvan_newman(g))

    nx.nx_pydot.to_pydot(g).write_png(
        "structural_analysis" + filename[filename.index('/'):] + "_" * (len(modifiers) > 0) + "_".join(modifiers) +  ".png"
    )  