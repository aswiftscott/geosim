"""Display surface maps as matplotlib figures.

The single public function :func:`display_surface_map` is the shared renderer
used by all per-field display commands (topography elevation display,
geology plates display, climate temperature display, …) and by composite
figures such as :func:`geosim.climate.itcz.display_itcz`.

Each call reprojects the internal surface-map array to an equirectangular
image via :func:`geosim.core.grid.surface_map_to_equirectangular`, then
renders it into either a new standalone figure (default) or a caller-supplied
subplot axis.
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    import matplotlib.axes


def subplot_grid(n: int) -> tuple[int, int]:
    """Return ``(nrows, ncols)`` for the tightest grid that fits *n* panels.

    Chooses the most square arrangement with at least as many columns as rows
    (landscape bias).  Examples::

        n=1 → (1, 1)    n=2 → (1, 2)    n=3 → (2, 2)
        n=4 → (2, 2)    n=5 → (2, 3)    n=6 → (2, 3)
        n=7 → (3, 3)    n=8 → (2, 4)    n=9 → (3, 3)

    Use with ``plt.subplots(nrows, ncols, squeeze=False)`` so the returned axes
    array is always 2-D regardless of grid dimensions.

    Args:
        n: Number of panels to fit (must be >= 1).

    Returns:
        ``(nrows, ncols)`` with ``nrows * ncols >= n`` and ``ncols >= nrows``.
    """
    if n <= 0:
        raise ValueError(f"n must be >= 1, got {n}")
    ncols = math.ceil(math.sqrt(n))
    nrows = math.ceil(n / ncols)
    return nrows, ncols


def display_surface_map(
    arr: np.ndarray,
    grid_type: str,
    resolution: int,
    title: str = "",
    colormap: str = "viridis",
    vmin: float | None = None,
    vmax: float | None = None,
    units: str = "",
    ax: "matplotlib.axes.Axes | None" = None,
) -> None:
    """Render a surface-map array as an equirectangular image.

    Reprojects *arr* to a regular lon/lat grid and renders it with matplotlib.

    When *ax* is ``None`` (the default) a new standalone figure is created and
    displayed; the call blocks until the user closes the window.  When *ax* is
    provided the image is drawn into that axis and the caller is responsible for
    showing the figure — this is used by composite displays such as
    :func:`geosim.climate.itcz.display_itcz`.

    Args:
        arr: 1-D HEALPix array (spherical) or 2-D array (flat).
        grid_type: 'spherical' or 'flat'.
        resolution: HEALPix order for spherical; grid side-length for flat.
        title: Axis title.
        colormap: Matplotlib colormap name.  Default 'viridis'.
        vmin: Lower bound for the colour scale.  Defaults to array minimum.
        vmax: Upper bound for the colour scale.  Defaults to array maximum.
        units: Label shown on the colourbar.
        ax: Existing matplotlib ``Axes`` to draw into.  When ``None`` a new
            figure is created and shown immediately.
    """
    import matplotlib.pyplot as plt
    from geosim.core.grid import surface_map_to_equirectangular

    image = surface_map_to_equirectangular(arr, grid_type, resolution)

    standalone = ax is None
    if standalone:
        fig, ax = plt.subplots(figsize=(12, 6))
    else:
        fig = ax.get_figure()

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

    if standalone:
        plt.tight_layout()
        plt.show()
