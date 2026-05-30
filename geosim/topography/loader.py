"""Elevation map loader for Topography."""
from __future__ import annotations

from pathlib import Path

import numpy as np

from geosim.core.grid import open_png_array, png_array_to_surface_map, png_to_surface_map

_DEFAULT_ELEV_RANGE = 16_000.0  # metres — kept consistent with default -8000/+8000


def estimate_sea_level_range(png_arr: np.ndarray) -> tuple[float, float]:
    """Derive min/max elevation bounds so that the mode brightness maps to 0 m.

    Assumes a fixed total elevation range of ``_DEFAULT_ELEV_RANGE`` metres
    (matching the default −8000 / +8000 m scale).  The range is split at the
    mode pixel value so that:

        brightness 0   → min_elev  (most negative)
        brightness mode → 0 m  (sea level)
        brightness 255  → max_elev  (most positive)

    The metres-per-step scale is constant across the whole range:
        scale = _DEFAULT_ELEV_RANGE / 255

    Returns:
        (min_elev, max_elev) in metres.
    """
    counts = np.bincount(png_arr.ravel().astype(np.uint8))
    mode = int(counts.argmax())
    scale = _DEFAULT_ELEV_RANGE / 255.0
    min_elev = -mode * scale
    max_elev = (255 - mode) * scale
    return min_elev, max_elev


def load_elevation_png(
    png_path: str | Path,
    grid_type: str,
    resolution: int,
    min_elev: float = -8000.0,
    max_elev: float = 8000.0,
    max_pixels: int | None = 100_000_000,
    estimate_sea_level: bool = False,
) -> np.ndarray:
    """Load a PNG as a planet-wide elevation map (metres).

    Thin wrapper over :func:`geosim.core.grid.png_to_surface_map` with
    elevation-appropriate defaults.  The PNG is interpreted as an
    equirectangular projection; brightness 0 = min_elev, 255 = max_elev.

    Args:
        png_path: Path to the PNG file (any mode; converted to grayscale).
        grid_type: 'spherical' or 'flat'.
        resolution: HEALPix order for spherical; grid side-length for flat.
        min_elev: Elevation (m) mapped to pixel brightness 0.  Default −8000.
            Ignored when *estimate_sea_level* is True.
        max_elev: Elevation (m) mapped to pixel brightness 255.  Default 8000.
            Ignored when *estimate_sea_level* is True.
        max_pixels: Downsample the PNG if it exceeds this pixel count.
            Default 100 000 000 (100 Mpx).  Pass ``None`` to disable.
        estimate_sea_level: If True, ignore *min_elev*/*max_elev* and instead
            derive them from the image so that the most common brightness value
            (the mode, which is typically the ocean floor) maps to 0 m.

    Returns:
        numpy float64 array of elevation values in metres.
    """
    if estimate_sea_level:
        png_arr = open_png_array(png_path, max_pixels)
        min_elev, max_elev = estimate_sea_level_range(png_arr)
        print(f"  Estimated sea level: mode brightness → 0 m  (min={min_elev:.0f} m, max={max_elev:.0f} m)")
        return png_array_to_surface_map(png_arr, grid_type, resolution, min_elev, max_elev)

    return png_to_surface_map(png_path, grid_type, resolution, min_elev, max_elev, max_pixels)

