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
  - converting a surface-map array back to a 2-D equirectangular image (for display)
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


# ---------------------------------------------------------------------------
# Surface-map → 2-D equirectangular image (for display / export)
# ---------------------------------------------------------------------------

def surface_map_to_equirectangular(
    arr: np.ndarray,
    grid_type: str,
    resolution: int,
    output_height: int = 360,
    output_width: int = 720,
) -> np.ndarray:
    """Convert a surface-map array to a 2-D equirectangular image.

    This is the inverse of :func:`png_to_surface_map`: it reprojects the
    internal grid representation back into a regular (lon, lat) grid suitable
    for display or PNG export.

    For spherical grids (HEALPix), each output pixel's centre (lon, lat) is
    mapped to the nearest HEALPix pixel using nearest-neighbour lookup — fast
    and exact (no blurring of discrete geology/plate maps).

    For flat grids the array is simply resized to (output_height, output_width)
    using bilinear interpolation.

    Args:
        arr: 1-D HEALPix array (spherical) or 2-D array (flat).
        grid_type: 'spherical' or 'flat'.
        resolution: HEALPix order for spherical; grid side-length for flat.
        output_height: Number of rows in the output image.  Default 360.
        output_width:  Number of columns in the output image.  Default 720.

    Returns:
        2-D float64 array of shape (output_height, output_width).
    """
    if grid_type == "spherical":
        from astropy_healpix import HEALPix
        import astropy.units as u

        nside = 2 ** resolution
        hp = HEALPix(nside=nside, order="ring")

        # Pixel-centre longitudes and latitudes for the output grid
        lon_centers = (np.arange(output_width) + 0.5) / output_width * 360.0
        lat_centers = 90.0 - (np.arange(output_height) + 0.5) / output_height * 180.0
        lon_grid, lat_grid = np.meshgrid(lon_centers, lat_centers)

        ipix = hp.lonlat_to_healpix(
            lon_grid.ravel() * u.deg,
            lat_grid.ravel() * u.deg,
        )
        return arr[ipix].reshape(output_height, output_width)
    else:
        return zoom(
            arr.astype(np.float64),
            (output_height / arr.shape[0], output_width / arr.shape[1]),
            order=1,
        )


# ---------------------------------------------------------------------------
# Natural output dimensions for a given grid
# ---------------------------------------------------------------------------

def natural_equirectangular_size(grid_type: str, resolution: int) -> tuple[int, int]:
    """Return a natural (height, width) for an equirectangular export image.

    Chosen so that the output pixel density roughly matches the source grid —
    i.e. the image is large enough to show all the detail in the data without
    being gratuitously oversized.

    For spherical grids: width = 45 * 2^order, height = width // 2.
    For flat grids: (resolution, resolution).

    Args:
        grid_type: 'spherical' or 'flat'.
        resolution: HEALPix order for spherical; grid side-length for flat.

    Returns:
        (height, width) tuple of integers.
    """
    if grid_type == "spherical":
        width = 45 * (2 ** resolution)
        return width // 2, width
    else:
        return resolution, resolution


# ---------------------------------------------------------------------------
# Surface-map → greyscale PNG file
# ---------------------------------------------------------------------------

def surface_map_to_png(
    arr: np.ndarray,
    out_path,
    grid_type: str,
    resolution: int,
    min_val: float,
    max_val: float,
    output_height: int | None = None,
    output_width: int | None = None,
) -> None:
    """Save a surface-map array as an 8-bit greyscale PNG.

    Reprojects *arr* to equirectangular via
    :func:`surface_map_to_equirectangular`, linearly scales values from
    [min_val, max_val] to [0, 255], and writes the result as a greyscale PNG.

    Values below min_val are clamped to 0 (black); values above max_val are
    clamped to 255 (white).

    If output_height/output_width are not given, uses
    :func:`natural_equirectangular_size` for the grid.

    Args:
        arr: 1-D HEALPix array (spherical) or 2-D array (flat).
        out_path: Destination file path (str or Path); parent dirs must exist.
        grid_type: 'spherical' or 'flat'.
        resolution: HEALPix order for spherical; grid side-length for flat.
        min_val: Data value mapped to brightness 0 (black).
        max_val: Data value mapped to brightness 255 (white).
        output_height: Rows in the output PNG; defaults to natural size.
        output_width: Columns in the output PNG; defaults to natural size.
    """
    from PIL import Image

    nat_h, nat_w = natural_equirectangular_size(grid_type, resolution)
    h = output_height if output_height is not None else nat_h
    w = output_width if output_width is not None else nat_w

    image = surface_map_to_equirectangular(arr, grid_type, resolution, h, w)
    brightness = (image - min_val) / (max_val - min_val) * 255.0
    brightness = np.clip(brightness, 0, 255).astype(np.uint8)

    Image.fromarray(brightness, mode="L").save(out_path)


def null_surface_map_png(
    out_path,
    grid_type: str,
    resolution: int,
    output_height: int | None = None,
    output_width: int | None = None,
) -> None:
    """Save a mid-grey placeholder PNG at the natural size for this grid.

    Used when a field has no data yet but the user wants a blank template to
    paint on and re-import.  Mid-grey (128) is chosen so that when the image
    is loaded with default min/max it maps to approximately 0 m elevation.

    Args:
        out_path: Destination file path (str or Path); parent dirs must exist.
        grid_type: 'spherical' or 'flat'.
        resolution: HEALPix order for spherical; grid side-length for flat.
        output_height: Rows; defaults to natural size.
        output_width: Columns; defaults to natural size.
    """
    from PIL import Image

    nat_h, nat_w = natural_equirectangular_size(grid_type, resolution)
    h = output_height if output_height is not None else nat_h
    w = output_width if output_width is not None else nat_w

    arr = np.full((h, w), 128, dtype=np.uint8)
    Image.fromarray(arr, mode="L").save(out_path)

