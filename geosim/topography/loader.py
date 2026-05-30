"""Elevation map loader for Topography."""
from __future__ import annotations

from pathlib import Path

import numpy as np

from geosim.core.grid import png_to_surface_map


def load_elevation_png(
    png_path: str | Path,
    grid_type: str,
    resolution: int,
    min_elev: float = -8000.0,
    max_elev: float = 8000.0,
    max_pixels: int | None = 100_000_000,
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
        max_elev: Elevation (m) mapped to pixel brightness 255.  Default 8000.
        max_pixels: Downsample the PNG if it exceeds this pixel count.
            Default 100 000 000 (100 Mpx).  Pass ``None`` to disable.

    Returns:
        numpy float64 array of elevation values in metres.
    """
    return png_to_surface_map(png_path, grid_type, resolution, min_elev, max_elev, max_pixels)

