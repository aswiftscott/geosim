"""Climate simulation engine.

The public function :func:`simulate_climate` produces one full set of
planet-wide climate fields from the current state of the world.  It is
designed to be called iteratively: pass the previous call's output back in as
``initial_state`` and the algorithm will refine it rather than starting from
scratch.

The actual physics are not yet implemented; every field is currently returned
as a zeroed array of the correct shape so that the surrounding CLI
infrastructure can be developed and tested independently.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from geosim.atmosphere.atmosphere import Atmosphere
    from geosim.core.world import WorldConfig
    from geosim.geology.geology import Geology
    from geosim.planetology.planetology import Planetology
    from geosim.topography.topography import Topography


# All fields produced by a single simulation pass, keyed by the attribute name
# on Climate.  Each value is a 1-D HEALPix array (spherical) or 2-D numpy
# array (flat) of the same shape as the topography elevation map.
ClimateState = dict[str, np.ndarray]

_CLIMATE_FIELDS: list[tuple[str, str]] = [
    ("surface_temperature", "K"),
    ("air_pressure",        "Pa"),
    ("precipitation",       "mm/yr"),
    ("humidity",            "kg/kg"),
]


def _empty_state(n_pixels: int) -> ClimateState:
    """Return a zeroed ClimateState for a grid with *n_pixels* cells."""
    return {field: np.zeros(n_pixels, dtype=np.float32) for field, _ in _CLIMATE_FIELDS}


def simulate_climate(
    config: "WorldConfig",
    topography: "Topography | None",
    geology: "Geology | None",
    planetology: "Planetology | None",
    atmosphere: "Atmosphere | None",
    initial_state: ClimateState | None = None,
) -> ClimateState:
    """Run one pass of the climate simulation and return updated field arrays.

    Parameters
    ----------
    config:
        World configuration (grid type and resolution).
    topography:
        Current topography, used to derive surface elevation for each pixel.
        May be *None* if no topography has been created yet, in which case a
        flat sea-level surface is assumed.
    geology:
        Current geology.  Reserved for future use (rock type, albedo, etc.).
    planetology:
        Orbital and physical parameters (insolation, axial_tilt, eccentricity,
        days_to_perigee, day_length, year_length, mass, radius).
    atmosphere:
        Atmospheric composition (CO₂, CH₄, N₂O, etc.).  Provides
        ``compute_optical_depth()``, ``compute_atmospheric_albedo()``, and
        ``compute_surface_pressure()`` which combine composition with the
        per-pixel humidity from *initial_state*.
    initial_state:
        Output of the previous simulation pass.  When provided the algorithm
        should use these values as starting guesses; when *None* the algorithm
        initialises all fields from scratch.  The current stub ignores this.

    Returns
    -------
    ClimateState
        A dict mapping each climate field name to a numpy array of the same
        spatial shape as the grid (1-D for spherical HEALPix, 2-D for flat).
    """
    # Determine grid size from topography if available, otherwise use the
    # HEALPix formula for the configured order.
    if topography is not None:
        tier = topography.tiers.get(config.base_resolution)
        if tier is not None and len(tier.elevation) > 0:
            elevation = tier.elevation.get(tier.elevation.latest_time)
            n_pixels = elevation.shape[0]
        else:
            n_pixels = 12 * (4 ** config.base_resolution)  # 12 * nside^2
    else:
        n_pixels = 12 * (4 ** config.base_resolution)

    state = _empty_state(n_pixels) if initial_state is None else {
        k: v.copy() for k, v in initial_state.items()
    }

    # --- TODO: implement climate physics here ---
    # Suggested approach (each bullet is a self-contained function to add):
    #
    # 1. Solar irradiance per pixel
    #    - Depends on: planetology (insolation, axial_tilt, days_to_perigee,
    #      eccentricity, year_length, day_length)
    #    - axial_tilt drives seasonal variation and polar night/day
    #    - days_to_perigee + eccentricity controls which hemisphere gets closer
    #      to the star during summer (e.g. Earth: NH winter ≈ perihelion)
    #    - Output: insolation array (W/m²)
    #
    # 2. Surface albedo per pixel
    #    - Depends on: topography (elevation → ice/ocean/land), geology (rock type)
    #    - Output: surface_albedo array (0–1)
    #
    # 3. Humidity first guess
    #    - Use initial_state["humidity"] if available, else zeros
    #    - Humidity drives cloud formation and water-vapour optical depth
    #    - Output: humidity array (kg/kg) — refined in step 7
    #
    # 4. Atmospheric optical depth + albedo (calls Atmosphere methods)
    #    - tau   = atmosphere.compute_optical_depth(t, humidity)   if atmosphere else 0
    #    - atm_a = atmosphere.compute_atmospheric_albedo(t, humidity) if atmosphere else 0
    #    - effective_albedo = atm_a + surface_albedo * (1 − atm_a)
    #    - Output: tau array, effective_albedo array (0–1)
    #
    # 5. Surface temperature (grey-atmosphere energy balance)
    #    - T_eff = (S * (1 − α) / (4σ))^0.25
    #    - T_surface = T_eff * (1 + τ/2)^0.25
    #    - Depends on: insolation (step 1), effective_albedo (step 4), tau (step 4)
    #    - Output: state["surface_temperature"] (K)
    #
    # 6. Surface pressure
    #    - P = atmosphere.compute_surface_pressure(t, planetology) if atmosphere else 0
    #    - Output: state["air_pressure"] (Pa, uniform for now; altitude correction later)
    #
    # 7. Atmospheric circulation (Hadley / Ferrel / polar cells)
    #    - Depends on: surface_temperature, planetology (rotation rate from
    #      day_length, axial_tilt, surface_pressure)
    #    - Output: wind vectors (intermediate; not a stored field yet)
    #
    # 8. Precipitation + humidity update
    #    - Depends on: circulation, surface_temperature, topography (orographic
    #      lifting), atmosphere (available moisture sources)
    #    - Output: state["precipitation"] (mm/yr), state["humidity"] (kg/kg)

    return state
