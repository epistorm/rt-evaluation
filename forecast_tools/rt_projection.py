import numpy as np
import pandas as pd

WEEKLEN = 7  # Number of days in a week


class RtData:
    """An ensemble of R(t) time series.

    Exposes methods to calculate commonly used statistics over the
    ensemble.

    Attributes
    ----------
    array : np.ndarray
        2D array with the R(t) data.
        Signature: array[i_sample, i_period]
    df : pd.DataFrame
        Pandas data frame with the R(t) data. Linked to `array`.
        Signature: df.loc[i_sample, i_period]

    Notes
    -----
    Calculation uses smart getters, avoiding repeated calculations.

    """

    def __init__(self, array: np.ndarray, file_path=None):

        # Main containers
        self.array: np.ndarray = array  # Expected signature: a[exec][i_t]
        self.nperiods = array.shape[1]  # Number of time stamps in the dataset
        self.nsamples = array.shape[0]  # Nr. of iterations from the MCMC process

        self.df = pd.DataFrame(array)  # a[exec][i_t]

        # Default calculation parameters
        self.rolling_width = WEEKLEN
        self.quantile_alpha = 0.05

        # Attributes that can be calculated with smart getters.
        self._avg = None  # Average time series. Np array.  | a[i_t]
        self._rolling_mean = None  # Rolling average ensemble  | a[exec][i_t]
        self._rolling_mean_avg = None  # Mean of the individual rolling averages  | a[i_t]
        self._median: np.ndarray = None  # Median time series  |  a[i_t]
        self._median_pd: pd.Series = None
        self._loquant = None  # Lower quantiles  | a[i_t]
        self._hiquant = None  # Upper quantiles  | a[i_t]
        self._loquant_pd: pd.Series = None  # Lower quantiles  | a[i_t]
        self._hiquant_pd: pd.Series = None  # Upper quantiles  | a[i_t]
        self._roll_loquant = None  # Lower quantile of the rolling average  | a[i_t]
        self._roll_upquant = None
        self._sortd: np.ndarray = None  # Iteration-sorted R(t) for each t  | a[exec][i_t]

        # Etc
        self.file_path = file_path

    def get_avg(self, force_calc=False):
        """Return the average time series (average over ensemble of MCMC iterations)."""
        if self._avg is None or force_calc:
            self._avg = np.average(self.array, axis=0)
        return self._avg

    def get_median(self, force_calc=False):
        if self._median is None or force_calc:
            self._median = np.median(self.array, axis=0)
        return self._median

    def get_median_pd(self, force_calc=False):
        """Use the pandas interface and returns as a series."""
        if self._median_pd is None or force_calc:
            self._median_pd = self.df.median(axis=0)
        return self._median_pd

    def get_quantiles(self, alpha=None, force_calc=False):
        """Return the lower and upper quantiles for the raw data (as time series)."""
        if alpha is not None and alpha != self.quantile_alpha:
            self.quantile_alpha = alpha
            force_calc = True

        if self._loquant is None or self._hiquant is None or force_calc:
            self._loquant = np.quantile(
                self.array, self.quantile_alpha / 2, axis=0)
            self._hiquant = np.quantile(
                self.array, 1.0 - self.quantile_alpha / 2, axis=0)
        return self._loquant, self._hiquant

    def get_quantiles_pd(self, alpha=None, force_calc=False):
        """Return the lower and upper quantiles for the raw data (as pandas time series)."""
        if alpha is not None and alpha != self.quantile_alpha:
            self.quantile_alpha = alpha
            force_calc = True

        if self._loquant_pd is None or self._hiquant_pd is None or force_calc:
            self._loquant_pd = self.df.quantile(
                self.quantile_alpha / 2, axis=0
            )
            self._hiquant_pd = self.df.quantile(
                1.0 - self.quantile_alpha / 2, axis=0
            )
            # self._hiquant_pd = np.quantile(
            #     self.array, 1.0 - self.quantile_alpha / 2, axis=0)
        return self._loquant_pd, self._hiquant_pd

    def get_rolling_mean(self, width=None, force_calc=False):
        """
        Return the INDIVIDUAL rolling average of each MCMC iteration.
        Signature: a[exec][i_t] (DataFrame)
        """
        if width is not None and width != self.rolling_width:
            self.rolling_width = width
            force_calc = True

        if self._rolling_mean is None or force_calc:
            self._rolling_mean = self.df.rolling(
                self.rolling_width, center=False, axis=1
            ).mean()

        return self._rolling_mean

    def get_rolling_mean_avg(self, width=None, force_calc=False):
        """
        Get the AVERAGE time series of the rolling means.
        Signature: a[i_t] (DataFrame)
        """
        if width is not None and width != self.rolling_width:
            self.rolling_width = width
            force_calc = True

        if self._rolling_mean_avg is None or force_calc:
            roll = self.get_rolling_mean(width=width, force_calc=force_calc)
            self._rolling_mean_avg = roll.mean(axis=0)

        return self._rolling_mean_avg

    def get_rolling_quantiles(self, alpha=None, width=None, force_calc=False):
        """Return the quantiles of the individual rolling averages."""
        if alpha is not None and alpha != self.quantile_alpha:
            self.quantile_alpha = alpha
            force_calc = True

        if width is not None and width != self.rolling_width:
            self.rolling_width = width
            force_calc = True

        if (self._roll_loquant is None or self._roll_upquant is None
                or force_calc):
            roll = self.get_rolling_mean(force_calc)
            self._roll_loquant = roll.quantile(
                q=self.quantile_alpha/2, axis=0)
            self._roll_upquant = roll.quantile(
                q=1.0 - self.quantile_alpha/2, axis=0)

        return self._roll_loquant, self._roll_upquant

    def get_sortd(self):
        """Return the iteration-sorted R(t) ensemble for each time step. This is, for each t, the ensemble of R(t)
        values (iterations) is sorted.
        """
        if self._sortd is None:
            self._sortd = np.sort(self.array, axis=0)

        return self._sortd


