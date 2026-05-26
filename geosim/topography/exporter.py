"""Elevation map exporter for Topography."""
from __future__ import annotations

from pathlib import Path

import numpy as np

from geosim.core.grid import null_surface_map_png, surface_map_to_png


def export_elevation_png(
    arr: np.ndarray,
    out_path: str | Path,
    grid_type: str,
    resolution: int,
    min_elev: float | None = None,
    max_elev: float | None = None,
) -> tuple[float, float]:
    """Save an elevation array as a greyscale PNG.

    Thin wrapper over :func:`geosim.core.grid.surface_map_to_png` with
    elevation-appropriate behaviour: if min_elev/max_elev are not supplied,
    the actual data range is used so that the full dynamic range of the PNG
    is utilised.

    Args:
        arr: 1-D HEALPix or 2-D flat elevation array (metres).
        out_path: Destination file path.
        grid_type: 'spherical' or 'flat'.
        resolution: HEALPix order for spherical; grid side-length for flat.
        min_elev: Value mapped to black.  Defaults to arr.min().
        max_elev: Value mapped to white.  Defaults to arr.max().

    Returns:
        (min_elev, max_elev) actually used, so the caller can report them to
        the user for use with 'topography elevation load'.
    """
    actual_min = float(arr.min()) if min_elev is None else min_elev
    actual_max = float(arr.max()) if max_elev is None else max_elev
    if actual_min == actual_max:
        actual_max = actual_min + 1.0  # avoid divide-by-zero for flat maps

    surface_map_to_png(arr, out_path, grid_type, resolution, actual_min, actual_max)
    return actual_min, actual_max
