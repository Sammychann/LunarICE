"""
Visualization Module for LunarIce-360.

All plotting functions for the LunarIce-360 pipeline. Each function saves
figures to the outputs/ directory and returns the matplotlib figure object.

Usage:
    from lunarice360.visualization import plot_ice_probability_map
    fig = plot_ice_probability_map(ice_prob, dem=my_dem)
"""

import os
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for saving
import matplotlib.pyplot as plt

from . import config

# Try importing corner for MCMC corner plots
try:
    import corner
    HAS_CORNER = True
except ImportError:
    HAS_CORNER = False


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def setup_output_dir():
    """Create the outputs/ directory if it does not exist.

    Uses the output directory path from config.OUTPUT_DIR.

    Returns
    -------
    str
        Absolute path to the output directory.
    """
    out = config.OUTPUT_DIR
    os.makedirs(out, exist_ok=True)
    return os.path.abspath(out)


def _save_figure(fig, save_path, default_name):
    """Internal helper to save a figure to disk.

    Parameters
    ----------
    fig : matplotlib.figure.Figure
        The figure to save.
    save_path : str or None
        Explicit path. If None, saves to OUTPUT_DIR/default_name.
    default_name : str
        Default filename (without extension).
    """
    if save_path is None:
        setup_output_dir()
        save_path = os.path.join(
            config.OUTPUT_DIR,
            f"{default_name}.{config.FIGURE_FORMAT}"
        )
    fig.savefig(save_path, dpi=config.FIGURE_DPI, bbox_inches='tight',
                facecolor=fig.get_facecolor(), edgecolor='none')
    print(f"  [VIZ] Saved: {save_path}")
    plt.close(fig)
    import gc
    gc.collect()


def _compute_hillshade(dem, azimuth=315, altitude=45):
    """Compute hillshade from a DEM for visualization backgrounds.

    Parameters
    ----------
    dem : np.ndarray
        Digital Elevation Model (2D array).
    azimuth : float
        Sun azimuth in degrees (default 315).
    altitude : float
        Sun altitude in degrees (default 45).

    Returns
    -------
    np.ndarray
        Hillshade array normalized to [0, 1].
    """
    az_rad = np.radians(azimuth)
    alt_rad = np.radians(altitude)

    # Compute gradients
    dy, dx = np.gradient(dem)
    slope = np.arctan(np.sqrt(dx**2 + dy**2))
    aspect = np.arctan2(-dy, dx)

    # Hillshade formula
    hs = (np.sin(alt_rad) * np.cos(slope) +
          np.cos(alt_rad) * np.sin(slope) * np.cos(az_rad - aspect))

    # Normalize to [0, 1]
    hs = (hs - hs.min()) / (hs.max() - hs.min() + 1e-10)
    return hs


# =============================================================================
# PRIMARY VISUALIZATION FUNCTIONS
# =============================================================================

def plot_ice_probability_map(ice_prob, dem=None,
                              title='Ice Probability Map', save_path=None):
    """Plot ice probability as a heatmap, optionally over DEM hillshade.

    Parameters
    ----------
    ice_prob : np.ndarray
        2D array of ice probabilities in [0, 1].
    dem : np.ndarray, optional
        Digital Elevation Model for hillshade background.
    title : str
        Figure title.
    save_path : str, optional
        Path to save the figure. If None, saves to outputs/.

    Returns
    -------
    matplotlib.figure.Figure
        The generated figure.
    """
    fig, ax = plt.subplots(figsize=(10, 8))

    # Show hillshade background if DEM is provided
    if dem is not None:
        hs = _compute_hillshade(dem)
        ax.imshow(hs, cmap='gray', alpha=0.6)

    # Mask low probabilities
    ice_masked = np.ma.masked_where(ice_prob <= 0.1, ice_prob)

    # Overlay ice probability heatmap
    im = ax.imshow(ice_masked, cmap=config.COLORMAP_ICE,
                   alpha=0.7, vmin=0.1, vmax=1.0)

    # Colorbar
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label('Ice Probability', fontsize=12)

    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.set_xlabel('Column (pixels)', fontsize=11)
    ax.set_ylabel('Row (pixels)', fontsize=11)
    fig.tight_layout()

    _save_figure(fig, save_path, 'ice_probability_map')
    return fig