def get_sorted_mean_ensemble(
        rtm: RtData, nperiods_past, q_low, q_hig, r_max=None,
):
    """Sorts the ensembles of R(t) values (at each time,
    independently), gets an interquantile range and then calculates
    the average over each sorted time series.

    Optionally, values are also filtered by its maximum value.

    Returns
    -------
    out : np.ndarray
        A 1D array with the averages of each R(t) sorted curve.
    """
    # Sort and get IQR
    i_low, i_hig = [round(rtm.nsamples * q) for q in (q_low, q_hig)]
    filt = rtm.get_sortd()[i_low:i_hig, -nperiods_past:]

    # Calculate mean ensemble and filter by maximum
    mean_vals = filt.mean(axis=1)

    if r_max is not None:
        mean_vals = mean_vals[
                    :np.searchsorted(mean_vals, r_max, side="right")]

    return mean_vals



def extend_1darray_repeat(arr, nperiods, dtype=float, out=None):
    # Repeats mean values over time
    if out is None:
        out = np.empty((arr.shape[0], nperiods), dtype=dtype)

    # out[:] = np.tile(arr[:, np.newaxis], (1, nperiods))  # Slower!
    for i in range(nperiods):
        out[:, i] = arr

    return out


def flat_avg_synth(
        nperiods_fore, rtm: RtData, nperiods_past,
        q_low=0.0, q_hig=1.0, r_max=None, **kwargs):
    """TODO DOCS"""

    mean_vals = get_sorted_mean_ensemble(
        rtm, nperiods_past, q_low, q_hig, r_max)

    out = extend_1darray_repeat(mean_vals, nperiods_fore)

    return out


def apply_static_ramp_inplace(arr, k_start, k_end, nperiods):
    """"""
    arr *= np.linspace(k_start, k_end, nperiods)[np.newaxis, :]


def static_ramp_avg_synth(
        nperiods_fore, rtm: RtData, nperiods_past,
        k_start, k_end,
        q_low=0.0, q_hig=1.0, r_max=None,
        **kwargs
):
    """Generate a linear R(t) series based on the averages of estimated
    values from the past.

    Each time series is generated from a sample value of R, which
    is multiplied by k_start at the beginning of the fore time series
    and by k_end at the end. Values in between are linearly
    interpolated.

    Parameters
    ----------
    nperiods_fore : int
        Number of forward periods to generate for.
    rtm : RtData
        Object with the past R(t) estimation ensemble.
    nperiods_past : int
        Number of backward periods up to which the average is taken.
    q_low : float, optional
        Lower boundary of the interquantile range to filter by.
    q_hig : float, optional
        Upper boundary of the interquantile range to filter by.
        Default takes the entire sample.
    k_start : float
        Ramp coefficient to apply at the start of the future R(t)
        time series.
    k_end : float
        Ramp coefficient to apply at the end of the future R(t)
        time series.
    r_max : float, optional
        Maximum value of the R average accepted. The ensemble is
        truncated up to this point.
        Defaults to None, which causes no truncation.
    logger : logging.Loger, optional
        Alternative logger object. Defaults to module's logger.

    Returns
    -------
    out : np.ndarray
        Array with synthesized R(t) values.
        Signature: out[i_sample, i_t]
    """
    out = flat_avg_synth(
        nperiods_fore, rtm, nperiods_past, q_low, q_hig, r_max)

    apply_static_ramp_inplace(out, k_start, k_end, nperiods_fore)

    return out