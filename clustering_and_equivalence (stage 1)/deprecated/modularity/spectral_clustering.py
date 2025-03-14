"""
Maybe try this

probably won't help though because its' very random - likely good for other clustering applications but not equivalence

Thesis explaining it more if we want to implement

https://dial.uclouvain.be/memoire/ucl/en/object/thesis%3A8207/datastream/PDF_01/view

-------------------------------------------------------------------------------------------------------------------------

Ultimately, the problem is twofold. How can we implement the spectral clustering method which requires finding the eigenvalues of
    an adjacency matrix without constructing the n^2 matrix.
        -- sparse matrix? edge degree is quite low so this is possible
        -- matrix-free calculation? LOBPCG https://epubs.siam.org/doi/10.1137/S1064827500366124 

Secondly, is this stable...?

"""

from scipy.sparse import csr_matrix
from sklearn.cluster import SpectralClustering
from functools import reduce

from r1cs_scripts.circuit_representation import Circuit

from deprecated.modularity.modularity_optimisation import undirected_adjacency


def spectral_undirected_clustering(circ: Circuit):
    """
    ad-hoc testing

    TODO: improve + standardise

    Time jump from 700 -> 20000 is 1.7 -> 70s -- ~1.5 orders of magnitude..
    Not stable for Reveal indicating not stable for larger instances

    In theory the eigenvalues will be the same (with the same eigenvectors up to reordering), but numerical methods add innacuracies
    and non-numerical methods take too long.
    """

    adjacencies = undirected_adjacency(circ)

    acc = ([], [], [])
    def update(coni): acc[2].append(len(acc[0])); acc[0].extend(adjacencies[coni].values()); acc[1].extend(adjacencies[coni].keys())
    calc = map(update, range(circ.nConstraints))
    for _ in calc: pass
    acc[2].append(len(acc[0]))

    sparse = csr_matrix(acc, shape=[circ.nConstraints, circ.nConstraints])

    clustering = SpectralClustering(
        n_clusters=int(circ.nConstraints ** 0.5),
        eigen_solver='lobpcg',
        random_state=42,
        affinity = 'precomputed',
        assign_labels='cluster_qr',
        eigen_tol=1e-4
    )

    clustering.fit(sparse)

    # print(clustering.labels_)

    cluster_lists = {}

    for i in range(circ.nConstraints):
        cluster_lists.setdefault(clustering.labels_[i], []).append(i)
        # TODO: implement

    return cluster_lists