def plot_H_alpha_plane(H, alpha, zones=None,
                       title='H/\u03b1 Classification', save_path=None):
    """Plot the H/alpha classification plane.

    Parameters
    ----------
    H : np.ndarray
        Entropy values (2D or flattened).
    alpha : np.ndarray
        Alpha angle values in degrees (2D or flattened).
    zones : np.ndarray, optional
        Zone labels for each pixel. If None, color by density.
    title : str
        Figure title.
    save_path : str, optional
        Path to save the figure.

    Returns
    -------
    matplotlib.figure.Figure
        The generated figure.
    """
    fig, ax = plt.subplots(figsize=(10, 8))

    H_flat = H.ravel()
    alpha_flat = alpha.ravel()

    # Subsample if more than 100k pixels
    n_pixels = len(H_flat)
    if n_pixels > 100000:
        idx = np.random.choice(n_pixels, 100000, replace=False)
        H_flat = H_flat[idx]
        alpha_flat = alpha_flat[idx]
        if zones is not None:
            zones_flat = zones.ravel()[idx]
        else:
            zones_flat = None
    else:
        zones_flat = zones.ravel() if zones is not None else None

    # Scatter plot
    if zones_flat is not None:
        unique_zones = np.unique(zones_flat)
        zone_names = {
            0: 'Z1: Low H, Low \u03b1',
            1: 'Z2: Low H, Med \u03b1',
            2: 'Z3: Low H, High \u03b1',
            3: 'Z4: Med H, Low \u03b1',
            4: 'Z5: Med H, Med \u03b1',
            5: 'Z6: Med H, High \u03b1',
            6: 'Z7: High H, Low \u03b1',
            7: 'Z8: High H, Med \u03b1',
            8: 'Z9: High H, High \u03b1',
        }
        colors_map = plt.cm.Set1(np.linspace(0, 1, max(9, len(unique_zones))))
        for z in unique_zones:
            mask = zones_flat == z
            label = zone_names.get(int(z), f'Zone {int(z)}')
            ax.scatter(H_flat[mask], alpha_flat[mask], s=1, alpha=0.3,
                       color=colors_map[int(z) % len(colors_map)], label=label)
        ax.legend(markerscale=8, fontsize=9, loc='upper left')
    else:
        ax.scatter(H_flat, alpha_flat, s=1, alpha=0.2,
                   c='steelblue', edgecolors='none')

    # Draw zone boundary lines
    ax.axvline(x=config.H_LOW, color='red', linestyle='--', linewidth=1.2,
               label=f'H = {config.H_LOW}')
    ax.axvline(x=config.H_HIGH, color='darkred', linestyle='--', linewidth=1.2,
               label=f'H = {config.H_HIGH}')
    ax.axhline(y=config.ALPHA_LOW, color='blue', linestyle='--', linewidth=1.2,
               label=f'\u03b1 = {config.ALPHA_LOW}\u00b0')
    ax.axhline(y=config.ALPHA_HIGH, color='darkblue', linestyle='--', linewidth=1.2,
               label=f'\u03b1 = {config.ALPHA_HIGH}\u00b0')

    # Zone labels
    ax.text(0.25, 20, 'Z1', fontsize=12, fontweight='bold', color='gray',
            ha='center', va='center', alpha=0.6)
    ax.text(0.25, 47.5, 'Z2', fontsize=12, fontweight='bold', color='gray',
            ha='center', va='center', alpha=0.6)
    ax.text(0.25, 70, 'Z3', fontsize=12, fontweight='bold', color='gray',
            ha='center', va='center', alpha=0.6)
    ax.text(0.7, 20, 'Z4', fontsize=12, fontweight='bold', color='gray',
            ha='center', va='center', alpha=0.6)
    ax.text(0.7, 47.5, 'Z5', fontsize=12, fontweight='bold', color='gray',
            ha='center', va='center', alpha=0.6)
    ax.text(0.7, 70, 'Z6', fontsize=12, fontweight='bold', color='gray',
            ha='center', va='center', alpha=0.6)
    ax.text(0.95, 20, 'Z7', fontsize=12, fontweight='bold', color='gray',
            ha='center', va='center', alpha=0.6)
    ax.text(0.95, 47.5, 'Z8', fontsize=12, fontweight='bold', color='gray',
            ha='center', va='center', alpha=0.6)
    ax.text(0.95, 70, 'Z9', fontsize=12, fontweight='bold', color='gray',
            ha='center', va='center', alpha=0.6)

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 90)
    ax.set_xlabel('Entropy (H)', fontsize=12)
    ax.set_ylabel('Alpha (\u03b1) [degrees]', fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    fig.tight_layout()

    _save_figure(fig, save_path, 'H_alpha_plane')
    return fig


def plot_decomposition_panels(Pv, Ps, Pd,
                               title='m-\u03c7 Decomposition', save_path=None):
    """Plot m-chi decomposition panels: Volume, Surface, Double-bounce.

    Parameters
    ----------
    Pv : np.ndarray
        Volume scattering power (2D).
    Ps : np.ndarray
        Surface scattering power (2D).
    Pd : np.ndarray
        Double-bounce scattering power (2D).
    title : str
        Figure title.
    save_path : str, optional
        Path to save the figure.

    Returns
    -------
    matplotlib.figure.Figure
        The generated figure.
    """
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    panels = [
        (Pv, 'Volume (Pv)', 'Reds'),
        (Ps, 'Surface (Ps)', 'Blues'),
        (Pd, 'Double-bounce (Pd)', 'Greens'),
    ]

    for ax, (data, label, cmap) in zip(axes, panels):
        im = ax.imshow(data, cmap=cmap)
        ax.set_title(label, fontsize=12, fontweight='bold')
        ax.set_xlabel('Column', fontsize=10)
        ax.set_ylabel('Row', fontsize=10)
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

    fig.suptitle(title, fontsize=14, fontweight='bold', y=1.02)
    fig.tight_layout()

    _save_figure(fig, save_path, 'decomposition_panels')
    return fig


def plot_terrain_analysis(slope, roughness, illumination, hazard,
                          title='Terrain Analysis', save_path=None):
    """Plot terrain analysis as 2x2 subplots.

    Parameters
    ----------
    slope : np.ndarray
        Slope map in degrees.
    roughness : np.ndarray
        RMS roughness map.
    illumination : np.ndarray
        Illumination fraction map.
    hazard : np.ndarray
        Combined hazard map.
    title : str
        Figure title.
    save_path : str, optional
        Path to save the figure.

    Returns
    -------
    matplotlib.figure.Figure
        The generated figure.
    """
    fig, axes = plt.subplots(2, 2, figsize=(14, 12))

    panels = [
        (slope, 'Slope (degrees)', 'RdYlGn_r'),
        (roughness, 'Roughness (RMS)', 'hot'),
        (illumination, 'Illumination Fraction', 'YlOrBr'),
        (hazard, 'Hazard Map', config.COLORMAP_HAZARD),
    ]

    for ax, (data, label, cmap) in zip(axes.ravel(), panels):
        im = ax.imshow(data, cmap=cmap)
        ax.set_title(label, fontsize=12, fontweight='bold')
        ax.set_xlabel('Column', fontsize=10)
        ax.set_ylabel('Row', fontsize=10)
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

    fig.suptitle(title, fontsize=14, fontweight='bold')
    fig.tight_layout()

    _save_figure(fig, save_path, 'terrain_analysis')
    return fig


def plot_landing_site(landing_scores, best_sites, dem=None,
                      title='Landing Site Selection', save_path=None):
    """Plot landing site score map with best sites marked.

    Parameters
    ----------
    landing_scores : np.ndarray
        2D array of landing site scores.
    best_sites : list of dict or list of tuple
        Best landing sites. Each entry should have 'row', 'col', and
        optionally 'label'/'score', or be a (row, col) tuple.
    dem : np.ndarray, optional
        DEM for hillshade background.
    title : str
        Figure title.
    save_path : str, optional
        Path to save the figure.

    Returns
    -------
    matplotlib.figure.Figure
        The generated figure.
    """
    fig, ax = plt.subplots(figsize=(10, 8))

    # Show hillshade background if DEM is provided
    if dem is not None:
        hs = _compute_hillshade(dem)
        ax.imshow(hs, cmap='gray', alpha=0.5)

    # Show landing scores
    im = ax.imshow(landing_scores, cmap='viridis', alpha=0.8)
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label('Landing Score', fontsize=12)

    # Mark best sites with star markers
    for i, site in enumerate(best_sites):
        if isinstance(site, dict):
            r, c = site.get('row', 0), site.get('col', 0)
            label = site.get('label', f'Site {i+1}')
            score = site.get('score', None)
        else:
            r, c = site[0], site[1]
            label = f'Site {i+1}'
            score = None

        ax.plot(c, r, marker='*', markersize=18, color='gold',
                markeredgecolor='black', markeredgewidth=1.5)
        label_text = label
        if score is not None:
            label_text += f' ({score:.2f})'
        ax.annotate(label_text, (c, r), textcoords='offset points',
                    xytext=(10, 10), fontsize=10, fontweight='bold',
                    color='white',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='black',
                              alpha=0.7))

    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.set_xlabel('Column (pixels)', fontsize=11)
    ax.set_ylabel('Row (pixels)', fontsize=11)
    fig.tight_layout()

    _save_figure(fig, save_path, 'landing_site')
    return fig


