if __name__ == '__main__':
    from r1cs_scripts.circuit_representation import Circuit
    from r1cs_scripts.read_r1cs import parse_r1cs
    from compare_circuits import get_classes
    from structural_analysis.signal_graph import *

    circ = Circuit()
    
    #filename = "SudokuO1.r1cs"
    filename = "Poseidon.r1cs"

    graph_gen = negone_to_signal
    
    parse_r1cs(filename, circ)
    groups = get_classes(circ, circ, [("S1", circ), ("S2", circ)])

    g = graph_gen(
        circ.constraints,
    )

    write_png(
        g,
        "structural_analysis/" + filename + ".png"
    )  