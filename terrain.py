"""
Terrain Analysis Module for LunarIce-360.

Computes geomorphological and illumination products from a Digital
Elevation Model (DEM) for landing-site safety assessment and rover
traverse planning in lunar south polar regions.

Products
--------
- Slope & Aspect  (from Sobel gradients)
- RMS Roughness   (local height variance)
- Hurst Exponent  (fractal surface characterisation)
- Illumination    (ray-tracing shadow/lit binary mask)
- Cumulative Illumination Fraction  (multi-azimuth, multi-elevation)
- Hazard Map      (composite safety score)
"""

import numpy as np
from scipy.ndimage import sobel, uniform_filter, generic_filter
from scipy.stats import linregress

from . import config


# =============================================================================
# SLOPE
# =============================================================================

def compute_slope(dem, pixel_size):
    """
    Compute terrain slope from a DEM using Sobel gradient operators.

    Parameters
    ----------
    dem : np.ndarray, shape (rows, cols)
        Elevation values in metres.
    pixel_size : float
        Ground spacing of DEM pixels in metres.

    Returns
    -------
    np.ndarray, shape (rows, cols)
        Slope in **degrees**.
    """
    dz_dx = sobel(dem, axis=1) / (8.0 * pixel_size)
    dz_dy = sobel(dem, axis=0) / (8.0 * pixel_size)
    slope_rad = np.arctan(np.sqrt(dz_dx ** 2 + dz_dy ** 2))
    return np.degrees(slope_rad)


# =============================================================================
# ASPECT
# =============================================================================

def compute_aspect(dem, pixel_size):
    """
    Compute terrain aspect (downhill direction) from a DEM.

    Parameters
    ----------
    dem : np.ndarray, shape (rows, cols)
        Elevation values in metres.
    pixel_size : float
        Ground spacing of DEM pixels in metres.

    Returns
    -------
    np.ndarray, shape (rows, cols)
        Aspect in **degrees**, range [0, 360).
        0° = North, 90° = East, etc.
    """
    dz_dx = sobel(dem, axis=1) / (8.0 * pixel_size)
    dz_dy = sobel(dem, axis=0) / (8.0 * pixel_size)
    aspect_rad = np.arctan2(-dz_dx, dz_dy)
    aspect_deg = np.degrees(aspect_rad) % 360.0
    return aspect_deg


# =============================================================================
# ROUGHNESS (RMS Height)
# =============================================================================

def compute_roughness_rms(dem, window_size=None):
    """
    Compute RMS height roughness as the square root of local variance.

    Uses a uniform (box) filter to estimate local mean and local
    mean-square, then derives variance = E[x²] - (E[x])².

    Parameters
    ----------
    dem : np.ndarray, shape (rows, cols)
        Elevation values in metres.
    window_size : int, optional
        Side length of the square averaging window (default from
        ``config.ROUGHNESS_WINDOW``).

    Returns
    -------
    np.ndarray, shape (rows, cols)
        RMS roughness in metres.
    """
    if window_size is None:
        window_size = config.ROUGHNESS_WINDOW

    local_mean = uniform_filter(dem.astype(np.float64), size=window_size)
    local_mean_sq = uniform_filter(dem.astype(np.float64) ** 2,
                                    size=window_size)
    variance = local_mean_sq - local_mean ** 2
    # Clamp numerical noise below zero
    variance = np.maximum(variance, 0.0)
    return np.sqrt(variance)


# =============================================================================
# HURST EXPONENT
# =============================================================================

