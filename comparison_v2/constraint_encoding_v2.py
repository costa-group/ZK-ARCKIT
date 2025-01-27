## ABANDONDED FOR NOW DUE TO POR BENCHMARKING ON PREVIOUS

##
    ## we have constraint classes and signal classes
    ## 

        ## when we go to encode we do it by constraint class
        ## constraint classes with length > 1 are encoded
        ##  use singular_options_v2 to further restrict signal mappings for > 1
        ##  then to signal_bijection on signals classes of length > 1

from pysat.formula import CNF

def encode_classes_v2(
        names,
        in_pair,
        normalised_constraints,
        fingerprint_to_normi,
        fingerprint_to_signals
    ):
    pass

    # encode classes

    formula = CNF()

    classes_to_encode = sorted(filter(lambda key : len(fingerprint_to_signals[names[0]][key]) > 1, fingerprint_to_signals[names[0]].keys()), key = lambda k : len(fingerprint_to_signals[names[0]][k]))

    for key in classes_to_encode:

        ## the logic is as follows:
            # we know already by the fingerprints the class of the encoding for the signals... 
        # formula.extend(encode_class)
        pass