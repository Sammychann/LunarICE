"""
Landing Site Selection Module for LunarIce-360.

Evaluates candidate landing locations near detected ice deposits using
terrain safety, illumination, proximity to ice, and surface flatness.

The pipeline produces a continuous score map across the DEM, from which
the top N non-overlapping sites are extracted and ranked.
"""

import numpy as np
from scipy.ndimage import generic_filter

from . import config


# =============================================================================
# PROXIMITY SCORE
# =============================================================================

def compute_proximity_score(shape, target_center, pixel_size,
                            ideal_dist=None, sigma=None):
    """
    Compute a Gaussian proximity score centred on an ideal distance
    from a target location (e.g., an ice deposit).

    score(r) = exp(-((r - ideal_dist)² / (2 σ²)))

    Pixels at exactly ``ideal_dist`` metres from the target receive
    a score of 1.0;  the score falls off as a Gaussian on either side.

    Parameters
    ----------
    shape : tuple (rows, cols)
        Shape of the output score map.
    target_center : tuple (row, col)
        Pixel coordinates of the target (e.g., centre of ice deposit).
    pixel_size : float
        Ground pixel spacing in metres.
    ideal_dist : float, optional
        Ideal distance in metres (default from
        ``config.LANDING_IDEAL_DISTANCE``).
    sigma : float, optional
        Gaussian width in metres (default from
        ``config.LANDING_DISTANCE_SIGMA``).

    Returns
    -------
    np.ndarray, shape (rows, cols)
        Proximity score in [0, 1].
    """
    if ideal_dist is None:
        ideal_dist = config.LANDING_IDEAL_DISTANCE
    if sigma is None:
        sigma = config.LANDING_DISTANCE_SIGMA

    rows, cols = shape
    rr, cc = np.meshgrid(np.arange(rows), np.arange(cols), indexing='ij')

    # Distance in metres from target
    dist_m = np.sqrt(((rr - target_center[0]) * pixel_size) ** 2
                     + ((cc - target_center[1]) * pixel_size) ** 2)

    score = np.exp(-((dist_m - ideal_dist) ** 2) / (2.0 * sigma ** 2))
    return score


# =============================================================================
# FLATNESS SCORE
# =============================================================================

def compute_flatness_score(slope, window_size=11, max_slope=None):
    """
    Determine surface flatness by checking the **local maximum slope**
    within a sliding window.

    A pixel is considered flat (score = 1) if the maximum slope in
    its neighbourhood is below ``max_slope``; otherwise score = 0.

    Parameters
    ----------
    slope : np.ndarray (rows, cols)
        Slope in degrees.
    window_size : int, optional
        Side length of the square evaluation window (pixels).
    max_slope : float, optional
        Maximum acceptable local slope in degrees (default 8.0°).

    Returns
    -------
    np.ndarray, shape (rows, cols), dtype bool
        ``True`` (1) where the surface is sufficiently flat.
    """
    if max_slope is None:
        max_slope = 8.0

    local_max_slope = generic_filter(slope, np.max, size=window_size)
    return local_max_slope < max_slope


# =============================================================================
# MULTI-CRITERIA SCORING
# =============================================================================

def score_landing_sites(slope, hazard_map, illumination_frac,
                        target_center, pixel_size, weights=None):
    """
    Produce a composite landing-site score map.

    Hard constraints (binary):
        - Slope must be < ``config.LANDING_MAX_SLOPE`` (10°).
        - Local flatness check (``compute_flatness_score``).

    Soft criteria (continuous, combined via weighted sum):
        - **Safety**: ``1 - hazard_map`` (higher = safer).
        - **Illumination**: ``illumination_frac``.
        - **Proximity**: Gaussian score relative to target.
        - **Flatness**: (already folded into the hard mask, but
          a continuous flatness measure is also weighted in as
          ``1 - slope / LANDING_MAX_SLOPE`` for pixels that pass).

    Parameters
    ----------
    slope : np.ndarray (rows, cols)
        Slope in degrees.
    hazard_map : np.ndarray (rows, cols)
        Hazard score [0, 1] (0 = safe).
    illumination_frac : np.ndarray (rows, cols)
        Illumination fraction [0, 1].
    target_center : tuple (row, col)
        Pixel coordinates of the ice target.
    pixel_size : float
        Ground pixel spacing in metres.
    weights : dict or None, optional
        Keys: 'safety', 'illumination', 'proximity', 'flatness'.
        Defaults to ``config.LANDING_WEIGHTS``.

    Returns
    -------
    np.ndarray, shape (rows, cols)
        Landing suitability score in [0, 1].  Pixels that fail hard
        constraints are set to 0.
    """
    if weights is None:
        weights = config.LANDING_WEIGHTS

    rows, cols = slope.shape

    # ---- Hard constraints ----
    slope_ok = slope < config.LANDING_MAX_SLOPE
    flat_ok = compute_flatness_score(slope)
    hard_mask = slope_ok & flat_ok

    # ---- Soft criteria ----
    safety_score = 1.0 - np.clip(hazard_map, 0.0, 1.0)
    illum_score = np.clip(illumination_frac, 0.0, 1.0)
    prox_score = compute_proximity_score(
        (rows, cols), target_center, pixel_size)
    flatness_score = np.clip(1.0 - slope / config.LANDING_MAX_SLOPE,
                             0.0, 1.0)

    w_safe = weights.get('safety', 0.30)
    w_illum = weights.get('illumination', 0.25)
    w_prox = weights.get('proximity', 0.25)
    w_flat = weights.get('flatness', 0.20)

    total_w = w_safe + w_illum + w_prox + w_flat

    composite = (w_safe * safety_score
                 + w_illum * illum_score
                 + w_prox * prox_score
                 + w_flat * flatness_score)

    if total_w > 0:
        composite /= total_w

    # Apply hard mask
    composite[~hard_mask] = 0.0

    return np.clip(composite, 0.0, 1.0)