def compute_hurst_exponent(dem, patch_size=64, lags=None):
    """
    Estimate per-patch Hurst exponent from the DEM structure function.

    For each non-overlapping patch the isotropic variogram is computed
    at the specified lags, and the Hurst exponent *H* is obtained from
    a linear regression on ``log(lag)`` vs ``log(variance)``:

        variance(lag) ∝ lag^{2H}  →  log(var) = 2H·log(lag) + const

    Parameters
    ----------
    dem : np.ndarray, shape (rows, cols)
        Elevation values in metres.
    patch_size : int, optional
        Side length of square patches (pixels).
    lags : list[int] or None, optional
        Pixel lags at which to compute the structure function.
        Defaults to ``[1, 2, 4, 8, 16, 32]``.

    Returns
    -------
    np.ndarray, shape (n_patches_y, n_patches_x)
        Hurst exponent map.  May contain ``NaN`` where the regression
        is ill-conditioned or a patch is too small.
    """
    if lags is None:
        lags = [1, 2, 4, 8, 16, 32]

    rows, cols = dem.shape
    n_patches_y = rows // patch_size
    n_patches_x = cols // patch_size

    H_map = np.full((n_patches_y, n_patches_x), np.nan)

    for py in range(n_patches_y):
        for px in range(n_patches_x):
            patch = dem[py * patch_size:(py + 1) * patch_size,
                        px * patch_size:(px + 1) * patch_size]

            # Skip if patch contains no valid data
            if patch.size == 0 or np.all(np.isnan(patch)):
                continue

            log_lags = []
            log_vars = []

            for lag in lags:
                if lag >= patch_size:
                    continue
                # Horizontal differences
                dh_x = patch[:, lag:] - patch[:, :-lag]
                # Vertical differences
                dh_y = patch[lag:, :] - patch[:-lag, :]

                all_diffs = np.concatenate([dh_x.ravel(), dh_y.ravel()])
                all_diffs = all_diffs[np.isfinite(all_diffs)]

                if len(all_diffs) < 2:
                    continue

                var = np.var(all_diffs)
                if var > 0:
                    log_lags.append(np.log(lag))
                    log_vars.append(np.log(var))

            if len(log_lags) >= 3:
                result = linregress(log_lags, log_vars)
                H = result.slope / 2.0
                # Physical range for Hurst exponent is (0, 1)
                if 0 < H < 1:
                    H_map[py, px] = H

    return H_map


# =============================================================================
# ILLUMINATION (RAY-TRACING)
# =============================================================================

def compute_illumination(dem, sun_elevation_deg, sun_azimuth_deg,
                         pixel_size):
    """
    Compute a binary illumination mask using a simplified ray-tracing
    approach.

    For each pixel, rays are cast from the sun direction by stepping
    through the DEM.  If a ray from a pixel hits higher terrain before
    reaching the sun, the pixel is shadowed.

    The algorithm uses **numpy array shifting** for efficiency: at each
    step distance the entire DEM is shifted and compared against the
    height threshold determined by the sun elevation.

    Parameters
    ----------
    dem : np.ndarray, shape (rows, cols)
        Elevation in metres.
    sun_elevation_deg : float
        Sun elevation angle above the horizon (degrees).
    sun_azimuth_deg : float
        Sun azimuth (degrees, 0 = North, clockwise).
    pixel_size : float
        Ground pixel spacing in metres.

    Returns
    -------
    np.ndarray, shape (rows, cols), dtype bool
        ``True`` where the pixel is illuminated, ``False`` where shadowed.
    """
    from scipy.ndimage import rotate
    
    rows, cols = dem.shape
    tan_elev = np.tan(np.radians(sun_elevation_deg))
    
    # 1. Rotate DEM so sun is coming from the left (West)
    # Standard azimuth: 0=N, 90=E. Image coords: row 0 is N, col 0 is W.
    # We want sun at West, so rotate by (270 - azimuth)
    angle = 270.0 - sun_azimuth_deg
    dem_rot = rotate(dem, angle, reshape=True, mode='nearest')
    
    # 2. Distance from left edge
    cols_rot = dem_rot.shape[1]
    x_coords = np.arange(cols_rot) * pixel_size
    
    # 3. Effective height: actual height minus the drop of the sun's ray
    H_eff = dem_rot - x_coords[np.newaxis, :] * tan_elev
    
    # 4. Sweep from left to right to find maximum blocking height
    H_max = np.maximum.accumulate(H_eff, axis=1)
    
    # 5. Shadowed if effective height is less than max encountered
    shadow_rot = H_eff < (H_max - 1e-4)
    
    # 6. Rotate back to original orientation
    shadow_full = rotate(shadow_rot, -angle, reshape=False, order=0)
    
    # 7. Crop back to original exact shape
    r_center = shadow_full.shape[0] / 2.0
    c_center = shadow_full.shape[1] / 2.0
    
    r_start = int(round(r_center - rows / 2.0))
    c_start = int(round(c_center - cols / 2.0))
    
    shadow = shadow_full[r_start:r_start + rows, c_start:c_start + cols]
    
    return ~shadow


# =============================================================================
# CUMULATIVE ILLUMINATION
# =============================================================================

