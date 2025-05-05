# Clustering and Equivalence

This section of the repository handles the clustering and equivalence of R1CS Circuits. The codebase can be broadly divided into handling one of the sections. The filesystem structure is depicted below, each of the first three directories is for a dedicated subsection with the latter two having broad utility across the codebase. 
```bash      
├───comparison_v2
├───maximal_equivalence
│   └───subclassing
├───structural_analysis
│   ├───clustering_methods
│   │   ├───naive
│   │   └───networkx
│   ├───cluster_trees
│   └───utilities
├───r1cs_scripts
└───utilities
```

## Equivalence

The main file is `comparison_v2`, it contains the method `circuit_equivalence` which takes in two circuits and determines whether or not they are equivalent up to renaming, scaling, and shuffling. The process involves three steps; normalisation - here we calculate the norms of the constraints so that they can be compared directly despite scaling, fingerprinting - here we use internal and structural information to build classes of potential pairings prior to encoding, SAT encoding - here we encode each equivalence rule for each class.

### Normalisation

`normalisation.py` in the top-level directory handles the process of normalisation. We calculate, for each constraint, some number of normalised constraints. For almost all constraints this number is 1, for constraints that have linear parts that are exactly a constant multiple of the set of $n$-th roots of unity $\bmod p$ for the large prime $p$ then there are $n$ constraints. 

### Fingerprinting

`comparison_v2/fingerprinting_v2.py` defines the methods for fingerprinting. The methods themselves become quite complicated due to various optimisations but the broad idea is rather straightforward. 

Equivalent normalised constraint must have the same coefficient multisets in each part - this defines an initial fingerprint. With this we can then build classes for signals based on having a non-zero characteristic (i.e. coefficient tuple) with a norm of class $i$. With this we can then go back to the norms and update the fingerprints so the multiset of coefficients taking into account signal classes must be the same.

In this way we iteratively improve the initial fingerprints to encode structural information and vastly reduce the number of comparisons that are viable and thus need to be encoded into SAT. Current methods give, for tested circuits, an almost perfect encoding of the norms into classes (i.e. almost every class has just 1 element).

### SAT Encoding

`comparison_v2/constraint_encoding_v2.py` contains the methods for encoding to SAT. We encode the following constraints:
- For each constraint in the 'left' circuit in a class:
    - It is mapped to at least one constraint in the 'right' circuit for that class
    - If it is mapped to a constraint in the right circuit:
        - Each signal in the 'left' constraint is mapped to at least one viable signal in the 'right' constraint and vice versa
- For each signal in the left circuit in the class, we ensure it is mapped to exactly one signal on the right, and vice versa.
Hence a satisfying assignment is a bijection between the signals of the circuits, and a mapping of left to right for the normalised constraints. It can be shown that this is equivalent to a bijection between the constraints if the circuits internally contains no equivalent constraint (which is assumed).

## Maximal Equivalence

## Clustering