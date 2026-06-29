"""
LunarIce-360: Lunar Subsurface Ice Detection & Rover Traverse Planning
=======================================================================

A complete pipeline for detecting subsurface ice in lunar south polar
permanently shadowed regions using Chandrayaan-2 DFSAR radar data,
selecting safe landing sites, planning optimal rover traverses, and
estimating ice volumes with uncertainty quantification.

Modules:
    config              - Physical constants, thresholds, parameters
    data_loader         - Load GeoTIFF, PDS, raw binary data
    preprocessing       - Speckle filtering, calibration
    polarimetry         - CPR, DOP, m-chi, H/A/alpha decomposition
    ice_detection       - GMM, Isolation Forest, fusion engine
    terrain             - Slope, roughness, illumination, hazard
    landing_site        - Multi-criteria landing site selection
    traverse            - NSGA-II rover path optimization
    roa                 - Region of Attraction and path caching
    volume_estimation   - Bayesian MCMC ice volume estimation
    visualization       - All plotting and figure generation
    demo_synthetic      - Synthetic data generation for testing
"""

__version__ = "1.0.0"
__author__ = "LunarIce-360 Team"
