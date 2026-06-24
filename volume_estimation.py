"""
Bayesian MCMC Ice Volume Estimation.

This module implements a Bayesian framework for estimating subsurface
ice volume in lunar permanently shadowed regions. It combines:
    - Dielectric mixing models (Maxwell-Garnett, Bruggeman)
    - A simplified radar forward model for CPR and sigma0
    - MCMC posterior sampling via the emcee ensemble sampler

The inferred ice fraction and depth, combined with crater geometry,
yield volumetric ice estimates with full uncertainty quantification.
"""

import numpy as np
import emcee

from . import config


# =============================================================================
# DIELECTRIC MODELS
# =============================================================================

def density_to_permittivity(density_kgm3):
    """
    Convert regolith bulk density to complex permittivity.

    Uses the Olhoeft & Strangway (1975) empirical relation for
    lunar regolith, where the real part depends on density and
    the imaginary part is a small fraction of the real part.

    Parameters
    ----------
    density_kgm3 : float
        Bulk density of the regolith in kg/m³.

    Returns
    -------
    complex
        Complex relative permittivity (eps_real + j*eps_imag).

    References
    ----------
    Olhoeft, G. R. & Strangway, D. W. (1975). Dielectric properties
    of the first 100 meters of the Moon. Earth Planet. Sci. Lett.
    """
    rho_gcc = density_kgm3 / 1000.0  # Convert to g/cm³
    eps_real = (1.919 * rho_gcc) ** 2
    eps_imag = 0.005 * eps_real
    return complex(eps_real, eps_imag)


def maxwell_garnett(eps_host, eps_inclusion, f_vol):
    """
    Maxwell-Garnett effective medium approximation.

    Computes the effective permittivity of a two-phase mixture where
    spherical inclusions (e.g., ice) are embedded in a host medium
    (e.g., regolith). Valid for dilute to moderate inclusion fractions.

    Parameters
    ----------
    eps_host : complex
        Complex permittivity of the host medium.
    eps_inclusion : complex
        Complex permittivity of the inclusion material.
    f_vol : float
        Volume fraction of the inclusion phase (0 to 1).

    Returns
    -------
    complex
        Effective complex permittivity of the mixture.

    References
    ----------
    Sihvola, A. (1999). Electromagnetic Mixing Formulas and Applications.
    """
    eps_h = complex(eps_host)
    eps_i = complex(eps_inclusion)
    f = float(f_vol)

    numerator = eps_i + 2 * eps_h + 2 * f * (eps_i - eps_h)
    denominator = eps_i + 2 * eps_h - f * (eps_i - eps_h)

    eps_eff = eps_h * (numerator / denominator)
    return eps_eff


def bruggeman(eps_a, eps_b, f_b, tol=1e-8, max_iter=100):
    """
    Bruggeman effective medium approximation (iterative solution).

    Solves the symmetric Bruggeman equation for a two-phase mixture
    using Newton iteration. Unlike Maxwell-Garnett, this model treats
    both phases equivalently and is valid at higher volume fractions.

    The implicit equation solved is:
        f_a * (eps_a - eps_eff) / (eps_a + 2*eps_eff)
      + f_b * (eps_b - eps_eff) / (eps_b + 2*eps_eff) = 0

    Parameters
    ----------
    eps_a : complex
        Complex permittivity of phase A (e.g., regolith).
    eps_b : complex
        Complex permittivity of phase B (e.g., ice).
    f_b : float
        Volume fraction of phase B (0 to 1).
    tol : float, optional
        Convergence tolerance (default: 1e-8).
    max_iter : int, optional
        Maximum number of Newton iterations (default: 100).

    Returns
    -------
    complex
        Effective complex permittivity of the mixture.
    """
    eps_a = complex(eps_a)
    eps_b = complex(eps_b)
    f_a = 1.0 - f_b
    f_b = float(f_b)

    # Initial guess: linear mixing
    eps_eff = f_a * eps_a + f_b * eps_b

    for _ in range(max_iter):
        # Bruggeman function: F(eps_eff) = 0
        term_a = f_a * (eps_a - eps_eff) / (eps_a + 2.0 * eps_eff)
        term_b = f_b * (eps_b - eps_eff) / (eps_b + 2.0 * eps_eff)
        F = term_a + term_b

        # Derivative dF/d(eps_eff) via quotient rule
        dterm_a = f_a * (
            -1.0 * (eps_a + 2.0 * eps_eff) - (eps_a - eps_eff) * 2.0
        ) / (eps_a + 2.0 * eps_eff) ** 2
        dterm_b = f_b * (
            -1.0 * (eps_b + 2.0 * eps_eff) - (eps_b - eps_eff) * 2.0
        ) / (eps_b + 2.0 * eps_eff) ** 2
        dF = dterm_a + dterm_b

        if abs(dF) < 1e-30:
            break

        # Newton update
        eps_eff = eps_eff - F / dF

        if abs(F) < tol:
            break

    return eps_eff


