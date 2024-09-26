
import math

import numpy as np
import scipy.stats


class TgBase:
    """DOCS TO BE BUILT

    Notes
    -----
    The values of the generation time are measured in units of the
    granular dt.

    """
    is_const: bool
    params: list
    nparams: int

    def __init__(self, tmax=None):
        self.tmax = tmax

    def get_param_arrays_byindex(
            self, start=None, stop=None):
        """"""
        raise NotImplementedError

    def get_param_arrays_bysize(self, size):
        """"""
        raise NotImplementedError

    def get_pmf_array(self, idx=None):
        """Return a probability mass function (PMF) of the generation
        time for primary cases reported at time given by `idx`.

        This PMF is a sequence of size `self.max`, where the i-th
        element is the probability that a secondary case created
        from a primary one at time `idx` will be reported at `i`periods
        after time `idx`.
        In this sense, the function returns the Tg distribution for
        primary cases at time 'idx'.

        The first entry of the PMF array is dummy, as same-period
        generations are not considered in the Rtrend model. Thus,
        the PMF array is normalized such that `sum(pmf[1:]) = 1`.

        Parameters
        ----------
        TODO

        Returns
        -------
        TODO

        Notes
        -----
        Parameter `idx` is optional for constant tg distributions
        (i.e., with self.is_const = True). It is required if the
        distribution is variable.

        """
        raise NotImplementedError


class ConstGammaTg(TgBase):
    """Gamma-distributed generation time with constant parameters."""
    is_const = True
    params = ["shape", "rate"]
    nparams = 2

    def __init__(self, shape, rate, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # TODO: assert values (>0)

        self.shape = shape
        self.rate = rate

        self.avg = shape / rate
        self.std = math.sqrt(shape) / rate

        if self.tmax is None:
            # Take a sufficiently high truncation point
            # devnote: could use CDF > high value
            self.tmax = math.ceil(self.avg + 10 * self.std)

        # Pre-build the normalized P(Tg) array once.
        self._pmf = scipy.stats.gamma.pdf(
            np.arange(self.tmax), a=self.shape, scale=1. / self.rate)
        self._pmf /= self._pmf[1:].sum()

    def get_param_arrays_byindex(
            self, start=None, stop=None):
        raise ValueError(
            f"Hey, class {self.__class__.__name__} cannot get a"
            f" parameter array by index because it is constant.")

    def get_param_arrays_bysize(self, size):

        return np.repeat(np.array([[self.shape, self.rate]]),
                         size, axis=0)

    def get_pmf_array(self, idx=None):
        return self._pmf

