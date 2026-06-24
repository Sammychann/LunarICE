"""
Data Loader Module for LunarIce-360.

Provides functions to load radar imagery (GeoTIFF, PDS/IMG),
multi-channel Stokes parameter data, DEMs, and utilities for
computing Stokes parameters from complex E-field components.

Supported formats:
    - GeoTIFF  (via rasterio)
    - PDS/IMG  (via GDAL)
"""

import numpy as np

try:
    import rasterio
except ImportError:
    rasterio = None

try:
    from osgeo import gdal
    gdal.UseExceptions()
except ImportError:
    gdal = None

from . import config


# =============================================================================
# GeoTIFF / PDS Loaders
# =============================================================================

def load_geotiff(filepath):
    """Load a single- or multi-band GeoTIFF file.

    Parameters
    ----------
    filepath : str or pathlib.Path
        Path to the GeoTIFF file.

    Returns
    -------
    data_array : numpy.ndarray
        Image data.  Shape is (rows, cols) for single-band files
        or (bands, rows, cols) for multi-band files.
    profile : dict
        Rasterio dataset profile (driver, dtype, CRS, etc.).
    transform : affine.Affine
        Affine geotransform mapping pixel coords to CRS coords.

    Raises
    ------
    ImportError
        If *rasterio* is not installed.
    FileNotFoundError
        If *filepath* does not exist.
    """
    if rasterio is None:
        raise ImportError(
            "rasterio is required for load_geotiff. "
            "Install it with: pip install rasterio"
        )

    try:
        with rasterio.open(filepath) as src:
            data_array = src.read()          # shape: (bands, rows, cols)
            profile = dict(src.profile)
            transform = src.transform

        # Squeeze to 2-D if single band
        if data_array.shape[0] == 1:
            data_array = data_array.squeeze(axis=0)

        print(f"[data_loader] Loaded GeoTIFF: {filepath}")
        print(f"  Shape: {data_array.shape}  |  dtype: {data_array.dtype}")
        return data_array, profile, transform

    except FileNotFoundError:
        raise FileNotFoundError(f"GeoTIFF file not found: {filepath}")
    except Exception as e:
        raise RuntimeError(f"Error loading GeoTIFF '{filepath}': {e}") from e


def load_pds(filepath):
    """Load a PDS/IMG format file using GDAL.

    Parameters
    ----------
    filepath : str or pathlib.Path
        Path to the PDS/IMG file.

    Returns
    -------
    data_array : numpy.ndarray
        Image data.  Shape is (rows, cols) for single-band or
        (bands, rows, cols) for multi-band.
    geotransform : tuple of float
        GDAL-style geotransform (originX, pixelW, 0, originY, 0, pixelH).
    projection : str
        WKT projection string (may be empty for some PDS products).

    Raises
    ------
    ImportError
        If GDAL/osgeo is not installed.
    FileNotFoundError
        If *filepath* does not exist.
    """
    if gdal is None:
        raise ImportError(
            "GDAL (osgeo) is required for load_pds. "
            "Install it with: pip install gdal"
        )

    try:
        ds = gdal.Open(str(filepath))
        if ds is None:
            raise FileNotFoundError(
                f"GDAL could not open PDS/IMG file: {filepath}"
            )

        n_bands = ds.RasterCount
        geotransform = ds.GetGeoTransform()
        projection = ds.GetProjection()

        if n_bands == 1:
            data_array = ds.GetRasterBand(1).ReadAsArray().astype(np.float64)
        else:
            data_array = np.stack(
                [ds.GetRasterBand(i + 1).ReadAsArray().astype(np.float64)
                 for i in range(n_bands)],
                axis=0,
            )

        ds = None  # close dataset

        print(f"[data_loader] Loaded PDS/IMG: {filepath}")
        print(f"  Shape: {data_array.shape}  |  Bands: {n_bands}")
        return data_array, geotransform, projection

    except FileNotFoundError:
        raise
    except Exception as e:
        raise RuntimeError(f"Error loading PDS file '{filepath}': {e}") from e


# =============================================================================
# Stokes Parameter Loading
# =============================================================================

def load_stokes_channels(s1_path, s2_path, s3_path, s4_path,
                         file_format='geotiff'):
    """Load all four Stokes parameter channels from separate files.

    Parameters
    ----------
    s1_path, s2_path, s3_path, s4_path : str
        File paths for the S1, S2, S3, and S4 channels respectively.
    file_format : {'geotiff', 'pds'}, default 'geotiff'
        Format of the input files.

    Returns
    -------
    stokes : dict
        Dictionary with keys ``'S1'``, ``'S2'``, ``'S3'``, ``'S4'``,
        each mapping to a 2-D ``numpy.ndarray``.

    Raises
    ------
    ValueError
        If *file_format* is not recognised, or if channel shapes
        do not match.
    """
    loader = _get_loader(file_format)

    try:
        paths = {'S1': s1_path, 'S2': s2_path, 'S3': s3_path, 'S4': s4_path}
        stokes = {}

        for key, path in paths.items():
            result = loader(path)
            data = result[0]  # first element is always the data array
            # Ensure 2-D
            if data.ndim > 2:
                data = data[0]
            stokes[key] = data.astype(np.float64)

        # Validate matching shapes
        shapes = {k: v.shape for k, v in stokes.items()}
        unique_shapes = set(shapes.values())
        if len(unique_shapes) > 1:
            raise ValueError(
                f"Stokes channel shapes do not match: {shapes}"
            )

        print(f"[data_loader] Loaded Stokes channels — shape: "
              f"{stokes['S1'].shape}")
        return stokes

    except Exception as e:
        raise RuntimeError(
            f"Error loading Stokes channels: {e}"
        ) from e


