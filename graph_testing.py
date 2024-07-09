if __name__ == '__main__':
    import networkx as nx
    from functools import reduce
    from r1cs_scripts.circuit_representation import Circuit
    from r1cs_scripts.read_r1cs import parse_r1cs
    from comparison.compare_circuits import constraint_classes
    from structural_analysis.signal_graph import *
    from structural_analysis.constraint_graph import *
    from structural_analysis.graph_clustering.HCS_clustering import HCS
    from structural_analysis.graph_clustering.nx_clustering_builtins import *
    from structural_analysis.graph_clustering.stepped_girvan_newman import stepped_girvan_newman
    from structural_analysis.graph_clustering.signal_equivalence_clustering import naive_removal_clustering
    from structural_analysis.graph_clustering.degree_clustering import twice_average_degree, ratio_of_signals

    circ = Circuit()
    
    # filename = "r1cs_files/SudokuO1.r1cs"
    filename = "r1cs_files/PoseidonO1.r1cs"
    # filename = "r1cs_files/MultiAND.r1cs"
    modifiers = ["signal_twice"]

    parse_r1cs(filename, circ)

    clusters = twice_average_degree(circ.constraints)

    g = shared_constraint_graph(list(map(
        lambda i : circ.constraints[i],
        reduce(
        lambda acc, x : acc + x,
        filter(lambda l : len(l) > 1, clusters),
        []
    ))))

    nx.nx_pydot.to_pydot(g).write_png(
        "structural_analysis" + filename[filename.index('/'):] + "_" * (len(modifiers) > 0) + "_".join(modifiers) +  ".png"
    )  