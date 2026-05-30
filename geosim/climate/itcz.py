"""ITCZ (Intertropical Convergence Zone) probability maps.

The ITCZ is the near-equatorial belt where the trade winds of the Northern and
Southern hemispheres meet.  It is the primary driver of tropical precipitation
and an important organising feature for the global circulation.

This module provides two routes to a per-pixel *ITCZ probability map* —
a float array of shape ``(n_seasons, n_pixels)`` where each season slice holds
values 0--1 representing how likely the ITCZ is to be over each surface pixel
during that part of the year:

``itcz_from_temperature``
    Used when a surface-temperature map is already available (i.e., on any
    simulation pass after the first).  The ITCZ closely follows the *thermal
    equator* -- the latitude of maximum near-surface temperature at each
    longitude -- so probability peaks are placed there and spread with a
    Gaussian kernel.

``itcz_from_topography``
    Used on the very first simulation pass, before any temperature map exists.
    The position of the thermal equator is *estimated* from the land/ocean
    distribution: large landmasses heat up more than oceans in summer, pulling
    the ITCZ poleward toward them.  Over open ocean and when no topography is
    available, the ITCZ is assumed to sit near the sub-solar latitude.

``compute_itcz``
    Dispatcher: selects the right route based on what data is available.
    This is the function called by ``simulate_climate``.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from geosim.core.world import WorldConfig
    from geosim.planetology.planetology import Planetology
    from geosim.topography.topography import Topography

# ---------------------------------------------------------------------------
# Physical constants
# ---------------------------------------------------------------------------

_DEFAULT_AXIAL_TILT_DEG = 23.5    # Earth-like axial tilt (degrees)

# Thermal lag: not yet used, reserved for future refinement
_THERMAL_LAG_LAND_DAYS  = 30.0    # land temperature peaks ~1 month after solstice
_THERMAL_LAG_OCEAN_DAYS = 75.0    # ocean temperature peaks ~2.5 months after solstice

# ODE relaxation rates (fraction of gap closed per degree of longitude).
# Calibrated to Earth:
#   _K_LAND:  ITCZ tracks ~90% of subsolar latitude over ~12 000 km of pure land
#             (108 one-degree bins → k ≈ ln(10)/108 ≈ 0.021)
#   _K_OCEAN: ITCZ returns to within 300 km of equator over ~8 000 km of open ocean
#             (72 one-degree bins → k ≈ ln(1/0.12)/72 ≈ 0.029)
_K_LAND  = 0.021
_K_OCEAN = 0.029

_N_LON_BINS  = 360    # longitude bins for the ODE scan (1° each)
_N_ODE_PASSES = 3     # passes around the globe to establish periodicity

_HIGHLAND_THRESHOLD_M = 3000.0   # elevation above which land blocks the ITCZ
_HIGHLAND_HEAT_WEIGHT = -0.3     # heat weight for high terrain (negative → repels)

_ITCZ_SIGMA_DEG = 7.0            # Gaussian half-width of the ITCZ band (degrees)


def compute_itcz(
    config: "WorldConfig",
    topography: "Topography | None",
    planetology: "Planetology | None",
    surface_temperature: np.ndarray | None,
    n_seasons: int = 4,
    display_map: bool = True,
) -> np.ndarray:
    """Return the ITCZ probability map of shape ``(n_seasons, n_pixels)``,
    choosing the best available method.

    If *surface_temperature* is provided (any simulation pass after the first),
    delegates to :func:`itcz_from_temperature`.  Otherwise falls back to
    :func:`itcz_from_topography`.

    This is the entry point called by ``simulate_climate``.

    Args:
        config:              World grid configuration.
        topography:          Current topography (may be None).
        planetology:         Orbital/physical parameters (may be None).
        surface_temperature: ``(n_seasons, n_pixels)`` surface temperature array
            (K) from the previous pass, or None.
        n_seasons:           Number of seasonal time-slices per year.

    Returns:
        Float32 array of shape ``(n_seasons, n_pixels)``, values in [0, 1].
    """
    if surface_temperature is not None:
        return itcz_from_temperature(surface_temperature, config, planetology, n_seasons, display_map)

    elevation: np.ndarray | None = None
    if topography is not None:
        tier = topography.tiers.get(config.base_resolution)
        if tier is not None and len(tier.elevation) > 0:
            elevation = tier.elevation.get(tier.elevation.latest_time)

    return itcz_from_topography(elevation, config, planetology, n_seasons, display_map)


def itcz_from_temperature(
    surface_temperature: np.ndarray,
    config: "WorldConfig",
    planetology: "Planetology | None" = None,
    n_seasons: int = 4,
    display_map: bool = True,
) -> np.ndarray:
    """Estimate the ITCZ probability map from an existing surface-temperature field.

    The ITCZ closely tracks the *thermal equator* -- the latitude of maximum
    near-surface temperature at each longitude.  For each season slice, this
    function:
      1. Reads the seasonal temperature map ``surface_temperature[s]``.
      2. Identifies the latitude of maximum temperature per longitude column.
      3. Places a Gaussian probability peak there for each column.
      4. Averages across longitudes to get a single latitudinal profile.

    Args:
        surface_temperature: ``(n_seasons, n_pixels)`` surface temperature (K).
        config:              World grid configuration.
        planetology:         Reserved for future use (axial tilt constrains the
            expected ITCZ latitude range; currently ignored).
        n_seasons:           Number of seasonal time-slices per year.

    Returns:
        Float32 array of shape ``(n_seasons, n_pixels)``, values in [0, 1].

    Notes:
        Gaussian width (sigma) is currently fixed at 10 degrees.  In reality
        the ITCZ width varies with sea-surface temperature gradients; this
        should be made a function of the temperature gradient magnitude.

    TODO:
        1. Obtain per-pixel (lon, lat) from ``core.grid.healpix_pixel_lonlat``
           (spherical) or construct from array indices (flat).
        2. For each season slice s and each unique-longitude bin:
           a. Find the pixel with the highest temperature -> that pixel's
              latitude is ``lat_thermal[s, lon_bin]``.
        3. For each pixel, compute angular distance from ``lat_thermal`` at the
           corresponding season and longitude.
        4. Apply a Gaussian: ``prob = exp(-0.5 * (dist / sigma_deg)**2)``,
           where ``sigma_deg`` is approximately 10 degrees.
        5. Normalise each season slice so its global maximum is 1.0.
        6. If axial_tilt is set via *planetology*, verify the range of
           thermal-equator migration is reasonable.
    """
    n_pixels = surface_temperature.shape[-1]
    # --- TODO: implement (see docstring) ---
    # Placeholder: for each season, use a Gaussian centred at the solar
    # declination for that season (a reasonable first approximation).
    return _seasonal_gaussians(n_pixels, n_seasons, config, planetology, sigma_deg=10.0)


def itcz_from_topography(
    elevation: np.ndarray | None,
    config: "WorldConfig",
    planetology: "Planetology | None" = None,
    n_seasons: int = 4,
    display_map: bool = True,
) -> "np.ndarray | tuple[np.ndarray, list[np.ndarray]]":
    """Estimate the ITCZ probability map from the land/ocean distribution.

    Used on the first simulation pass when no surface-temperature map yet exists.
    Landmasses heat up much more than oceans in summer, pulling the ITCZ poleward.

    Algorithm — first-order relaxation ODE integrated eastward:

      For each longitude bin x (0° → 360°, wrapping):
          y_target[s] = subsolar_lat[s] * heat_frac[x]
          y[s]        = y[s] + k[x] * (y_target[s] - y[s])

      where:
        - subsolar_lat[s] = -axial_tilt * cos(2π * s / n_seasons)
          (most poleward in midsummer, equatorial in winter)
        - heat_frac[x]  = mean heat weight of pixels in longitude bin x
            ocean (elev ≤ 0)          →  0.0  (ITCZ target = equator)
            low land (0–3000 m)       →  1.0  (ITCZ target = subsolar lat)
            high land (> 3000 m)      → −0.3  (ITCZ repelled, unlikely to cross)
        - k[x] = blend of _K_OCEAN and _K_LAND based on |heat_frac[x]|

      The scan repeats _N_ODE_PASSES times so that the starting condition at
      x = 0 converges to the periodic solution (y at x = 359° feeds directly
      into x = 0° of the next pass).

    Constants are calibrated to Earth:
      - Over Africa (≈100 % land, ≈12 000 km): ITCZ reaches ≈90 % of
        subsolar latitude  →  k_land ≈ 0.021 per degree-lon.
      - Over the Pacific (≈100 % ocean, ≈8 000 km): ITCZ returns to within
        300 km of the equator  →  k_ocean ≈ 0.029 per degree-lon.

    Per-bin ITCZ latitudes are converted to per-pixel probabilities via a
    Gaussian centred at the bin latitude (σ = _ITCZ_SIGMA_DEG).

    Args:
        elevation:   (n_pixels,) elevation array, or None (pure-ocean fallback).
        config:      World grid configuration.
        planetology: Used to read axial_tilt.  Falls back to
                     _DEFAULT_AXIAL_TILT_DEG when None or empty.
        n_seasons:   Number of seasonal time-slices per year.
        debug:       When True, return a tuple (final_result, pass_list) where
                     pass_list[i] is the (n_seasons, n_pixels) probability array
                     produced after ODE pass i+1.

    Returns:
        Float32 array of shape (n_seasons, n_pixels), values in [0, 1].
        When debug=True, returns (array, list[array]) instead.
    """
    # --- Pixel count and grid coordinates ---
    if elevation is not None:
        n_pixels = elevation.shape[0]
    else:
        n_pixels = 12 * (4 ** config.base_resolution)

    if config.grid_type == "spherical":
        from geosim.core.grid import healpix_pixel_lonlat
        lon_deg, lat_deg = healpix_pixel_lonlat(config.base_resolution)
        lon_deg = np.asarray(lon_deg, dtype=np.float32)
        lat_deg = np.asarray(lat_deg, dtype=np.float32)
    else:
        side = config.base_resolution
        row_idx = np.arange(n_pixels) // side
        col_idx = np.arange(n_pixels) % side
        lat_deg = np.linspace(90.0, -90.0, side, dtype=np.float32)[row_idx]
        lon_deg = np.linspace(0.0, 360.0, side, endpoint=False, dtype=np.float32)[col_idx]

    # Map each pixel to a longitude bin
    bin_idx = np.floor(lon_deg / (360.0 / _N_LON_BINS)).astype(np.int32) % _N_LON_BINS

    # --- Per-pixel heat weight ---
    if elevation is not None:
        heat_weight = np.where(
            elevation <= 0,
            0.0,
            np.where(elevation > _HIGHLAND_THRESHOLD_M, _HIGHLAND_HEAT_WEIGHT, 1.0),
        ).astype(np.float32)
    else:
        heat_weight = np.zeros(n_pixels, dtype=np.float32)

    # --- Average heat weight per longitude bin ---
    bin_counts = np.bincount(bin_idx, minlength=_N_LON_BINS).astype(np.float32)
    bin_heat   = np.bincount(bin_idx, weights=heat_weight, minlength=_N_LON_BINS).astype(np.float32)
    heat_frac  = np.zeros(_N_LON_BINS, dtype=np.float32)
    nonempty = bin_counts > 0
    heat_frac[nonempty] = bin_heat[nonempty] / bin_counts[nonempty]

    # ODE response rate per bin (blends ocean and land rates by |heat_frac|)
    k_per_bin = (_K_OCEAN + (_K_LAND - _K_OCEAN) * np.abs(heat_frac)).astype(np.float32)

    # --- Axial tilt ---
    axial_tilt = _DEFAULT_AXIAL_TILT_DEG
    if planetology is not None and len(planetology.axial_tilt) > 0:
        axial_tilt = float(planetology.axial_tilt.get(planetology.axial_tilt.latest_time))

    # Subsolar latitude per season (s=0 = NH winter solstice → most southerly)
    s_idx = np.arange(n_seasons, dtype=np.float32)
    subsolar_lats = (-axial_tilt * np.cos(2.0 * np.pi * s_idx / n_seasons)).astype(np.float32)

    # --- ODE passes ---
    # y[s] carries the ITCZ latitude state for each season across all passes
    y = np.zeros(n_seasons, dtype=np.float32)

    pass_results: list[np.ndarray] = []

    for k in range(_N_ODE_PASSES):
        season_lats = np.empty((n_seasons, _N_LON_BINS), dtype=np.float32)
        for x in range(_N_LON_BINS):
            y_target = subsolar_lats * heat_frac[x]   # (n_seasons,)
            y       += k_per_bin[x] * (y_target - y)  # (n_seasons,) in-place update
            season_lats[:, x] = y

        # Convert this pass's bin latitudes to per-pixel Gaussian probability
        pass_prob = np.empty((n_seasons, n_pixels), dtype=np.float32)
        for s in range(n_seasons):
            centers = season_lats[s][bin_idx]          # (n_pixels,)
            dist    = lat_deg - centers
            pass_prob[s] = np.exp(-0.5 * (dist / _ITCZ_SIGMA_DEG) ** 2)
        pass_results.append(pass_prob)

        # Display ITCZ map
        if display_map:
            display_itcz(pass_prob, config, elevation, title="Pass " + str(k + 1))

    final = pass_results[-1]
    return final


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _seasonal_gaussians(
    n_pixels: int,
    n_seasons: int,
    config: "WorldConfig",
    planetology: "Planetology | None",
    sigma_deg: float = 10.0,
) -> np.ndarray:
    """Return a ``(n_seasons, n_pixels)`` Gaussian ITCZ probability array.

    Each season slice is a Gaussian centred on the solar declination for that
    season, which is a reasonable placeholder until the real algorithm is
    implemented.

    Solar declination for season s (0 = NH winter solstice):
        delta(s) = -axial_tilt * cos(2*pi * s / n_seasons)

    Args:
        n_pixels:   Number of grid pixels.
        n_seasons:  Number of seasonal slices.
        config:     World grid configuration.
        planetology: Read axial_tilt from here if available.
        sigma_deg:  Gaussian standard deviation in degrees latitude.

    Returns:
        Float32 array of shape ``(n_seasons, n_pixels)``, peak value 1.0 per
        season.
    """
    # Read axial tilt
    axial_tilt = _DEFAULT_AXIAL_TILT_DEG
    if planetology is not None and len(planetology.axial_tilt) > 0:
        axial_tilt = float(planetology.axial_tilt.get(planetology.axial_tilt.latest_time))

    # Per-pixel latitudes
    if config.grid_type == "spherical":
        from geosim.core.grid import healpix_pixel_lonlat
        _, lat_deg = healpix_pixel_lonlat(config.base_resolution)
    else:
        side = config.base_resolution
        row_idx = np.arange(n_pixels) // side
        lat_deg = np.linspace(90.0, -90.0, side)[row_idx]

    result = np.empty((n_seasons, n_pixels), dtype=np.float32)
    for s in range(n_seasons):
        # Solar declination: most southerly (negative) at s=0 (NH winter)
        decl = -axial_tilt * np.cos(2.0 * np.pi * s / n_seasons)
        dist = lat_deg - decl
        result[s] = np.exp(-0.5 * (dist / sigma_deg) ** 2).astype(np.float32)

    return result


# ---------------------------------------------------------------------------
# Visualisation
# ---------------------------------------------------------------------------

def display_itcz(
    itcz: np.ndarray,
    config: "WorldConfig",
    elevation: np.ndarray | None = None,
    season: "int | None" = None,
    title: str = "ITCZ",
) -> None:
    """Display the ITCZ probability map alongside an elevation world map.

    Opens a single matplotlib window containing:
      - Panel 0: world elevation map (terrain colourmap).
      - Panel 1…n: ITCZ probability map for each season (YlOrRd colourmap).

    Args:
        itcz:      (n_seasons, n_pixels) ITCZ probability array.
        config:    World grid configuration.
        elevation: (n_pixels,) elevation array.  When None a blank map is shown.
        season:    Season index to display.  When None (default), all seasons
                   are shown, one panel each.
        title:     Figure suptitle.
    """
    import matplotlib.pyplot as plt
    from geosim.viz.display import display_surface_map, subplot_grid

    grid_type  = config.grid_type
    resolution = config.base_resolution

    if season is None:
        seasons_to_show = list(range(itcz.shape[0]))
    else:
        seasons_to_show = [season]

    n_panels = 1 + len(seasons_to_show)
    nrows, ncols = subplot_grid(n_panels)
    fig, axes_2d = plt.subplots(nrows, ncols, figsize=(6 * ncols, 4 * nrows),
                                squeeze=False)
    axes = axes_2d.flatten()

    # Hide unused cells
    for i in range(n_panels, nrows * ncols):
        axes[i].set_visible(False)

    # --- Panel 0: elevation / world map ---
    if elevation is not None:
        display_surface_map(elevation, grid_type, resolution,
                            title="World map", colormap="terrain", units="m",
                            ax=axes[0])
    else:
        blank = np.zeros(itcz.shape[1], dtype=np.float32)
        display_surface_map(blank, grid_type, resolution,
                            title="World map", colormap="Blues", ax=axes[0])

    # --- ITCZ panels ---
    for i, s in enumerate(seasons_to_show):
        display_surface_map(itcz[s], grid_type, resolution,
                            title=f"ITCZ  (season {s})",
                            colormap="YlOrRd", vmin=0.0, vmax=1.0,
                            units="prob", ax=axes[i + 1])

    if title:
        fig.suptitle(title)
    plt.tight_layout()
    plt.show()


