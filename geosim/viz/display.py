"""Display surface maps as matplotlib figures.

The single public function :func:`display_surface_map` is the shared renderer
used by all per-field display commands (topography elevation display,
geology plates display, climate temperature display, …).

Each call reprojects the internal surface-map array to an equirectangular
image via :func:`geosim.core.grid.surface_map_to_equirectangular`, then
renders it with matplotlib and blocks until the user closes the window.
"""
from __future__ import annotations

import numpy as np


def display_surface_map(
    arr: np.ndarray,
    grid_type: str,
    resolution: int,
    title: str = "",
    colormap: str = "viridis",
    vmin: float | None = None,
    vmax: float | None = None,
    units: str = "",
) -> None:
    """Render a surface-map array as an equirectangular image.

    Reprojects *arr* to a regular lon/lat grid and displays it with
    matplotlib.  Blocks until the user closes the figure window.

    This function is called by every per-field display command; individual
    commands supply appropriate defaults (colormap, units, etc.).

    Args:
        arr: 1-D HEALPix array (spherical) or 2-D array (flat).
        grid_type: 'spherical' or 'flat'.
        resolution: HEALPix order for spherical; grid side-length for flat.
        title: Figure title.
        colormap: Matplotlib colormap name.  Default 'viridis'.
        vmin: Lower bound for the colour scale.  Defaults to array minimum.
        vmax: Upper bound for the colour scale.  Defaults to array maximum.
        units: Label shown on the colourbar.
    """
    import matplotlib.pyplot as plt
    from geosim.core.grid import surface_map_to_equirectangular

    image = surface_map_to_equirectangular(arr, grid_type, resolution)

    fig, ax = plt.subplots(figsize=(12, 6))
    im = ax.imshow(
        image,
        aspect="auto",
        extent=[0, 360, -90, 90],
        origin="upper",
        cmap=colormap,
        vmin=vmin,
        vmax=vmax,
    )
    cbar = fig.colorbar(im, ax=ax, fraction=0.02, pad=0.02)
    if units:
        cbar.set_label(units)

    ax.set_xlabel("Longitude (°)")
    ax.set_ylabel("Latitude (°)")
    ax.set_xticks(range(0, 361, 60))
    ax.set_yticks(range(-90, 91, 30))
    if title:
        ax.set_title(title)

    plt.tight_layout()
    plt.show()
