"""Shared grid utilities for surface map creation and sampling.

All sub-objects (Topography, Geology, Climate, …) that store planet-wide maps
use the same two grid representations:

  spherical  — 1-D HEALPix array, ring ordering, length 12 * nside²
                where nside = 2 ** order
  flat       — 2-D numpy array of shape (resolution, resolution)

This module provides the shared functions for:
  - converting HEALPix pixel indices to (lon, lat) coordinates
  - bilinearly sampling an equirectangular image at arbitrary (lon, lat) points
  - loading a PNG as a surface-map array (used by every object's PNG loader)
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy.ndimage import map_coordinates, zoom


# ---------------------------------------------------------------------------
# Coordinate helpers
# ---------------------------------------------------------------------------

def healpix_pixel_lonlat(order: int) -> tuple[np.ndarray, np.ndarray]:
    """Return (lon_deg, lat_deg) for every HEALPix pixel at the given order.

    Uses ring ordering.  lon_deg is in [0, 360), lat_deg in [-90, +90].

    Args:
        order: HEALPix order; nside = 2 ** order.

    Returns:
        Tuple of (lon_deg, lat_deg), each a 1-D float64 array of length
        12 * nside².
    """
    from astropy_healpix import HEALPix
    import astropy.units as u

    nside = 2 ** order
    hp = HEALPix(nside=nside, order="ring")
    lon, lat = hp.healpix_to_lonlat(np.arange(hp.npix))
    return lon.to(u.deg).value, lat.to(u.deg).value


# ---------------------------------------------------------------------------
# Sampling helpers
# ---------------------------------------------------------------------------

def sample_equirectangular(
    png_arr: np.ndarray,
    lon_deg: np.ndarray,
    lat_deg: np.ndarray,
) -> np.ndarray:
    """Bilinearly sample an equirectangular image at (lon, lat) coordinates.

    The image is assumed to span lon [0, 360) left-to-right and
    lat [+90, -90] top-to-bottom (standard equirectangular convention).
    Longitude wraps at the left/right edges.

    Args:
        png_arr: 2-D float array of shape (H, W), values arbitrary.
        lon_deg: 1-D array of longitude values in degrees [0, 360).
        lat_deg: 1-D array of latitude values in degrees [-90, +90].

    Returns:
        1-D array of interpolated values, same length as lon_deg / lat_deg.
    """
    H, W = png_arr.shape
    col_coords = (lon_deg / 360.0) * W          # wraps via mode="wrap"
    row_coords = (90.0 - lat_deg) / 180.0 * H
    row_coords = np.clip(row_coords, 0, H - 1)
    return map_coordinates(png_arr, [row_coords, col_coords], order=1, mode="wrap")


# ---------------------------------------------------------------------------
# PNG → surface-map loader
# ---------------------------------------------------------------------------

def png_to_surface_map(
    png_path: str | Path,
    grid_type: str,
    resolution: int,
    min_val: float,
    max_val: float,
) -> np.ndarray:
    """Load a PNG as a planet-wide surface-map array.

    The PNG is interpreted as an equirectangular projection:
      - left edge = longitude 0°, right edge = 360° (wraps)
      - top edge = latitude +90°, bottom edge = -90°
      - brightness 0 (black) = min_val
      - brightness 255 (white) = max_val

    For spherical grids, returns a 1-D HEALPix array (ring ordering) of
    length 12 * nside², where nside = 2 ** resolution.

    For flat grids, returns a 2-D array of shape (resolution, resolution).

    This function is the shared core used by all per-object PNG loaders
    (topography, geology, climate, …).  Each loader calls this with
    domain-appropriate defaults and then wraps the result as needed.

    Args:
        png_path: Path to the PNG file (any mode; converted to grayscale).
        grid_type: 'spherical' or 'flat'.
        resolution: HEALPix order for spherical; grid side-length for flat.
        min_val: Value mapped to pixel brightness 0.
        max_val: Value mapped to pixel brightness 255.

    Returns:
        numpy float64 array of values linearly scaled from min_val to max_val.
    """
    from PIL import Image

    img = Image.open(png_path).convert("L")  # force 8-bit grayscale
    png_arr = np.asarray(img, dtype=np.float64)  # shape (H, W), values 0–255
    H, W = png_arr.shape

    if grid_type == "spherical":
        lon_deg, lat_deg = healpix_pixel_lonlat(resolution)
        brightness = sample_equirectangular(png_arr, lon_deg, lat_deg)
    else:
        brightness = zoom(png_arr, (resolution / H, resolution / W), order=1)

    return min_val + (brightness / 255.0) * (max_val - min_val)
