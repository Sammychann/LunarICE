"""
Configuration & Physical Constants for LunarIce-360.

All tunable parameters, physical constants, and thresholds used
throughout the pipeline are defined here. Modify these values
to adapt the pipeline to different datasets or mission scenarios.
"""

import numpy as np

# =============================================================================
# PHYSICAL CONSTANTS
# =============================================================================

# Radar wavelengths (meters)
WAVELENGTH_L = 0.24       # L-band (~1.25 GHz)
WAVELENGTH_S = 0.12       # S-band (~2.5 GHz)

# Dielectric constants (complex: real + j*imaginary)
EPS_REGOLITH_DRY = complex(2.8, 0.014)       # Typical dry lunar regolith
EPS_ICE_25K = complex(3.12, 0.0003)           # Water ice at 25 Kelvin
EPS_ICE_100K = complex(3.15, 0.001)           # Water ice at 100 Kelvin
EPS_BASALT = complex(7.0, 0.14)              # Basaltic rock

# Ice density (kg/m³)
ICE_DENSITY = 917.0

# Regolith properties
REGOLITH_DENSITY_MIN = 1200.0   # kg/m³
REGOLITH_DENSITY_MAX = 1900.0   # kg/m³
REGOLITH_DENSITY_TYPICAL = 1500.0
REGOLITH_POROSITY = 0.5         # Typical porosity (fraction)

# Radar penetration depths in dry regolith (approximate, meters)
PENETRATION_L_BAND = 4.0        # L-band: 3-5 m
PENETRATION_S_BAND = 1.5        # S-band: 1-2 m

# =============================================================================
# ICE DETECTION THRESHOLDS
# =============================================================================

# Primary thresholds (Sinha et al. 2026)
CPR_ICE_THRESHOLD = 1.0         # CPR > 1.0 indicates volume scattering
DOP_ICE_THRESHOLD = 0.13        # DOP < 0.13 indicates depolarized scattering

# H/A/alpha zone boundaries (Cloude-Pottier classification)
H_LOW = 0.5                     # Low/Medium entropy boundary
H_HIGH = 0.9                    # Medium/High entropy boundary
ALPHA_LOW = 40.0                # degrees — surface/dipole boundary
ALPHA_HIGH = 55.0               # degrees — dipole/double-bounce boundary

# ML parameters
GMM_N_CLUSTERS = 5              # Number of GMM clusters
ISOLATION_FOREST_CONTAMINATION = 0.10  # Expected anomaly fraction

# Ice detection fusion weights
FUSION_WEIGHTS = {
    'gmm': 0.35,
    'anomaly': 0.25,
    'threshold': 0.20,
    'h_alpha_zone': 0.20
}

# Minimum cluster size (pixels) to be considered a valid ice detection
MIN_ICE_CLUSTER_PIXELS = 5

# =============================================================================
# PREPROCESSING PARAMETERS
# =============================================================================

SPECKLE_FILTER_WINDOW = 7       # Lee filter window size (pixels)
SPATIAL_AVERAGING_WINDOW = 7    # Window for coherency matrix estimation

# =============================================================================
# TERRAIN & LANDING PARAMETERS
# =============================================================================

# Slope thresholds (degrees)
LANDING_MAX_SLOPE = 10.0        # Maximum slope for landing
ROVER_MAX_SLOPE = 20.0          # Maximum slope rover can traverse

# Roughness
ROUGHNESS_WINDOW = 11           # Window size for RMS roughness (pixels)

# Landing site scoring weights
LANDING_WEIGHTS = {
    'safety': 0.30,
    'illumination': 0.25,
    'proximity': 0.25,
    'flatness': 0.20
}

# Ideal landing distance from ice target (meters)
LANDING_IDEAL_DISTANCE = 3000.0
LANDING_DISTANCE_SIGMA = 2000.0  # Gaussian falloff parameter

# Illumination
ILLUMINATION_MIN_FRACTION = 0.40  # Minimum illumination for landing
SUN_ELEVATION_RANGE = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]  # degrees
N_AZIMUTH_STEPS = 36             # Steps for full 360° sweep

# =============================================================================
# ROVER SPECIFICATIONS
# =============================================================================