# =============================================================================
# RADAR FORWARD MODEL
# =============================================================================

def radar_forward_model(f_ice, roughness_cm, density_kgm3, depth_m,
                        wavelength=None, incidence_deg=35.0):
    """
    Predict radar observables (CPR, sigma0) given subsurface ice parameters.

    Combines a dielectric mixing model with a simplified surface/volume
    scattering model to predict the Circular Polarization Ratio (CPR)
    and normalized radar cross-section (sigma0).

    Parameters
    ----------
    f_ice : float
        Volume fraction of ice in the regolith (0 to 1).
    roughness_cm : float
        Surface RMS roughness in centimeters.
    density_kgm3 : float
        Bulk density of the regolith in kg/m³.
    depth_m : float
        Depth of the ice-bearing layer in meters.
    wavelength : float, optional
        Radar wavelength in meters (default: from config.WAVELENGTH_L).
    incidence_deg : float, optional
        Radar incidence angle in degrees (default: 35.0).

    Returns
    -------
    predicted_CPR : float
        Predicted Circular Polarization Ratio.
    predicted_sigma0 : float
        Predicted normalized radar cross-section in dB.
    """
    if wavelength is None:
        wavelength = config.WAVELENGTH_L

    # Compute effective permittivity of ice-regolith mixture
    eps_regolith = density_to_permittivity(density_kgm3)
    eps_ice = config.EPS_ICE_100K
    eps_eff = maxwell_garnett(eps_regolith, eps_ice, f_ice)

    # Fresnel reflection coefficient at normal incidence (simplified)
    sqrt_eps = np.sqrt(eps_eff.real)
    R_surface = ((sqrt_eps - 1.0) / (sqrt_eps + 1.0)) ** 2

    # Roughness parameter: Rayleigh criterion
    roughness_m = roughness_cm / 100.0
    ks = 2.0 * np.pi * roughness_m / wavelength  # roughness wave parameter

    # Surface scattering contribution (Hagfors-like)
    incidence_rad = np.deg2rad(incidence_deg)
    cos_inc = np.cos(incidence_rad)
    sigma_surface = R_surface * cos_inc ** 2 * np.exp(-ks ** 2)

    # Volume scattering from ice inclusions
    # Proportional to ice fraction, depth, and 1/wavelength
    sigma_volume = (
        f_ice * depth_m * (2.0 * np.pi / wavelength) ** 2
        * 0.01  # calibration factor
    )

    # Two-way attenuation through regolith
    tan_delta = eps_eff.imag / max(eps_eff.real, 1e-10)
    attenuation = np.exp(
        -4.0 * np.pi * depth_m * np.sqrt(eps_eff.real) * tan_delta / wavelength
    )
    sigma_volume *= attenuation

    # Total backscatter
    sigma_total = sigma_surface + sigma_volume

    # CPR model:
    # Surface scattering produces CPR ~ 0 (same-sense dominated)
    # Volume scattering produces CPR > 1 (opposite-sense dominated)
    if sigma_total > 0:
        cpr_surface = 0.1 * sigma_surface / sigma_total
        cpr_volume = 1.5 * sigma_volume / sigma_total
        predicted_CPR = cpr_surface + cpr_volume + 0.2  # baseline CPR
    else:
        predicted_CPR = 0.2

    # sigma0 in dB
    predicted_sigma0 = 10.0 * np.log10(max(sigma_total, 1e-30))

    return float(predicted_CPR), float(predicted_sigma0)


# =============================================================================
# BAYESIAN INFERENCE
# =============================================================================

def log_prior(theta):
    """
    Compute log prior probability for MCMC parameters.

    Applies uniform priors within configured bounds for all parameters,
    with an additional weak Gaussian prior on ice fraction centered
    at 0.06 to encode expected low concentrations.

    Parameters
    ----------
    theta : array-like
        Parameter vector [f_ice, roughness_cm, density_kgm3, depth_m].

    Returns
    -------
    float
        Log prior probability. Returns -inf if any parameter is
        outside its allowed bounds.
    """
    f_ice, roughness, density, depth = theta

    # Uniform prior bounds from config
    if not (config.PRIOR_ICE_FRACTION[0] <= f_ice <= config.PRIOR_ICE_FRACTION[1]):
        return -np.inf
    if not (config.PRIOR_ROUGHNESS_CM[0] <= roughness <= config.PRIOR_ROUGHNESS_CM[1]):
        return -np.inf
    if not (config.PRIOR_DENSITY[0] <= density <= config.PRIOR_DENSITY[1]):
        return -np.inf
    if not (config.PRIOR_DEPTH[0] <= depth <= config.PRIOR_DEPTH[1]):
        return -np.inf

    # Weak Gaussian prior on ice fraction (centered at 0.06)
    lp = -0.5 * ((f_ice - 0.06) / 0.10) ** 2

    return lp


