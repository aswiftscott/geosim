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


def _make_elevation_cmap(vmin: float, vmax: float, sea_level: float = 0.0):
    """Build a (cmap, norm) pair for elevation data with a hard colour break at sea level.

    Water (below sea_level): dark navy → light cyan/blue (shallow).
    Land  (above sea_level): bright green → brown → snow-white.
    The two palettes are joined end-to-end into a single ListedColormap so
    the colour jump at the boundary is sharp rather than interpolated.
    """
    import matplotlib.colors as mcolors
    import matplotlib.pyplot as plt

    data_range = vmax - vmin
    if data_range == 0:
        return plt.cm.terrain, mcolors.Normalize(vmin=vmin, vmax=vmax)

    sea_frac = np.clip((sea_level - vmin) / data_range, 0.0, 1.0)

    N = 512
    n_below = max(1, round(sea_frac * N))
    n_above = max(1, N - n_below)

    # Water: dark navy/black (deepest) → pale blue (just below sea level)
    water = plt.cm.Blues_r(np.linspace(0.05, 0.55, n_below))
    # Land: vivid green (coast) → brown → white (highest peaks)
    land = plt.cm.terrain(np.linspace(0.25, 1.0, n_above))

    cmap = mcolors.ListedColormap(np.vstack([water, land]))
    norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
    return cmap, norm


def display_surface_map(
    arr: np.ndarray,
    grid_type: str,
    resolution: int,
    title: str = "",
    colormap: str = "viridis",
    vmin: float | None = None,
    vmax: float | None = None,
    units: str = "",
    sea_level: float | None = None,
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
        colormap: Matplotlib colormap name.  Ignored when *sea_level* is set.
        vmin: Lower bound for the colour scale.  Defaults to array minimum.
        vmax: Upper bound for the colour scale.  Defaults to array maximum.
        units: Label shown on the colourbar.
        sea_level: When provided, use a custom elevation colormap with a hard
            colour break at this value (water below, land above).  Overrides
            *colormap*.
    """
    import matplotlib.pyplot as plt
    from geosim.core.grid import surface_map_to_equirectangular

    image = surface_map_to_equirectangular(arr, grid_type, resolution)

    effective_vmin = float(arr.min()) if vmin is None else vmin
    effective_vmax = float(arr.max()) if vmax is None else vmax

    if sea_level is not None:
        cmap, norm = _make_elevation_cmap(effective_vmin, effective_vmax, sea_level)
    else:
        import matplotlib.colors as mcolors
        cmap = colormap
        norm = mcolors.Normalize(vmin=effective_vmin, vmax=effective_vmax)

    fig, ax = plt.subplots(figsize=(12, 6))
    im = ax.imshow(
        image,
        aspect="auto",
        extent=[0, 360, -90, 90],
        origin="upper",
        cmap=cmap,
        norm=norm,
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