def plot_traverse_path(path, dem, hazard_map=None, ice_prob=None,
                       start=None, goal=None,
                       title='Rover Traverse Path', save_path=None):
    """Plot rover traverse path over DEM or hazard map.

    Parameters
    ----------
    path : np.ndarray
        Array of (row, col) waypoints defining the path.
    dem : np.ndarray
        Digital Elevation Model.
    hazard_map : np.ndarray, optional
        Hazard map to show as background instead of DEM.
    ice_prob : np.ndarray, optional
        Ice probability overlay.
    start : tuple, optional
        (row, col) of start position.
    goal : tuple, optional
        (row, col) of goal position.
    title : str
        Figure title.
    save_path : str, optional
        Path to save the figure.

    Returns
    -------
    matplotlib.figure.Figure
        The generated figure.
    """
    fig, ax = plt.subplots(figsize=(10, 8))

    # Background: hazard map or DEM hillshade
    if hazard_map is not None:
        im = ax.imshow(hazard_map, cmap=config.COLORMAP_HAZARD, alpha=0.7)
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04,
                     label='Hazard Level')
    else:
        hs = _compute_hillshade(dem)
        ax.imshow(hs, cmap='gray')

    # Optional ice overlay
    if ice_prob is not None:
        ice_masked = np.ma.masked_where(ice_prob <= 0.1, ice_prob)
        ax.imshow(ice_masked, cmap=config.COLORMAP_ICE, alpha=0.4)

    # Draw path
    path = np.array(path)
    ax.plot(path[:, 1], path[:, 0], '-', color='cyan', linewidth=2.5,
            label='Traverse Path', zorder=5)
    ax.plot(path[:, 1], path[:, 0], 'o', color='white', markersize=5,
            markeredgecolor='cyan', markeredgewidth=1, zorder=6,
            label='Waypoints')

    # Mark start and goal
    if start is not None:
        ax.plot(start[1], start[0], '^', color='lime', markersize=15,
                markeredgecolor='black', markeredgewidth=1.5, zorder=7,
                label='Start')
    if goal is not None:
        ax.plot(goal[1], goal[0], 'v', color='red', markersize=15,
                markeredgecolor='black', markeredgewidth=1.5, zorder=7,
                label='Goal')

    ax.legend(loc='upper right', fontsize=10)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.set_xlabel('Column (pixels)', fontsize=11)
    ax.set_ylabel('Row (pixels)', fontsize=11)
    fig.tight_layout()

    _save_figure(fig, save_path, 'traverse_path')
    return fig