ROVER_SPEED = 0.05              # m/s (50 mm/s — typical lunar rover)
ROVER_SOLAR_POWER = 100.0       # Watts from solar panel (when illuminated)
ROVER_LOCOMOTION_POWER = 50.0   # Watts base locomotion consumption
ROVER_BATTERY_CAPACITY = 500.0  # Watt-hours
ROVER_COMM_RANGE = 5000.0       # meters (max distance from lander)

# =============================================================================
# NSGA-II PATH PLANNING PARAMETERS
# =============================================================================

NSGA2_POP_SIZE = 100            # Population size
NSGA2_N_OFFSPRINGS = 50         # Offspring per generation
NSGA2_N_GENERATIONS = 200       # Number of generations
NSGA2_N_WAYPOINTS = 8           # Intermediate waypoints in path

# =============================================================================
# BAYESIAN MCMC PARAMETERS
# =============================================================================

MCMC_N_WALKERS = 32             # Number of MCMC walkers
MCMC_N_STEPS = 5000             # Total MCMC steps
MCMC_BURN_IN = 1000             # Burn-in steps to discard
MCMC_THIN = 15                  # Thinning factor

# Prior bounds for MCMC parameters
PRIOR_ICE_FRACTION = (0.01, 0.40)       # 1% to 40%
PRIOR_ROUGHNESS_CM = (0.1, 5.0)         # 0.1 to 5 cm
PRIOR_DENSITY = (1200.0, 1900.0)        # kg/m³
PRIOR_DEPTH = (0.5, 5.0)               # meters

# MCMC initial guess
MCMC_INITIAL_GUESS = np.array([0.08, 1.0, 1500.0, 2.5])
MCMC_INITIAL_SPREAD = np.array([0.03, 0.5, 100.0, 1.0])

# Measurement uncertainties
SIGMA_CPR = 0.15                # CPR measurement uncertainty
SIGMA_SIGMA0 = 2.0             # sigma0 uncertainty in dB

# =============================================================================
# VISUALIZATION PARAMETERS
# =============================================================================

FIGURE_DPI = 150
FIGURE_FORMAT = 'png'
COLORMAP_ICE = 'YlOrRd'
COLORMAP_TERRAIN = 'terrain'
COLORMAP_HAZARD = 'RdYlGn_r'

# =============================================================================
# OUTPUT DIRECTORY
# =============================================================================

OUTPUT_DIR = 'outputs'

# =============================================================================
# DATA PATHS (FOR REAL DATASETS)
# =============================================================================
# Set these paths to point to your downloaded GeoTIFF or PDS (.IMG) files.
# By default, the pipeline expects them in a 'data/' directory inside the workspace.

import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_DIR = os.path.dirname(BASE_DIR)

DATA_DIR = os.path.join(WORKSPACE_DIR, 'data')

# L-band Stokes parameter paths
L_BAND_S1 = os.path.join(DATA_DIR, 'dfsar', 'L_band', 'S1.tif')
L_BAND_S2 = os.path.join(DATA_DIR, 'dfsar', 'L_band', 'S2.tif')
L_BAND_S3 = os.path.join(DATA_DIR, 'dfsar', 'L_band', 'S3.tif')
L_BAND_S4 = os.path.join(DATA_DIR, 'dfsar', 'L_band', 'S4.tif')

# S-band Stokes parameter paths
S_BAND_S1 = os.path.join(DATA_DIR, 'dfsar', 'S_band', 'S1.tif')
S_BAND_S2 = os.path.join(DATA_DIR, 'dfsar', 'S_band', 'S2.tif')
S_BAND_S3 = os.path.join(DATA_DIR, 'dfsar', 'S_band', 'S3.tif')
S_BAND_S4 = os.path.join(DATA_DIR, 'dfsar', 'S_band', 'S4.tif')

# DEM path
DEM_PATH = os.path.join(DATA_DIR, 'dem', 'dem.tif')

# Target center coordinates in pixels (row, col) for landing site / rover path planning.
# Update this to match the crater/region of interest in your downloaded spatial grid.
TARGET_CENTER_PIXELS = (250, 250)

