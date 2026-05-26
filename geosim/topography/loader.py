"""Convert PNG files to elevation arrays for Topography."""
from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy.ndimage import map_coordinates, zoom


def load_elevation_png(
    png_path: str | Path,
    grid_type: str,
    resolution: int,
    min_elev: float = -8000.0,
    max_elev: float = 8000.0,
) -> np.ndarray:
    """Load a PNG as a planet-wide elevation map.

    The PNG is interpreted as an equirectangular projection:
      - left edge = longitude 0°, right edge = 360° (wraps)
      - top edge = latitude +90°, bottom edge = -90°
      - brightness 0 (black) = min_elev metres
      - brightness 255 (white) = max_elev metres

    For spherical grids, returns a 1-D HEALPix array (ring ordering) of
    length 12 * nside², where nside = 2 ** resolution.

    For flat grids, returns a 2-D array of shape (resolution, resolution).

    Args:
        png_path: Path to the PNG file (any mode; converted to grayscale).
        grid_type: 'spherical' or 'flat'.
        resolution: HEALPix order for spherical; grid side-length for flat.
        min_elev: Elevation (m) mapped to pixel brightness 0.
        max_elev: Elevation (m) mapped to pixel brightness 255.

    Returns:
        numpy float64 array of elevation values in metres.
    """
    from PIL import Image

    img = Image.open(png_path).convert("L")  # force 8-bit grayscale
    png_arr = np.asarray(img, dtype=np.float64)  # shape (H, W), values 0–255
    H, W = png_arr.shape

    if grid_type == "spherical":
        brightness = _sample_healpix(png_arr, H, W, resolution)
    else:
        brightness = _sample_flat(png_arr, H, W, resolution)

    return min_elev + (brightness / 255.0) * (max_elev - min_elev)


def _sample_healpix(
    png_arr: np.ndarray, H: int, W: int, order: int
) -> np.ndarray:
    """Sample the PNG at the centre of every HEALPix pixel (ring ordering).

    For each equal-area HEALPix pixel we compute its (lon, lat) centre and
    bilinearly interpolate the PNG at that point using
    scipy.ndimage.map_coordinates — a single vectorised call over all pixels.

    Returns an array of brightness values (0–255) of length 12 * nside².
    """
    from astropy_healpix import HEALPix
    import astropy.units as u

    nside = 2 ** order
    hp = HEALPix(nside=nside, order="ring")
    ipix = np.arange(hp.npix)

    lon, lat = hp.healpix_to_lonlat(ipix)
    lon_deg = lon.to(u.deg).value  # 0 – 360
    lat_deg = lat.to(u.deg).value  # -90 – +90

    # lon [0, 360) → col [0, W); map_coordinates wraps at boundaries
    col_coords = (lon_deg / 360.0) * W
    # lat [+90, -90] → row [0, H); top of PNG = +90°
    row_coords = (90.0 - lat_deg) / 180.0 * H
    row_coords = np.clip(row_coords, 0, H - 1)

    return map_coordinates(png_arr, [row_coords, col_coords], order=1, mode="wrap")


def _sample_flat(
    png_arr: np.ndarray, H: int, W: int, resolution: int
) -> np.ndarray:
    """Resize the PNG to (resolution × resolution) via bilinear interpolation."""
    resized = zoom(png_arr, (resolution / H, resolution / W), order=1)
    return resized