def plot_roa(roa_mask, dem=None, hazard_map=None,
             title='Region of Attraction', save_path=None):
    """Plot the Region of Attraction mask.

    Parameters
    ----------
    roa_mask : np.ndarray
        Boolean ROA mask.
    dem : np.ndarray, optional
        Background DEM for context.
    hazard_map : np.ndarray, optional
        Background hazard map.
    title : str
        Figure title.
    save_path : str, optional
        Path to save the figure.
    """
    fig, ax = plt.subplots(figsize=(8, 8))

    if hazard_map is not None:
        ax.imshow(hazard_map, cmap=config.COLORMAP_HAZARD)
    elif dem is not None:
        hillshade = _compute_hillshade(dem)
        ax.imshow(hillshade, cmap='gray')
    else:
        ax.set_facecolor('black')

    # Overlay ROA mask
    roa_display = np.ma.masked_where(~roa_mask, roa_mask)
    ax.imshow(roa_display, cmap='autumn', alpha=0.6)

    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.set_xlabel('Column')
    ax.set_ylabel('Row')
    fig.tight_layout()

    _save_figure(fig, save_path, 'roa_mask')
    return fig


def plot_pareto_front(pareto_F, selected_idx=None,
                      title='Pareto Front', save_path=None):
    """Plot 3D Pareto front of multi-objective optimization.

    Parameters
    ----------
    pareto_F : np.ndarray
        Array of shape (N, 3) with objective values:
        [distance, hazard, shadow_fraction].
    selected_idx : int, optional
        Index of the selected solution to highlight.
    title : str
        Figure title.
    save_path : str, optional
        Path to save the figure.

    Returns
    -------
    matplotlib.figure.Figure
        The generated figure.
    """
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')

    # Plot all Pareto solutions
    ax.scatter(pareto_F[:, 0], pareto_F[:, 1], pareto_F[:, 2],
               c='steelblue', alpha=0.5, s=30, label='Pareto Solutions')

    # Highlight selected solution
    if selected_idx is not None and selected_idx < len(pareto_F):
        sel = pareto_F[selected_idx]
        ax.scatter([sel[0]], [sel[1]], [sel[2]],
                   c='red', s=200, marker='*', edgecolors='black',
                   linewidths=1.5, label='Selected Solution', zorder=10)

    ax.set_xlabel('Total Distance (m)', fontsize=11)
    ax.set_ylabel('Cumulative Hazard', fontsize=11)
    ax.set_zlabel('Shadow Fraction', fontsize=11)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.legend(fontsize=10)

    _save_figure(fig, save_path, 'pareto_front')
    return fig