def stokes_from_complex(eh_real, eh_imag, ev_real, ev_imag):
    """Compute Stokes parameters from complex horizontal/vertical E-fields.

    The Stokes vector for fully-polarimetric radar is defined as:

    .. math::

        S_1 &= |E_H|^2 + |E_V|^2 \\\\
        S_2 &= |E_H|^2 - |E_V|^2 \\\\
        S_3 &= 2 \\operatorname{Re}(E_H E_V^*) \\\\
        S_4 &= -2 \\operatorname{Im}(E_H E_V^*)

    Parameters
    ----------
    eh_real, eh_imag : numpy.ndarray
        Real and imaginary parts of the horizontal polarisation E-field.
    ev_real, ev_imag : numpy.ndarray
        Real and imaginary parts of the vertical polarisation E-field.

    Returns
    -------
    S1, S2, S3, S4 : numpy.ndarray
        The four Stokes parameters (each same shape as inputs).
    """
    try:
        eh = eh_real.astype(np.float64) + 1j * eh_imag.astype(np.float64)
        ev = ev_real.astype(np.float64) + 1j * ev_imag.astype(np.float64)

        power_h = np.abs(eh) ** 2
        power_v = np.abs(ev) ** 2
        cross = eh * np.conj(ev)

        S1 = power_h + power_v
        S2 = power_h - power_v
        S3 = 2.0 * np.real(cross)
        S4 = -2.0 * np.imag(cross)

        print(f"[data_loader] Computed Stokes from complex E-fields — "
              f"shape: {S1.shape}")
        return S1, S2, S3, S4

    except Exception as e:
        raise RuntimeError(
            f"Error computing Stokes from complex E-fields: {e}"
        ) from e


# =============================================================================
# DEM Loading
# =============================================================================

def load_dem(filepath, file_format='geotiff'):
    """Load a Digital Elevation Model (DEM).

    Parameters
    ----------
    filepath : str or pathlib.Path
        Path to the DEM file.
    file_format : {'geotiff', 'pds'}, default 'geotiff'
        Format of the DEM file.

    Returns
    -------
    dem_array : numpy.ndarray
        2-D elevation array (metres).
    pixel_size_meters : float
        Ground pixel spacing in metres, derived from the geotransform.
    profile : dict or tuple
        For GeoTIFF: rasterio profile dict.
        For PDS: GDAL geotransform tuple.
    """
    loader = _get_loader(file_format)

    try:
        result = loader(filepath)
        dem_array = result[0].astype(np.float64)

        # Ensure 2-D
        if dem_array.ndim > 2:
            dem_array = dem_array[0]

        # Determine pixel size
        if file_format.lower() == 'geotiff':
            profile = result[1]
            transform = result[2]
            pixel_size_meters = abs(transform[0])  # pixel width in CRS units
        else:
            geotransform = result[1]
            profile = geotransform
            pixel_size_meters = abs(geotransform[1])

        print(f"[data_loader] Loaded DEM: {filepath}")
        print(f"  Shape: {dem_array.shape}  |  "
              f"Pixel size: {pixel_size_meters:.2f} m")
        return dem_array, pixel_size_meters, profile

    except Exception as e:
        raise RuntimeError(f"Error loading DEM '{filepath}': {e}") from e


# =============================================================================
# Validation
# =============================================================================