def log_likelihood(theta, observed_CPR, observed_sigma0):
    """
    Compute log likelihood of observed data given model parameters.

    Uses a chi-squared formulation comparing forward model predictions
    to observed CPR and sigma0 values, with measurement uncertainties
    from config.

    Parameters
    ----------
    theta : array-like
        Parameter vector [f_ice, roughness_cm, density_kgm3, depth_m].
    observed_CPR : float
        Measured Circular Polarization Ratio.
    observed_sigma0 : float
        Measured normalized radar cross-section in dB.

    Returns
    -------
    float
        Log likelihood value.
    """
    f_ice, roughness, density, depth = theta

    # Forward model prediction
    predicted_CPR, predicted_sigma0 = radar_forward_model(
        f_ice, roughness, density, depth
    )

    # Chi-squared log-likelihood
    chi2_cpr = ((observed_CPR - predicted_CPR) / config.SIGMA_CPR) ** 2
    chi2_sigma0 = ((observed_sigma0 - predicted_sigma0) / config.SIGMA_SIGMA0) ** 2

    return -0.5 * (chi2_cpr + chi2_sigma0)


def log_posterior(theta, observed_CPR, observed_sigma0):
    """
    Compute log posterior probability (prior + likelihood).

    Parameters
    ----------
    theta : array-like
        Parameter vector [f_ice, roughness_cm, density_kgm3, depth_m].
    observed_CPR : float
        Measured Circular Polarization Ratio.
    observed_sigma0 : float
        Measured normalized radar cross-section in dB.

    Returns
    -------
    float
        Log posterior probability. Returns -inf if prior rejects the
        parameter values.
    """
    lp = log_prior(theta)
    if not np.isfinite(lp):
        return -np.inf
    return lp + log_likelihood(theta, observed_CPR, observed_sigma0)


# =============================================================================
# MCMC SAMPLING
# =============================================================================

def run_mcmc(observed_CPR, observed_sigma0,
             n_walkers=None, n_steps=None, burn_in=None, thin=None):
    """
    Run MCMC posterior sampling using emcee EnsembleSampler.

    Initializes walkers around the configured initial guess with
    small random perturbations, then runs the affine-invariant
    ensemble sampler. After burn-in removal and thinning, returns
    summary statistics for ice fraction and depth.

    Parameters
    ----------
    observed_CPR : float
        Measured Circular Polarization Ratio.
    observed_sigma0 : float
        Measured normalized radar cross-section in dB.
    n_walkers : int, optional
        Number of MCMC walkers (default: from config).
    n_steps : int, optional
        Total number of MCMC steps (default: from config).
    burn_in : int, optional
        Number of burn-in steps to discard (default: from config).
    thin : int, optional
        Thinning factor for chain (default: from config).

    Returns
    -------
    dict
        Dictionary containing:
            - 'samples'   : np.ndarray — flat chain after burn-in/thinning,
                            shape (n_samples, 4)
            - 'sampler'   : emcee.EnsembleSampler — the sampler object
            - 'f_ice'     : dict with keys 'median', 'mean', 'std',
                            'ci_16', 'ci_84'
            - 'depth'     : dict with keys 'median', 'mean', 'std',
                            'ci_16', 'ci_84'
    """
    # Use config defaults if not specified
    if n_walkers is None:
        n_walkers = config.MCMC_N_WALKERS
    if n_steps is None:
        n_steps = config.MCMC_N_STEPS
    if burn_in is None:
        burn_in = config.MCMC_BURN_IN
    if thin is None:
        thin = config.MCMC_THIN

    ndim = len(config.MCMC_INITIAL_GUESS)

    # Initialize walkers with small random perturbations
    initial_guess = config.MCMC_INITIAL_GUESS
    spread = config.MCMC_INITIAL_SPREAD
    p0 = np.array([
        initial_guess + spread * np.random.randn(ndim) * 0.1
        for _ in range(n_walkers)
    ])

    # Clip initial positions to prior bounds
    p0[:, 0] = np.clip(p0[:, 0], config.PRIOR_ICE_FRACTION[0],
                        config.PRIOR_ICE_FRACTION[1])
    p0[:, 1] = np.clip(p0[:, 1], config.PRIOR_ROUGHNESS_CM[0],
                        config.PRIOR_ROUGHNESS_CM[1])
    p0[:, 2] = np.clip(p0[:, 2], config.PRIOR_DENSITY[0],
                        config.PRIOR_DENSITY[1])
    p0[:, 3] = np.clip(p0[:, 3], config.PRIOR_DEPTH[0],
                        config.PRIOR_DEPTH[1])

    # Create sampler and run MCMC
    sampler = emcee.EnsembleSampler(
        n_walkers, ndim, log_posterior,
        args=(observed_CPR, observed_sigma0),
    )
    sampler.run_mcmc(p0, n_steps, progress=True)

    # Extract flat chain with burn-in removal and thinning
    samples = sampler.get_chain(discard=burn_in, thin=thin, flat=True)

    # Compute summary statistics
    f_ice_samples = samples[:, 0]
    depth_samples = samples[:, 3]

    results = {
        'samples': samples,
        'sampler': sampler,
        'f_ice': {
            'median': float(np.median(f_ice_samples)),
            'mean': float(np.mean(f_ice_samples)),
            'std': float(np.std(f_ice_samples)),
            'ci_16': float(np.percentile(f_ice_samples, 16)),
            'ci_84': float(np.percentile(f_ice_samples, 84)),
        },
        'depth': {
            'median': float(np.median(depth_samples)),
            'mean': float(np.mean(depth_samples)),
            'std': float(np.std(depth_samples)),
            'ci_16': float(np.percentile(depth_samples, 16)),
            'ci_84': float(np.percentile(depth_samples, 84)),
        },
    }

    return results


