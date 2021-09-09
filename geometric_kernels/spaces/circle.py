"""
Spaces for which there exist analytical expressions for the manifold
and the eigenvalues and functions. Examples include the `Circle` and the `Hypersphere`.
The Geomstats package is used for most of the geometric calculations.
"""
from typing import Callable, Optional

import eagerpy as ep
import geomstats as gs
import numpy as np
from eagerpy import Tensor

from geometric_kernels.eagerpy_extras import cast_to_float, cos, from_numpy, sin
from geometric_kernels.eigenfunctions import Eigenfunctions, EigenfunctionWithAdditionTheorem
from geometric_kernels.spaces import DiscreteSpectrumSpace
from geometric_kernels.utils import chain


class SinCosEigenfunctions(EigenfunctionWithAdditionTheorem):
    """
    Eigenfunctions Laplace-Beltrami operator on the circle correspond
    to the Fourier basis, i.e. sin and cosines..
    """

    def __init__(self, num_eigenfunctions: int) -> None:
        assert (
            num_eigenfunctions % 2 == 1
        ), "num_eigenfunctions needs to be odd to include all eigenfunctions within a level."
        assert num_eigenfunctions >= 1

        self._num_eigenfunctions = num_eigenfunctions
        # We know `num_eigenfunctions` is odd, therefore:
        self._num_levels = num_eigenfunctions // 2 + 1

    def __call__(self, X: Tensor, **parameters) -> Tensor:
        """
        :param X: polar coordinates on the circle, [N, 1].
        :param parameters: unused.
        """
        theta = X
        const = 2.0 ** 0.5
        values = []
        for level in range(self.num_levels):
            if level == 0:
                values.append(ep.ones_like(theta))
            else:
                freq = 1.0 * level
                values.append(const * cos(freq * theta))
                values.append(const * sin(freq * theta))

        return ep.concatenate(values, axis=1)  # [N, M]

    def _addition_theorem(self, X: Tensor, X2: Tensor, **parameters) -> Tensor:
        r"""
        Returns the result of applying the additional theorem when
        summing over all the eigenfunctions within a level, for each level

        Concretely in the case for inputs on the sphere S^1:

        .. math:
            \sin(l \theta_1) \sin(l \theta_2) + \cos(l \theta_1) \cos(l \theta_2)
                = N_l \cos(l (\theta_1 - \theta_2)),
        where N_l = 1 for l = 0, else N_l = 2.

        :param X: [N, 1]
        :param X2: [N2, 1]
        :param parameters: unused.
        :return: Evaluate the sum of eigenfunctions on each level. Returns
            a value for each level [N, N2, L]
        """
        theta1, theta2 = X, X2
        angle_between = theta1[:, None, :] - theta2[None, :, :]  # [N, N2, 1]
        freqs = cast_to_float(ep.arange(X, self.num_levels))  # [L]
        values = cos(freqs[None, None, :] * angle_between)  # [N, N2, L]
        values = (
            cast_to_float(from_numpy(values, self.num_eigenfunctions_per_level[None, None, :]))
            * values
        )
        print(">>>", values)
        return values  # [N, N2, L]

    def _addition_theorem_diag(self, X: Tensor, **parameters) -> Tensor:
        """
        Returns the sum of eigenfunctions on a level for which we have a simplified expression

        :param X: [N, 1]
        :param parameters: unused.
        :return: Evaluate the sum of eigenfunctions on each level. Returns
            a value for each level [N, L]
        """
        N = X.shape[0]
        ones = ep.ones(X, (N, self.num_levels))  # [N, L]
        value = ones * cast_to_float(from_numpy(X, self.num_eigenfunctions_per_level[None, :]))
        return value  # [N, L]

    @property
    def num_eigenfunctions(self) -> int:
        """Number of eigenfunctions, M"""
        return self._num_eigenfunctions

    @property
    def num_levels(self) -> int:
        """
        Number of levels, L

        For each level except the first where there is just one, there are two
        eigenfunctions.
        """
        return self._num_levels

    @property
    def num_eigenfunctions_per_level(self) -> np.ndarray:
        """Number of eigenfunctions per level, [N_l]_{l=0}^{L-1}"""
        return np.array([1 if level == 0 else 2 for level in range(self.num_levels)])


class Circle(DiscreteSpectrumSpace, gs.geometry.hypersphere.Hypersphere):
    r"""
    Circle :math:`\mathbb{S}^1` manifold with sinusoids and cosines eigenfunctions.
    """

    def __init__(self):
        super().__init__(dim=1)

    def is_tangent(
        self,
        vector: Tensor,
        base_point: Optional[Tensor] = None,
        atol: float = gs.geometry.manifold.ATOL,
    ) -> bool:
        """
        Check whether the `vector` is tangent at `base_point`.
        :param vector: shape=[..., dim]
            Vector to evaluate.
        :param base_point: shape=[..., dim]
            Point on the manifold. Defaults to `None`.
        :param atol: float
            Absolute tolerance.
            Optional, default: 1e-6.
        :return: Boolean denoting if vector is a tangent vector at the base point.
        """
        raise NotImplementedError("`is_tangent` is not implemented for `Hypersphere`")

    @property
    def dimension(self) -> int:
        return 1

    def get_eigenfunctions(self, num: int) -> Eigenfunctions:
        """
        :param num: number of eigenfunctions returned.
        """
        return SinCosEigenfunctions(num)

    def get_eigenvalues(self, num: int) -> Tensor:
        """
        First `num` eigenvalues of the Laplace-Beltrami operator

        :return: [num, 1] array containing the eigenvalues
        """
        eigenfunctions = SinCosEigenfunctions(num)
        eigenvalues_per_level = ep.astensor(np.arange(eigenfunctions.num_levels) ** 2.0)  # [L,]
        eigenvalues = chain(
            eigenvalues_per_level, eigenfunctions.num_eigenfunctions_per_level
        )  # [num,]
        return ep.reshape(eigenvalues, (-1, 1))  # [num, 1]
