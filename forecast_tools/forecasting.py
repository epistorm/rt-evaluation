
import numba as nb
import numpy as np
import pandas as pd
import time





def reconstruct_ct(ct_past, rt_fore, tg_array, tg_max=None, ct_fore=None, seed=None, **kwargs):
    """
    This function will later be the wrapper for numbaed functions. It should be able to handle both single R(t) series
    and ensembles of these as well.


    (draft, under construction)
    NOTICE: the calculation is recursive (C(t) depends on C(t - s)), thus cannot be vectorized.
    ------
    ct_past :
        Vector of number of cases in the past.
    rt_fore : Union(np.ndarray, pd.Series, pd.DataFrame)
        A time series with R(t) in future steps. Its size is assumed as steps_fut.
        For now, I expect a pandas Series. I can review this as needed though. E.g. accept 2d arrays.
        The size of the forecast is assumed to be the size of this vector.
    tg_array :
        Vector with Tg(s), where s is time since infection.
    ct_fore :
        c_futu. Contains the forecast.
    tg_max :
        Truncation value (one past) for generation time.
    """
    num_steps_fore = rt_fore.shape[-1]

    # Input types interpretation
    # --------------------------

    # --- R(t) input
    run_mult = False  # Whether to run the reconstruction over multiple R(t) series.
    if isinstance(rt_fore, np.ndarray):  # Numpy array
        if rt_fore.ndim == 2:
            run_mult = True
        elif rt_fore.ndim > 2:
            raise ValueError(f"Hey, input R(t) array rt_fore must either be 1D or 2D (ndim = {rt_fore.ndim}).")

    elif isinstance(rt_fore, pd.Series):  # Pandas 1D series
        rt_fore = rt_fore.to_numpy()

    elif isinstance(rt_fore, pd.DataFrame):  # Pandas 2D data frame
        rt_fore = rt_fore.to_numpy()
        run_mult = True

    else:
        raise TypeError(f"Hey, invalid type for input R(t) rt_fore: {type(rt_fore)}")

    # --- C(t) past array
    if isinstance(ct_past, pd.Series):
        ct_past = ct_past.to_numpy()

    # --- Tg(s) array
    if isinstance(tg_array, pd.Series):
        tg_array = tg_array.to_numpy()

    # Optional arguments handling
    # ---------------------------

    if tg_max is None:
        tg_max = tg_array.shape[0]

    # Output array
    if ct_fore is None:
        ct_fore = np.empty_like(rt_fore, dtype=int)  # Agnostic to 1D or 2D

    # Time-based seed
    if seed is None:
        seed = round(1000 * time.time())

    # Dispatch and run the reconstruction
    # -----------------------------------
    if run_mult:
        return _reconstruct_ct_multiple(ct_past, rt_fore, tg_array, tg_max, ct_fore,
                                        num_steps_fore, seed)
    else:
        return _reconstruct_ct_single(ct_past, rt_fore, tg_array, tg_max, ct_fore,
                                      num_steps_fore, seed)


@nb.njit
def _reconstruct_ct_multiple(ct_past, rt_fore_2d, tg_dist, tg_max, ct_fore_2d, num_steps_fore, seed):

    np.random.seed(seed)  # Seeds the numba or numpy generator

    # Main loop over R(t) samples
    for rt_fore, ct_fore in zip(rt_fore_2d, ct_fore_2d):

        # Loop over future steps
        for i_t_fut in range(num_steps_fore):  # Loop over future steps
            lamb = 0.  # Sum of generated cases from past cases
            # r_curr = rt_fore.iloc[i_t_fut]  # Pandas
            r_curr = rt_fore[i_t_fut]

            # Future series chunk
            for st in range(1, min(i_t_fut + 1, tg_max)):
                lamb += r_curr * tg_dist[st] * ct_fore[i_t_fut - st]

            # Past series chunk
            for st in range(i_t_fut + 1, tg_max):
                lamb += r_curr * tg_dist[st] * ct_past[-(st - i_t_fut)]

            # Poisson number
            ct_fore[i_t_fut] = np.random.poisson(lamb)

    return ct_fore_2d


@nb.njit
def _reconstruct_ct_single(ct_past, rt_fore, tg_dist, tg_max, ct_fore, num_steps_fore, seed):

    np.random.seed(seed)  # Seeds the numba or numpy generator

    # Main loop over future steps
    for i_t_fut in range(num_steps_fore):  # Loop over future steps
        lamb = 0.  # Sum of generated cases from past cases
        # r_curr = rt_fore.iloc[i_t_fut]  # Pandas
        r_curr = rt_fore[i_t_fut]

        # Future series chunk
        for st in range(1, min(i_t_fut + 1, tg_max)):
            lamb += r_curr * tg_dist[st] * ct_fore[i_t_fut - st]

        # Past series chunk
        for st in range(i_t_fut + 1, tg_max):
            lamb += r_curr * tg_dist[st] * ct_past[-(st - i_t_fut)]

        # Poisson number
        ct_fore[i_t_fut] = np.random.poisson(lamb)

    return ct_fore