# =============================================================================
# ICE VOLUME CALCULATION
# =============================================================================

def calculate_ice_volume(mcmc_results, crater_area_m2):
    """
    Calculate ice volume and water mass from MCMC posterior samples.

    For each MCMC sample, computes the ice volume as:
        V_ice = f_ice × area × depth

    Returns low (16th percentile), median (50th), and high (84th)
    estimates for both volume and equivalent water mass.

    Parameters
    ----------
    mcmc_results : dict
        Output from run_mcmc containing 'samples' array.
    crater_area_m2 : float
        Surface area of the crater/region of interest in m².

    Returns
    -------
    dict
        Dictionary containing:
            - 'ice_volume_m3' : dict with 'low', 'median', 'high'
            - 'water_mass_kg' : dict with 'low', 'median', 'high'
            - 'all_volumes'   : np.ndarray — full distribution for plotting
    """
    samples = mcmc_results['samples']
    f_ice = samples[:, 0]     # ice volume fraction
    depth = samples[:, 3]     # depth in meters

    # Volume of ice = fraction × area × depth
    all_volumes = f_ice * crater_area_m2 * depth

    # Water mass = ice volume × ice density
    all_masses = all_volumes * config.ICE_DENSITY

    volume_low = float(np.percentile(all_volumes, 16))
    volume_median = float(np.median(all_volumes))
    volume_high = float(np.percentile(all_volumes, 84))

    mass_low = float(np.percentile(all_masses, 16))
    mass_median = float(np.median(all_masses))
    mass_high = float(np.percentile(all_masses, 84))

    return {
        'ice_volume_m3': {
            'low': volume_low,
            'median': volume_median,
            'high': volume_high,
        },
        'water_mass_kg': {
            'low': mass_low,
            'median': mass_median,
            'high': mass_high,
        },
        'all_volumes': all_volumes,
    }


# =============================================================================
# MIXING MODEL COMPARISON
# =============================================================================