def plot_energy_profile(energy_profile,
                        title='Rover Energy Profile', save_path=None):
    """Plot rover energy profile along the traverse.

    Parameters
    ----------
    energy_profile : dict
        Must contain keys:
        - 'cumulative_distance': array of cumulative distances (m)
        - 'battery_energy': array of battery energy at each step (Wh)
        - 'illuminated': boolean array (True = sunlit)
        Optionally:
        - 'battery_max': maximum battery capacity (Wh)
    title : str
        Figure title.
    save_path : str, optional
        Path to save the figure.

    Returns
    -------
    matplotlib.figure.Figure
        The generated figure.
    """
    fig, ax = plt.subplots(figsize=(12, 5))

    dist = np.asarray(energy_profile['cumulative_distance'])
    energy = np.asarray(energy_profile['battery_energy'])
    illuminated = np.asarray(energy_profile['illuminated'])
    battery_max = energy_profile.get('battery_max', config.ROVER_BATTERY_CAPACITY)

    # Color segments by illumination
    for i in range(len(dist) - 1):
        color = 'gold' if illuminated[i] else 'slategray'
        ax.plot(dist[i:i+2], energy[i:i+2], '-', color=color, linewidth=2.5)

    # Reference lines
    ax.axhline(y=0, color='red', linestyle='--', linewidth=1.5,
               label='Energy = 0 (death)', alpha=0.8)
    ax.axhline(y=battery_max, color='green', linestyle='--', linewidth=1.5,
               label=f'Battery Max ({battery_max:.0f} Wh)', alpha=0.8)

    # Legend patches for illumination
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='gold', label='Illuminated'),
        Patch(facecolor='slategray', label='Shadowed'),
        plt.Line2D([0], [0], color='red', linestyle='--', label='Energy = 0'),
        plt.Line2D([0], [0], color='green', linestyle='--',
                   label=f'Max ({battery_max:.0f} Wh)'),
    ]
    ax.legend(handles=legend_elements, fontsize=10, loc='upper right')

    ax.set_xlabel('Cumulative Distance (m)', fontsize=12)
    ax.set_ylabel('Battery Energy (Wh)', fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.set_ylim(bottom=min(-20, energy.min() - 20),
                top=battery_max * 1.1)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    _save_figure(fig, save_path, 'energy_profile')
    return fig


def plot_mcmc_corner(samples,
                     labels=None,
                     title='MCMC Posterior', save_path=None):
    """Plot MCMC posterior corner plot.

    Parameters
    ----------
    samples : np.ndarray
        MCMC samples of shape (n_samples, n_params).
    labels : list of str, optional
        Parameter labels. Defaults to standard ice parameters.
    title : str
        Figure title.
    save_path : str, optional
        Path to save the figure.

    Returns
    -------
    matplotlib.figure.Figure
        The generated figure.
    """
    if labels is None:
        labels = ['Ice Fraction', 'Roughness (cm)',
                  'Density (kg/m\u00b3)', 'Depth (m)']

    if HAS_CORNER:
        fig = corner.corner(
            samples,
            labels=labels,
            quantiles=[0.16, 0.5, 0.84],
            show_titles=True,
            title_kwargs={"fontsize": 12},
            title_fmt='.3f',
        )
        fig.suptitle(title, fontsize=14, fontweight='bold', y=1.02)
    else:
        # Fallback: simple pair plot using matplotlib
        n_params = samples.shape[1]
        fig, axes = plt.subplots(n_params, n_params,
                                 figsize=(3 * n_params, 3 * n_params))
        for i in range(n_params):
            for j in range(n_params):
                ax = axes[i, j]
                if i == j:
                    ax.hist(samples[:, i], bins=50, color='steelblue',
                            alpha=0.7, density=True)
                    q16, q50, q84 = np.percentile(samples[:, i],
                                                  [16, 50, 84])
                    ax.axvline(q50, color='red', linestyle='-')
                    ax.axvline(q16, color='red', linestyle='--', alpha=0.5)
                    ax.axvline(q84, color='red', linestyle='--', alpha=0.5)
                    ax.set_title(f'{labels[i]}\n'
                                 f'{q50:.3f}$^{{+{q84-q50:.3f}}}_'
                                 f'{{-{q50-q16:.3f}}}$',
                                 fontsize=9)
                elif i > j:
                    ax.scatter(samples[:, j], samples[:, i], s=1,
                               alpha=0.1, color='steelblue')
                else:
                    ax.set_visible(False)

                if i == n_params - 1:
                    ax.set_xlabel(labels[j], fontsize=9)
                if j == 0 and i > 0:
                    ax.set_ylabel(labels[i], fontsize=9)

        fig.suptitle(title, fontsize=14, fontweight='bold')
        fig.tight_layout()

    _save_figure(fig, save_path, 'mcmc_corner')
    return fig


def plot_volume_summary(volume_results,
                        title='Ice Volume Estimate', save_path=None):
    """Plot ice volume estimate with uncertainty.

    Parameters
    ----------
    volume_results : dict
        Must contain keys:
        - 'volume_samples' or 'volumes': array of volume samples (m\u00b3)
        Optionally:
        - 'median': median volume
        - 'ci_68_low', 'ci_68_high': 68% CI bounds
        - 'ci_95_low', 'ci_95_high': 95% CI bounds
    title : str
        Figure title.
    save_path : str, optional
        Path to save the figure.

    Returns
    -------
    matplotlib.figure.Figure
        The generated figure.
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    # Extract volume samples
    volumes = np.asarray(
        volume_results.get('volume_samples',
                           volume_results.get('volumes', []))
    )

    if len(volumes) > 0:
        # Compute statistics
        median = volume_results.get('median', np.median(volumes))
        ci_68_low = volume_results.get('ci_68_low',
                                       np.percentile(volumes, 16))
        ci_68_high = volume_results.get('ci_68_high',
                                        np.percentile(volumes, 84))
        ci_95_low = volume_results.get('ci_95_low',
                                       np.percentile(volumes, 2.5))
        ci_95_high = volume_results.get('ci_95_high',
                                        np.percentile(volumes, 97.5))

        # Histogram
        n, bins, patches = ax.hist(volumes, bins=60, color='steelblue',
                                   alpha=0.7, density=True,
                                   edgecolor='white', linewidth=0.5)

        # 68% CI shading
        mask_68 = (bins[:-1] >= ci_68_low) & (bins[1:] <= ci_68_high)
        for p, m in zip(patches, mask_68):
            if m:
                p.set_facecolor('cornflowerblue')
                p.set_alpha(0.9)

        # Median line
        ax.axvline(median, color='red', linewidth=2.5, linestyle='-',
                   label=f'Median: {median:.1f} m\u00b3')

        # CI lines
        ax.axvline(ci_68_low, color='orange', linewidth=1.5, linestyle='--',
                   label=f'68% CI: [{ci_68_low:.1f}, {ci_68_high:.1f}] m\u00b3')
        ax.axvline(ci_68_high, color='orange', linewidth=1.5, linestyle='--')
        ax.axvline(ci_95_low, color='gray', linewidth=1, linestyle=':',
                   label=f'95% CI: [{ci_95_low:.1f}, {ci_95_high:.1f}] m\u00b3')
        ax.axvline(ci_95_high, color='gray', linewidth=1, linestyle=':')

        # Annotation
        ax.annotate(
            f'Volume = {median:.1f}$^{{+{ci_68_high-median:.1f}}}'
            f'_{{-{median-ci_68_low:.1f}}}$ m\u00b3',
            xy=(0.05, 0.95), xycoords='axes fraction',
            fontsize=13, fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.4', facecolor='lightyellow',
                      alpha=0.9)
        )

        ax.legend(fontsize=10, loc='upper right')
    else:
        ax.text(0.5, 0.5, 'No volume data available',
                transform=ax.transAxes, ha='center', va='center',
                fontsize=14, color='gray')

    ax.set_xlabel('Ice Volume (m\u00b3)', fontsize=12)
    ax.set_ylabel('Probability Density', fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    fig.tight_layout()

    _save_figure(fig, save_path, 'volume_summary')
    return fig


def plot_dual_frequency(CPR_L, CPR_S,
                        title='Dual-Frequency Analysis', save_path=None):
    """Plot dual-frequency CPR analysis.

    Parameters
    ----------
    CPR_L : np.ndarray
        L-band Circular Polarization Ratio (2D).
    CPR_S : np.ndarray
        S-band Circular Polarization Ratio (2D).
    title : str
        Figure title.
    save_path : str, optional
        Path to save the figure.

    Returns
    -------
    matplotlib.figure.Figure
        The generated figure.
    """
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    # L-band CPR
    im0 = axes[0].imshow(CPR_L, cmap='inferno', vmin=0, vmax=2.0)
    axes[0].set_title('L-band CPR', fontsize=12, fontweight='bold')
    fig.colorbar(im0, ax=axes[0], fraction=0.046, pad=0.04)

    # S-band CPR
    im1 = axes[1].imshow(CPR_S, cmap='inferno', vmin=0, vmax=2.0)
    axes[1].set_title('S-band CPR', fontsize=12, fontweight='bold')
    fig.colorbar(im1, ax=axes[1], fraction=0.046, pad=0.04)

    # Differential CPR (L - S)
    diff = CPR_L - CPR_S
    im2 = axes[2].imshow(diff, cmap='RdBu_r', vmin=-1.0, vmax=1.0)
    axes[2].set_title('Differential CPR (L \u2212 S)', fontsize=12,
                       fontweight='bold')
    fig.colorbar(im2, ax=axes[2], fraction=0.046, pad=0.04)

    for ax in axes:
        ax.set_xlabel('Column', fontsize=10)
        ax.set_ylabel('Row', fontsize=10)

    fig.suptitle(title, fontsize=14, fontweight='bold', y=1.02)
    fig.tight_layout()

    _save_figure(fig, save_path, 'dual_frequency')
    return fig


def generate_summary_figure(ice_prob, hazard, path, volume_results,
                             roa_mask=None, title='LunarIce-360 Summary', save_path=None):
    """Generate master 2x2 summary figure.

    Parameters
    ----------
    ice_prob : np.ndarray
        Ice probability map (2D).
    hazard : np.ndarray
        Hazard map (2D).
    path : np.ndarray or list
        Traverse path as (row, col) waypoints.
    volume_results : dict
        Volume estimation results with 'volume_samples' or 'volumes'.
    roa_mask : np.ndarray, optional
        Region of Attraction mask.
    title : str
        Figure title.
    save_path : str, optional
        Path to save the figure.

    Returns
    -------
    matplotlib.figure.Figure
        The generated figure.
    """
    fig, axes = plt.subplots(2, 2, figsize=(16, 14))

    # Panel 1: Ice Probability Map
    ax1 = axes[0, 0]
    ice_masked = np.ma.masked_where(ice_prob <= 0.1, ice_prob)
    im1 = ax1.imshow(ice_masked, cmap=config.COLORMAP_ICE,
                     vmin=0.1, vmax=1.0)
    fig.colorbar(im1, ax=ax1, fraction=0.046, pad=0.04,
                 label='Ice Probability')
    ax1.set_title('Ice Probability', fontsize=12, fontweight='bold')

    # Panel 2: Hazard Map
    ax2 = axes[0, 1]
    im2 = ax2.imshow(hazard, cmap=config.COLORMAP_HAZARD)
    fig.colorbar(im2, ax=ax2, fraction=0.046, pad=0.04,
                 label='Hazard Level')
    ax2.set_title('Hazard Map', fontsize=12, fontweight='bold')

    # Panel 3: Traverse Path
    ax3 = axes[1, 0]
    ax3.imshow(hazard, cmap=config.COLORMAP_HAZARD, alpha=0.5)
    
    if roa_mask is not None:
        roa_display = np.ma.masked_where(~roa_mask, roa_mask)
        ax3.imshow(roa_display, cmap='spring', alpha=0.4)
        
    path_arr = np.array(path)
    ax3.plot(path_arr[:, 1], path_arr[:, 0], '-o', color='cyan',
             linewidth=2, markersize=4)
    if len(path_arr) > 0:
        ax3.plot(path_arr[0, 1], path_arr[0, 0], '^', color='lime',
                 markersize=12, markeredgecolor='black')
        ax3.plot(path_arr[-1, 1], path_arr[-1, 0], 'v', color='red',
                 markersize=12, markeredgecolor='black')
    ax3.set_title('Traverse Path', fontsize=12, fontweight='bold')

    # Panel 4: Volume Estimate Bar
    ax4 = axes[1, 1]
    volumes = np.asarray(
        volume_results.get('volume_samples',
                           volume_results.get('volumes', []))
    )
    if len(volumes) > 0:
        median_v = np.median(volumes)
        q16 = np.percentile(volumes, 16)
        q84 = np.percentile(volumes, 84)

        ax4.bar(['Ice Volume'], [median_v], color='steelblue',
                yerr=[[median_v - q16], [q84 - median_v]],
                capsize=10, error_kw={'linewidth': 2})
        ax4.set_ylabel('Volume (m\u00b3)', fontsize=12)
        ax4.set_title('Ice Volume Estimate', fontsize=12, fontweight='bold')
        ax4.annotate(
            f'{median_v:.1f}$^{{+{q84-median_v:.1f}}}'
            f'_{{-{median_v-q16:.1f}}}$ m\u00b3',
            xy=(0, median_v), xytext=(0.3, median_v * 1.15),
            fontsize=12, fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8)
        )
    else:
        ax4.text(0.5, 0.5, 'No volume data', transform=ax4.transAxes,
                 ha='center', va='center', fontsize=14, color='gray')
        ax4.set_title('Ice Volume Estimate', fontsize=12, fontweight='bold')

    fig.suptitle(title, fontsize=16, fontweight='bold')
    fig.tight_layout(rect=[0, 0, 1, 0.96])

    _save_figure(fig, save_path, 'summary_figure')
    return fig