# =============================================================================
# FIND BEST SITES
# =============================================================================

def find_best_sites(landing_scores, n_sites=3, min_separation_pixels=50):
    """
    Extract the top *N* non-overlapping landing sites from the score map.

    A greedy approach is used: the highest-scoring pixel is selected,
    then all pixels within ``min_separation_pixels`` are masked out,
    and the process repeats.

    Parameters
    ----------
    landing_scores : np.ndarray (rows, cols)
        Landing suitability score map.
    n_sites : int, optional
        Number of sites to return.
    min_separation_pixels : int, optional
        Minimum pixel distance between selected sites.

    Returns
    -------
    list of tuple
        Each entry is ``(row, col, score)`` for a selected site,
        sorted by descending score.
    """
    scores = landing_scores.copy()
    rows, cols = scores.shape
    sites = []

    rr, cc = np.meshgrid(np.arange(rows), np.arange(cols), indexing='ij')

    for _ in range(n_sites):
        # Find global maximum
        best_idx = np.nanargmax(scores)
        best_row, best_col = np.unravel_index(best_idx, scores.shape)
        best_score = scores[best_row, best_col]

        if best_score <= 0 or np.isnan(best_score):
            break

        sites.append((int(best_row), int(best_col), float(best_score)))

        # Mask out neighbourhood
        dist_pix = np.sqrt((rr - best_row) ** 2 + (cc - best_col) ** 2)
        scores[dist_pix < min_separation_pixels] = 0.0

    return sites


# =============================================================================
# REPORT GENERATION
# =============================================================================

def generate_landing_report(sites, pixel_size, slope, illumination_frac,
                            hazard_map):
    """
    Create a human-readable text summary for each candidate landing site.

    Parameters
    ----------
    sites : list of tuple
        ``(row, col, score)`` as returned by ``find_best_sites``.
    pixel_size : float
        Ground pixel spacing in metres.
    slope : np.ndarray (rows, cols)
        Slope in degrees.
    illumination_frac : np.ndarray (rows, cols)
        Illumination fraction [0, 1].
    hazard_map : np.ndarray (rows, cols)
        Hazard score [0, 1].

    Returns
    -------
    str
        Formatted multi-site report.
    """
    lines = []
    lines.append("=" * 60)
    lines.append("  LunarIce-360  —  Landing Site Assessment Report")
    lines.append("=" * 60)
    lines.append("")

    for rank, (r, c, score) in enumerate(sites, start=1):
        easting_m = c * pixel_size
        northing_m = r * pixel_size
        site_slope = slope[r, c]
        site_illum = illumination_frac[r, c]
        site_hazard = hazard_map[r, c]

        # Local statistics (5×5 neighbourhood)
        r_lo = max(0, r - 2)
        r_hi = min(slope.shape[0], r + 3)
        c_lo = max(0, c - 2)
        c_hi = min(slope.shape[1], c + 3)

        local_slope_mean = np.nanmean(slope[r_lo:r_hi, c_lo:c_hi])
        local_slope_max = np.nanmax(slope[r_lo:r_hi, c_lo:c_hi])
        local_illum_mean = np.nanmean(
            illumination_frac[r_lo:r_hi, c_lo:c_hi])

        lines.append(f"  Site #{rank}")
        lines.append(f"  {'─' * 40}")
        lines.append(f"    Pixel coordinates  : ({r}, {c})")
        lines.append(
            f"    Ground position   : ({easting_m:.0f} m E, "
            f"{northing_m:.0f} m N)")
        lines.append(f"    Composite score   : {score:.4f}")
        lines.append(f"    Slope (centre)    : {site_slope:.2f}°")
        lines.append(
            f"    Slope (local mean): {local_slope_mean:.2f}°")
        lines.append(
            f"    Slope (local max) : {local_slope_max:.2f}°")
        lines.append(
            f"    Illumination      : {site_illum:.1%}")
        lines.append(
            f"    Illumination (local mean): {local_illum_mean:.1%}")
        lines.append(f"    Hazard score      : {site_hazard:.4f}")
        lines.append("")

    lines.append("=" * 60)
    lines.append("  End of Report")
    lines.append("=" * 60)

    return "\n".join(lines)


def select_landing_sites(dem, slope, roughness, illumination, hazard, target_center, pixel_size):
    """
    Run the full landing site selection pipeline.
    
    Parameters
    ----------
    dem : np.ndarray
        Digital Elevation Model.
    slope : np.ndarray
        Terrain slope map in degrees.
    roughness : np.ndarray
        RMS roughness map.
    illumination : np.ndarray
        Illumination fraction map.
    hazard : np.ndarray
        Hazard map.
    target_center : tuple of int
        (row, col) coordinates of target crater center.
    pixel_size : float
        Ground pixel spacing in meters.
        
    Returns
    -------
    dict
        Dictionary containing scores and candidates.
    """
    scores = score_landing_sites(slope, hazard, illumination, target_center, pixel_size)
    best_sites_coords = find_best_sites(scores, n_sites=3)
    
    best_sites = []
    for rank, (r, c, val) in enumerate(best_sites_coords):
        best_sites.append({
            'row': int(r),
            'col': int(c),
            'score': float(val),
            'label': f'Site {rank+1}'
        })
        
    return {
        'scores': scores,
        'best_sites': best_sites
    }

