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

_DEFAULT_AXIAL_TILT_DEG = 23.5  # used when planetology is absent or unset


def compute_itcz(
    config: "WorldConfig",
    topography: "Topography | None",
    planetology: "Planetology | None",
    surface_temperature: np.ndarray | None,
    n_seasons: int = 4,
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
        return itcz_from_temperature(surface_temperature, config, planetology, n_seasons)

    elevation: np.ndarray | None = None
    if topography is not None:
        tier = topography.tiers.get(config.base_resolution)
        if tier is not None and len(tier.elevation) > 0:
            elevation = tier.elevation.get(tier.elevation.latest_time)

    return itcz_from_topography(elevation, config, planetology, n_seasons)


def itcz_from_temperature(
    surface_temperature: np.ndarray,
    config: "WorldConfig",
    planetology: "Planetology | None" = None,
    n_seasons: int = 4,
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
) -> np.ndarray:
    """Estimate the ITCZ probability map from the land/ocean distribution.

    Used on the first simulation pass when no surface-temperature map yet
    exists.  The key insight is that landmasses heat up much more than oceans
    in summer, pulling the ITCZ poleward.  The annual-mean thermal-equator
    latitude at each longitude therefore depends on the land fraction north and
    south of the geographic equator.

    If *elevation* is ``None`` (no topography loaded), the ITCZ follows the
    solar declination over all longitudes.

    Args:
        elevation:   Per-pixel surface elevation (m), or None.  Pixels with
            elevation > 0 are land; pixels <= 0 are ocean.
        config:      World grid configuration.
        planetology: Used to read ``axial_tilt`` (degrees); the maximum
            poleward excursion of the thermal equator scales with axial tilt.
            If None or unset, defaults to _DEFAULT_AXIAL_TILT_DEG.
        n_seasons:   Number of seasonal time-slices per year.

    Returns:
        Float32 array of shape ``(n_seasons, n_pixels)``, values in [0, 1].

    Notes:
        The thermal-equator displacement over land is proportional to the
        signed land-fraction imbalance: delta_lat = tilt * (f_land_N - f_land_S)
        where f_land_N and f_land_S are the land fractions in a latitude band
        north and south of the sub-solar latitude at each longitude.

    TODO:
        1. Obtain per-pixel (lon, lat) from ``core.grid.healpix_pixel_lonlat``.
        2. Build a land mask: ``land = elevation > 0``.
        3. Read axial tilt from ``planetology.axial_tilt`` if available;
           default to ``_DEFAULT_AXIAL_TILT_DEG``.
        4. For each season s and longitude bin:
           a. Compute the solar declination: decl = -tilt * cos(2*pi*s/N).
           b. Compute f_land_N: fraction of land pixels between decl and
              decl + tilt at that longitude.
           c. Compute f_land_S: fraction of land pixels between decl - tilt
              and decl at that longitude.
           d. Thermal-equator latitude: lat_te = decl + tilt*(f_land_N - f_land_S).
        5. For each pixel, compute angular distance from lat_te at the
           corresponding season and longitude.
        6. Apply Gaussian (sigma approx 10 deg) and normalise each season slice.
    """
    if elevation is not None:
        n_pixels = elevation.shape[0]
    else:
        n_pixels = 12 * (4 ** config.base_resolution)

    # --- TODO: implement (see docstring) ---
    # Placeholder: same as the temperature-based path for now.
    return _seasonal_gaussians(n_pixels, n_seasons, config, planetology, sigma_deg=10.0)


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