def compute_cumulative_illumination(dem, pixel_size, n_azimuths=None,
                                     sun_elevations=None):
    """
    Average illumination over many sun positions to estimate the
    fractional illumination of each pixel.

    Parameters
    ----------
    dem : np.ndarray, shape (rows, cols)
        Elevation in metres.
    pixel_size : float
        Ground pixel spacing in metres.
    n_azimuths : int, optional
        Number of azimuth steps over 360° (default from
        ``config.N_AZIMUTH_STEPS``).
    sun_elevations : list[float], optional
        Sun elevation angles in degrees (default from
        ``config.SUN_ELEVATION_RANGE``).

    Returns
    -------
    np.ndarray, shape (rows, cols)
        Illumination fraction in [0, 1].
    """
    if n_azimuths is None:
        n_azimuths = config.N_AZIMUTH_STEPS
    if sun_elevations is None:
        sun_elevations = config.SUN_ELEVATION_RANGE

    rows, cols = dem.shape
    accum = np.zeros((rows, cols), dtype=np.float64)
    count = 0

    azimuths = np.linspace(0, 360, n_azimuths, endpoint=False)

    for elev in sun_elevations:
        for az in azimuths:
            lit = compute_illumination(dem, elev, az, pixel_size)
            accum += lit.astype(np.float64)
            count += 1

    if count > 0:
        accum /= count

    return accum


# =============================================================================
# HAZARD MAP
# =============================================================================

def compute_hazard_map(slope, roughness, illumination_frac, weights=None):
    """
    Compute a composite hazard map from normalised terrain metrics.

    Each input is linearly normalised to [0, 1] and combined via a
    weighted sum.  Higher values indicate **more hazardous** terrain.

    - **Slope**: normalised directly (steeper = more dangerous).
    - **Roughness**: normalised directly (rougher = more dangerous).
    - **Illumination**: inverted (less light = more dangerous).

    Parameters
    ----------
    slope : np.ndarray (rows, cols)
        Slope in degrees.
    roughness : np.ndarray (rows, cols)
        RMS roughness in metres.
    illumination_frac : np.ndarray (rows, cols)
        Illumination fraction in [0, 1].
    weights : dict or None, optional
        Keys ``'slope'``, ``'roughness'``, ``'illumination'``.
        Defaults to equal weights ``{1/3, 1/3, 1/3}``.

    Returns
    -------
    np.ndarray, shape (rows, cols)
        Hazard score in [0, 1].  0 = safe, 1 = dangerous.
    """
    if weights is None:
        weights = {'slope': 1.0 / 3, 'roughness': 1.0 / 3,
                   'illumination': 1.0 / 3}

    def _normalise(arr):
        """Min-max normalise to [0, 1]."""
        a_min = np.nanmin(arr)
        a_max = np.nanmax(arr)
        denom = a_max - a_min
        if denom == 0:
            return np.zeros_like(arr, dtype=np.float64)
        return (arr - a_min) / denom

    slope_norm = _normalise(slope)
    rough_norm = _normalise(roughness)
    illum_inv = 1.0 - np.clip(illumination_frac, 0.0, 1.0)

    hazard = (weights.get('slope', 1 / 3) * slope_norm
              + weights.get('roughness', 1 / 3) * rough_norm
              + weights.get('illumination', 1 / 3) * illum_inv)

    total_w = sum(weights.values())
    if total_w > 0:
        hazard /= total_w

    return np.clip(hazard, 0.0, 1.0)


# =============================================================================
# ORCHESTRATOR
# =============================================================================

def run_terrain_analysis(dem, pixel_size):
    """
    Run the full terrain analysis pipeline.

    Parameters
    ----------
    dem : np.ndarray, shape (rows, cols)
        Elevation in metres.
    pixel_size : float
        Ground pixel spacing in metres.

    Returns
    -------
    dict
        'slope'               : slope map (degrees).
        'aspect'              : aspect map (degrees, 0-360).
        'roughness'           : RMS roughness map (metres).
        'hurst'               : Hurst exponent map (may contain NaN).
        'illumination_frac'   : cumulative illumination fraction [0, 1].
        'hazard_map'          : composite hazard score [0, 1].
    """
    slope = compute_slope(dem, pixel_size)
    aspect = compute_aspect(dem, pixel_size)
    roughness = compute_roughness_rms(dem)
    hurst = compute_hurst_exponent(dem)
    illum_frac = compute_cumulative_illumination(dem, pixel_size)
    hazard = compute_hazard_map(slope, roughness, illum_frac)

    return {
        'slope': slope,
        'aspect': aspect,
        'roughness': roughness,
        'hurst': hurst,
        'illumination_frac': illum_frac,
        'hazard_map': hazard,
    }
