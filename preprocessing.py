"""
Preprocessing Module for LunarIce-360.

Provides speckle filtering (Lee adaptive, boxcar), dB conversion
utilities, and a combined preprocessing pipeline for Stokes
parameter channels.
"""

import numpy as np
from scipy.ndimage import uniform_filter

from . import config
from .data_loader import validate_stokes


# =============================================================================
# Speckle Filters
# =============================================================================

def lee_filter(image, window_size=None):
    """Apply the Adaptive Lee speckle filter.

    The Lee filter preserves edges while reducing speckle noise by
    adapting the smoothing strength locally.  Where the local
    coefficient of variation is high (edges/point targets) the filter
    retains the original pixel; where it is low (homogeneous regions)
    the filter converges toward the local mean.

    .. math::

        \\hat{I}(i,j) = \\bar{I} + W \\cdot (I - \\bar{I})

    where ``W = 1 - Var_noise / Var_local`` (clipped to [0, 1]).

    Parameters
    ----------
    image : numpy.ndarray
        2-D input image (linear power scale).
    window_size : int, optional
        Side length of the square filter window (must be odd).
        Defaults to ``config.SPECKLE_FILTER_WINDOW``.

    Returns
    -------
    filtered : numpy.ndarray
        Speckle-filtered image (same shape as *image*).
    """
    if window_size is None:
        window_size = config.SPECKLE_FILTER_WINDOW

    image = np.asarray(image, dtype=np.float64)

    # Local statistics via uniform (box) filter
    local_mean = uniform_filter(image, size=window_size, mode='reflect')
    local_sq_mean = uniform_filter(image ** 2, size=window_size,
                                   mode='reflect')
    local_variance = np.maximum(local_sq_mean - local_mean ** 2, 0.0)

    # Estimate noise variance from the overall image
    # For fully-developed speckle the noise variance equals the
    # square of the overall mean (single-look).
    overall_mean = np.nanmean(image)
    noise_variance = overall_mean ** 2 if overall_mean != 0 else 1e-10

    # Adaptive weight: 0 → full smoothing, 1 → keep original
    weight = np.where(
        local_variance > 0,
        np.clip(1.0 - noise_variance / local_variance, 0.0, 1.0),
        0.0,
    )

    filtered = local_mean + weight * (image - local_mean)
    return filtered


def boxcar_filter(image, window_size=5):
    """Apply a simple boxcar (spatial averaging) filter.

    Parameters
    ----------
    image : numpy.ndarray
        2-D input image.
    window_size : int, default 5
        Side length of the square averaging window.

    Returns
    -------
    filtered : numpy.ndarray
        Spatially averaged image (same shape as *image*).
    """
    image = np.asarray(image, dtype=np.float64)
    filtered = uniform_filter(image, size=window_size, mode='reflect')
    return filtered


# =============================================================================
# Combined Stokes Preprocessing
# =============================================================================

def preprocess_stokes(S1, S2, S3, S4, filter_type='lee', window_size=None):
    """Apply speckle filtering to all four Stokes channels.

    Parameters
    ----------
    S1, S2, S3, S4 : numpy.ndarray
        Raw Stokes parameter arrays.
    filter_type : {'lee', 'boxcar'}, default 'lee'
        Which speckle filter to apply.
    window_size : int, optional
        Window size forwarded to the chosen filter.  Defaults to
        ``config.SPECKLE_FILTER_WINDOW`` for Lee and 5 for boxcar.

    Returns
    -------
    S1_f, S2_f, S3_f, S4_f : numpy.ndarray
        Filtered Stokes parameter arrays.

    Raises
    ------
    ValueError
        If *filter_type* is not recognised.
    """
    filter_type = filter_type.lower().strip()

    if filter_type == 'lee':
        filt = lee_filter
        if window_size is None:
            window_size = config.SPECKLE_FILTER_WINDOW
    elif filter_type == 'boxcar':
        filt = boxcar_filter
        if window_size is None:
            window_size = 5
    else:
        raise ValueError(
            f"Unknown filter_type '{filter_type}'. Use 'lee' or 'boxcar'."
        )

    print(f"[preprocessing] Applying {filter_type} filter "
          f"(window={window_size}) to Stokes channels…")

    S1_f = filt(S1, window_size=window_size)
    S2_f = filt(S2, window_size=window_size)
    S3_f = filt(S3, window_size=window_size)
    S4_f = filt(S4, window_size=window_size)

    # Validate filtered output
    validate_stokes(S1_f, S2_f, S3_f, S4_f)

    return S1_f, S2_f, S3_f, S4_f


# =============================================================================
# dB Conversion Utilities
# =============================================================================

def to_db(linear_value):
    """Convert linear power values to decibels.

    .. math::

        \\text{dB} = 10 \\log_{10}(\\text{linear\\_value})

    Zero and negative values are mapped to ``-np.inf`` (or handled
    gracefully with a very small floor value).

    Parameters
    ----------
    linear_value : float or numpy.ndarray
        Linear power value(s).

    Returns
    -------
    db_value : float or numpy.ndarray
        Power in decibels.
    """
    linear_value = np.asarray(linear_value, dtype=np.float64)

    # Replace zeros / negatives with a tiny positive number to avoid
    # -inf / nan in the log.  Using 1e-30 gives ≈ -300 dB floor.
    safe = np.where(linear_value > 0, linear_value, 1e-30)
    db_value = 10.0 * np.log10(safe)
    return db_value


def from_db(db_value):
    """Convert decibel values back to linear power.

    .. math::

        \\text{linear} = 10^{\\text{dB} / 10}

    Parameters
    ----------
    db_value : float or numpy.ndarray
        Power in decibels.

    Returns
    -------
    linear_value : float or numpy.ndarray
        Linear power value(s).
    """
    db_value = np.asarray(db_value, dtype=np.float64)
    linear_value = np.power(10.0, db_value / 10.0)
    return linear_value