def validate_stokes(S1, S2, S3, S4):
    """Validate Stokes parameters against physical constraints.

    Two checks are performed:

    1. **Non-negativity**: ``S1 >= 0`` (total power must be non-negative).
    2. **Polarisation constraint**: ``S1² >= S2² + S3² + S4²``
       (degree of polarisation cannot exceed unity).

    Parameters
    ----------
    S1, S2, S3, S4 : numpy.ndarray
        The four Stokes parameter arrays.

    Returns
    -------
    is_valid : bool
        ``True`` if all pixels satisfy both constraints,
        ``False`` otherwise.  Warnings are printed for violations.
    """
    n_pixels = S1.size
    is_valid = True

    # Check 1: S1 >= 0
    neg_mask = S1 < 0
    n_neg = np.count_nonzero(neg_mask)
    if n_neg > 0:
        pct = 100.0 * n_neg / n_pixels
        print(f"[WARNING] {n_neg} pixels ({pct:.2f}%) have S1 < 0 "
              f"(min S1 = {np.nanmin(S1):.6f})")
        is_valid = False

    # Check 2: S1^2 >= S2^2 + S3^2 + S4^2
    lhs = S1 ** 2
    rhs = S2 ** 2 + S3 ** 2 + S4 ** 2
    violation_mask = rhs > lhs + 1e-10  # small tolerance for floating point
    n_violation = np.count_nonzero(violation_mask)
    if n_violation > 0:
        pct = 100.0 * n_violation / n_pixels
        max_excess = np.nanmax(np.sqrt(rhs[violation_mask]) -
                               np.abs(S1[violation_mask]))
        print(f"[WARNING] {n_violation} pixels ({pct:.2f}%) violate "
              f"S1² >= S2² + S3² + S4² (max excess = {max_excess:.6f})")
        is_valid = False

    if is_valid:
        print("[data_loader] Stokes validation PASSED — "
              "all constraints satisfied.")

    return is_valid


# =============================================================================
# Internal Helpers
# =============================================================================

def _get_loader(file_format):
    """Return the appropriate loader function for *file_format*.

    Parameters
    ----------
    file_format : str
        ``'geotiff'`` or ``'pds'``.

    Returns
    -------
    loader : callable

    Raises
    ------
    ValueError
        If *file_format* is not recognised.
    """
    fmt = file_format.lower().strip()
    if fmt in ('geotiff', 'tiff', 'tif'):
        return load_geotiff
    elif fmt in ('pds', 'img'):
        return load_pds
    else:
        raise ValueError(
            f"Unsupported file format: '{file_format}'. "
            f"Use 'geotiff' or 'pds'."
        )


def load_dataset():
    """Load the real dataset using the paths configured in config.py.

    Returns
    -------
    dataset : dict
        A dictionary containing:
        - 'stokes_L': L-band Stokes dict with S1-S4 arrays.
        - 'stokes_S': S-band Stokes dict with S1-S4 arrays.
        - 'dem': 2D numpy array of elevation (meters).
        - 'pixel_size': Ground pixel spacing in meters.
        - 'target_center': (row, col) coordinates of target region.
    """
    import os

    # 1. Load DEM
    if not os.path.exists(config.DEM_PATH):
        raise FileNotFoundError(
            f"DEM file not found at: {os.path.abspath(config.DEM_PATH)}\n"
            f"Please download a LOLA/OHRC DEM and place it there."
        )

    dem_format = 'pds' if config.DEM_PATH.lower().endswith(('.img', '.lbl')) else 'geotiff'
    dem, pixel_size, _ = load_dem(config.DEM_PATH, file_format=dem_format)

    # 2. Load L-band Stokes
    l_paths = [config.L_BAND_S1, config.L_BAND_S2, config.L_BAND_S3, config.L_BAND_S4]
    for i, path in enumerate(l_paths, 1):
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"L-band Stokes S{i} file not found at: {os.path.abspath(path)}\n"
                f"Please download Chandrayaan-2 DFSAR L-band Stokes data."
            )

    l_format = 'pds' if config.L_BAND_S1.lower().endswith(('.img', '.lbl')) else 'geotiff'
    stokes_L = load_stokes_channels(
        config.L_BAND_S1, config.L_BAND_S2, config.L_BAND_S3, config.L_BAND_S4,
        file_format=l_format
    )

    # Validate L-band Stokes
    print("Validating L-band Stokes parameters...")
    validate_stokes(stokes_L['S1'], stokes_L['S2'], stokes_L['S3'], stokes_L['S4'])

    # 3. Load S-band Stokes
    s_paths = [config.S_BAND_S1, config.S_BAND_S2, config.S_BAND_S3, config.S_BAND_S4]
    for i, path in enumerate(s_paths, 1):
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"S-band Stokes S{i} file not found at: {os.path.abspath(path)}\n"
                f"Please download Chandrayaan-2 DFSAR S-band Stokes data."
            )

    s_format = 'pds' if config.S_BAND_S1.lower().endswith(('.img', '.lbl')) else 'geotiff'
    stokes_S = load_stokes_channels(
        config.S_BAND_S1, config.S_BAND_S2, config.S_BAND_S3, config.S_BAND_S4,
        file_format=s_format
    )

    # Validate S-band Stokes
    print("Validating S-band Stokes parameters...")
    validate_stokes(stokes_S['S1'], stokes_S['S2'], stokes_S['S3'], stokes_S['S4'])

    # Ensure Stokes and DEM dimensions are compatible
    if stokes_L['S1'].shape != dem.shape:
        print(f"\n[WARNING] Stokes shape {stokes_L['S1'].shape} does not match DEM shape {dem.shape}!")
        print("Ensure they are georeferenced and cropped to the same spatial bounding box.")

    return {
        'stokes_L': stokes_L,
        'stokes_S': stokes_S,
        'dem': dem,
        'pixel_size': pixel_size,
        'target_center': config.TARGET_CENTER_PIXELS
    }