def compare_mixing_models(observed_CPR, f_ice_range=None):
    """
    Compare Maxwell-Garnett and Bruggeman mixing models over a range
    of ice fractions.

    Useful for visualizing how the two dielectric mixing models diverge
    at higher ice concentrations and how each predicts CPR.

    Parameters
    ----------
    observed_CPR : float
        Measured CPR value for reference.
    f_ice_range : np.ndarray, optional
        Array of ice volume fractions to evaluate (default: 0.01 to 0.3,
        50 points).

    Returns
    -------
    dict
        Dictionary containing:
            - 'f_values'     : np.ndarray — ice fraction values
            - 'cpr_mg'       : np.ndarray — CPR from Maxwell-Garnett model
            - 'cpr_bg'       : np.ndarray — CPR from Bruggeman model
            - 'observed_CPR' : float — the input observed CPR for reference
    """
    if f_ice_range is None:
        f_ice_range = np.linspace(0.01, 0.3, 50)

    cpr_mg = np.zeros_like(f_ice_range)
    cpr_bg = np.zeros_like(f_ice_range)

    # Reference parameters for comparison
    density = config.REGOLITH_DENSITY_TYPICAL
    roughness = 1.0      # cm
    depth = 2.5           # m
    eps_regolith = density_to_permittivity(density)
    eps_ice = config.EPS_ICE_100K

    for i, f_ice in enumerate(f_ice_range):
        # Maxwell-Garnett CPR
        cpr_mg[i], _ = radar_forward_model(
            f_ice, roughness, density, depth
        )

        # Bruggeman: compute eps_eff, then use same radar model structure
        eps_eff_bg = bruggeman(eps_regolith, eps_ice, f_ice)

        # Simplified CPR from Bruggeman eps_eff
        sqrt_eps = np.sqrt(eps_eff_bg.real)
        R_surface = ((sqrt_eps - 1.0) / (sqrt_eps + 1.0)) ** 2
        roughness_m = roughness / 100.0
        ks = 2.0 * np.pi * roughness_m / config.WAVELENGTH_L
        sigma_surface = R_surface * np.cos(np.deg2rad(35.0)) ** 2 * np.exp(-ks ** 2)

        sigma_volume = (
            f_ice * depth * (2.0 * np.pi / config.WAVELENGTH_L) ** 2 * 0.01
        )
        tan_delta = eps_eff_bg.imag / max(eps_eff_bg.real, 1e-10)
        attenuation = np.exp(
            -4.0 * np.pi * depth * np.sqrt(eps_eff_bg.real)
            * tan_delta / config.WAVELENGTH_L
        )
        sigma_volume *= attenuation
        sigma_total = sigma_surface + sigma_volume

        if sigma_total > 0:
            cpr_bg[i] = (
                0.1 * sigma_surface / sigma_total
                + 1.5 * sigma_volume / sigma_total
                + 0.2
            )
        else:
            cpr_bg[i] = 0.2

    return {
        'f_values': f_ice_range,
        'cpr_mg': cpr_mg,
        'cpr_bg': cpr_bg,
        'observed_CPR': observed_CPR,
    }


def estimate_ice_volume(ice_prob, CPR_L, dem, pixel_size, sigma0_L=None):
    """
    Run MCMC and calculate the ice volume.
    
    Parameters
    ----------
    ice_prob : np.ndarray
        Ice probability map.
    CPR_L : np.ndarray
        L-band CPR.
    dem : np.ndarray
        Digital Elevation Model.
    pixel_size : float
        Ground pixel spacing in meters.
    sigma0_L : np.ndarray, optional
        L-band sigma0 in dB. If None, assumes a typical value.
        
    Returns
    -------
    dict
        Dictionary containing volume estimate summary statistics.
    """
    # 1. Define ice mask
    ice_mask = ice_prob > 0.5
    if not np.any(ice_mask):
        # Fallback if no ice detected: use a small central region
        rows, cols = ice_prob.shape
        ice_mask = np.zeros_like(ice_prob, dtype=bool)
        ice_mask[rows//2-10:rows//2+10, cols//2-10:cols//2+10] = True
        
    # 2. Get observed values
    observed_CPR = float(np.mean(CPR_L[ice_mask]))
    
    if sigma0_L is not None:
        observed_sigma0 = float(np.mean(sigma0_L[ice_mask]))
    else:
        # Typical lunar backscatter in L-band is around -10 to -15 dB
        observed_sigma0 = -12.0
        
    # 3. Run MCMC
    mcmc_results = run_mcmc(observed_CPR, observed_sigma0)
    
    # 4. Calculate volume
    ice_area_m2 = float(np.sum(ice_mask)) * pixel_size**2
    volume_results = calculate_ice_volume(mcmc_results, ice_area_m2)
    
    volume_samples = volume_results['all_volumes']
    
    res = {
        'volume_samples': volume_samples,
        'mcmc_samples': mcmc_results['samples'],
        'median': volume_results['ice_volume_m3']['median'],
        'ci_68_low': volume_results['ice_volume_m3']['low'],
        'ci_68_high': volume_results['ice_volume_m3']['high'],
        'ci_95_low': float(np.percentile(volume_samples, 2.5)),
        'ci_95_high': float(np.percentile(volume_samples, 97.5)),
        'ice_area_m2': ice_area_m2,
        'water_mass_kg': volume_results['water_mass_kg'],
        'ice_volume_m3': volume_results['ice_volume_m3'],
    }
    
    return res

