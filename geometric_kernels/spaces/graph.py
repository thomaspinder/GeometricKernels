"""
Graph object
"""

from typing import Dict, Tuple

import lab as B
import numpy as np

from geometric_kernels.lab_extras import degree, eigenpairs, set_value
from geometric_kernels.spaces.base import (
    ConvertEigenvectorsToEigenfunctions,
    DiscreteSpectrumSpace,
)
from geometric_kernels.spaces.eigenfunctions import Eigenfunctions


class Graph(DiscreteSpectrumSpace):
    """
    Represents an arbitrary undirected graph.
    """

    def __init__(self, adjacency_matrix: B.Numeric):  # type: ignore
        """
        :param adjacency_matrix: An n-dimensional square, symmetric matrix,
            where adjacency_matrix[i, j] is non-zero if there is an edge
            between nodes i and j. Scipy's sparse matrices are supported.
        """
        self.cache: Dict[int, Tuple[B.Numeric, B.Numeric]] = {}
        self._checks(adjacency_matrix)
        self.set_laplacian(adjacency_matrix)  # type: ignore

    @staticmethod
    def _checks(adjacency):
        assert (
            len(B.shape(adjacency)) == 2 and adjacency.shape[0] == adjacency.shape[1]
        ), "Matrix is not square."

        # this is more efficient than (adj == adj.T).all()
        assert not B.any(adjacency != B.T(adjacency)), "Adjacency is not symmetric."

    @property
    def dimension(self) -> int:
        return 0  # this is needed for the kernel math to work out

    def set_laplacian(self, adjacency):
        self._laplacian = degree(adjacency) - adjacency

    def get_eigensystem(self, num):
        """
        Returns the first `num` eigenvalues and eigenvectors of the graph Laplacian.
        Caches the solution to prevent re-computing the same values. Note that, if a
        sparse scipy matrix is input, requesting all n eigenpairs will lead to a
        conversion of the sparse matrix to a dense one due to scipy.sparse.linalg.eigsh
        limitations.

        :param num: number of eigenvalues and functions to return.
        :return: A Tuple of eigenvectors [n, num], eigenvalues [num, 1]
        """
        if num not in self.cache:
            evals, evecs = eigenpairs(self._laplacian, num)
            evals = set_value(
                evals, 0, np.finfo(float).eps
            )  # lowest eigenval should be zero

            self.cache[num] = (evecs, evals[:, None])

        return self.cache[num]

    def get_eigenfunctions(self, num: int) -> Eigenfunctions:
        """
        First `num` eigenfunctions of the Laplace-Beltrami operator on the Graph.

        :param num: number of eigenfunctions returned
        :return: eigenfu [n, num]
        """
        eigenfunctions = ConvertEigenvectorsToEigenfunctions(self.get_eigenvectors(num))
        return eigenfunctions

    def get_eigenvectors(self, num: int) -> B.Numeric:
        """
        :param num: number of eigenvectors returned
        :return: eigenvectors [n, num]
        """
        return self.get_eigensystem(num)[0]

    def get_eigenvalues(self, num: int) -> B.Numeric:
        """
        :param num: number of eigenvalues returned
        :return: eigenvalues [num, 1]
        """
        return self.get_eigensystem(num)[1]

    def get_repeated_eigenvalues(self, num: int) -> B.Numeric:
        """
        :param num: number of eigenvalues
        :return: eigenvalues [num, 1]
        """
        return self.get_eigenvalues(num)
