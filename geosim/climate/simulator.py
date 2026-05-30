"""Climate simulation engine.

Each simulation step is exposed as both a standalone function and a CLI
command (``climate <step> compute``).  ``simulate_climate`` is a thin wrapper
that runs all steps in order.

Step order and the Climate fields each step produces:

1.  itcz        - Find ITCZ by identifying thermal equator (if available)
                  (produces climate.itcz)
2.  currents    - Simulate ocean currents/temperature from ITCZ and surface sunlight (if available)
                  (produces climate.currents, climate.ocean_temperature)
3.  pressure    - Approximate pressure and prevailing winds from ocean temperature and topography
                  (produces climate.pressure, climate.winds)
4.  precipitation - Simulate precipitation from pressure, winds, ocean temperature and topography
                  (produces climate.precipitation)
5.  albedo      - Approximate surface albedo from Koppen climate zone and geology (if available)
                  (produces climate.albedo)
6.  clouds      - Approximate cloud cover from Koppen climate zone, topography, and pressure/AET (if available)
                  (produces climate.cloud_cover)
7.  sunlight    - Compute surface sunlight from planetology variables and cloud cover
                  (produces climate.sunlight)
8.  temperature - Simulate temperature from surface sunlight, surface albedo, precipitation, and topography
                  (produces climate.temperature)
9.  evaporation - Calculate PET and AET from temperature, available sunlight, and precipitation
                  (produces climate.pet, climate.aet)
10. koppen      - Find Koppen Climate zones from temperature, precipitation, etc
                  (produces a map for each Koppen zone - do not create yet)
11. hersfeldt    - Find hersfeldt climate zones from temperatures, PET, AET, etc
                  (produces a map for each hersfeldt zone - do not create yet)
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from geosim.core.world import World

# ---------------------------------------------------------------------------
# Field registry
# ---------------------------------------------------------------------------

# All Climate fields, in the order they appear in status() output.
# (field_name, unit_label)
_CLIMATE_FIELDS: list[tuple[str, str]] = [
    ("itcz",              "prob"),
    ("currents",          ""),
    ("ocean_temperature", "K"),
    ("pressure",          "Pa"),
    ("winds",             "m/s"),
    ("precipitation",     "mm/yr"),
    ("albedo",            ""),
    ("cloud_cover",       ""),
    ("sunlight",          "W/m2"),
    ("temperature",       "K"),
    ("pet",               "mm/yr"),
    ("aet",               "mm/yr"),
]

# Each step name maps to the Climate field(s) it produces.
_STEP_OUTPUTS: dict[str, list[str]] = {
    "itcz":          ["itcz"],
    "currents":      ["currents", "ocean_temperature"],
    "pressure":      ["pressure", "winds"],
    "precipitation": ["precipitation"],
    "albedo":        ["albedo"],
    "clouds":        ["cloud_cover"],
    "sunlight":      ["sunlight"],
    "temperature":   ["temperature"],
    "evaporation":   ["pet", "aet"],
    "koppen":        [],
    "hersfeldt":      [],
}

# Canonical step order for simulate_climate.
_STEP_ORDER: list[str] = [
    "itcz",
    "currents",
    "pressure",
    "precipitation",
    "albedo",
    "clouds",
    "sunlight",
    "temperature",
    "evaporation",
    "koppen",
    "hersfeldt",
]

# ---------------------------------------------------------------------------
# Working-state helpers
# ---------------------------------------------------------------------------

ClimateState = dict[str, np.ndarray]


def _n_pixels(world: "World") -> int:
    """Return the number of surface pixels for this world's base resolution."""
    if world.topography is not None:
        tier = world.topography.tiers.get(world.config.base_resolution)
        if tier is not None and len(tier.elevation) > 0:
            return tier.elevation.get(tier.elevation.latest_time).shape[0]
    return 12 * (4 ** world.config.base_resolution)


def _empty_state(n_pixels: int, n_seasons: int) -> ClimateState:
    """Return a zeroed ClimateState; each field is shape (n_seasons, n_pixels)."""
    return {
        field: np.zeros((n_seasons, n_pixels), dtype=np.float32)
        for field, _ in _CLIMATE_FIELDS
    }


def _load_working_state(world: "World") -> ClimateState:
    """Load the latest snapshot of every Climate field into a working-state dict.

    Fields with no history yet are left as zeros.
    """
    n_pixels = _n_pixels(world)
    state = _empty_state(n_pixels, world.climate.n_seasons)
    for field, _ in _CLIMATE_FIELDS:
        h = getattr(world.climate, field)
        if len(h) > 0:
            state[field] = h.get(h.latest_time).copy()
    return state


def _commit_fields(world: "World", state: ClimateState, fields: list[str]) -> None:
    """Append *fields* from *state* to the corresponding Climate histories."""
    t = world.current_time
    for field in fields:
        getattr(world.climate, field).append(t, state[field])


# ---------------------------------------------------------------------------
# Individual step compute functions
# ---------------------------------------------------------------------------

def _step_itcz(world: "World", state: ClimateState) -> None:
    from geosim.climate.itcz import compute_itcz
    prior_temp = state["temperature"]
    # Treat an all-zero temperature array (first-pass default) as absent
    if not np.any(prior_temp):
        prior_temp = None
    state["itcz"] = compute_itcz(
        config=world.config,
        topography=world.topography,
        planetology=world.planetology,
        surface_temperature=prior_temp,
        n_seasons=world.climate.n_seasons,
    )


def _step_currents(world: "World", state: ClimateState) -> None:
    # TODO: simulate ocean currents and ocean surface temperature.
    # Depends on: state["itcz"], state["sunlight"], topography (ocean mask).
    # Output: state["currents"] (m/s vector proxy), state["ocean_temperature"] (K).
    # Both shape (n_seasons, n_pixels).
    pass


def _step_pressure(world: "World", state: ClimateState) -> None:
    # TODO: approximate surface pressure and prevailing winds.
    # Depends on: state["ocean_temperature"], topography (elevation).
    # Output: state["pressure"] (Pa), state["winds"] (m/s), both (n_seasons, n_pixels).
    pass


def _step_precipitation(world: "World", state: ClimateState) -> None:
    # TODO: simulate precipitation from atmospheric circulation and orographic lifting.
    # Depends on: state["itcz"], state["pressure"], state["winds"],
    #             state["ocean_temperature"], topography (elevation).
    # Output: state["precipitation"] (mm/yr), shape (n_seasons, n_pixels).
    pass


def _step_albedo(world: "World", state: ClimateState) -> None:
    # TODO: approximate surface albedo from Koppen climate zone and geology.
    # Depends on: topography (elevation -> ocean/land/ice), geology (rock type).
    # If a prior Koppen map exists, use it to refine the albedo estimate.
    # Output: state["albedo"], shape (n_seasons, n_pixels), dimensionless 0–1.
    pass


def _step_clouds(world: "World", state: ClimateState) -> None:
    # TODO: approximate cloud cover fraction.
    # Depends on: topography, state["pressure"], state["aet"] (if available).
    # If a prior Koppen map exists, use it to refine the cloud fraction.
    # Output: state["cloud_cover"], shape (n_seasons, n_pixels), dimensionless 0–1.
    pass


def _step_sunlight(world: "World", state: ClimateState) -> None:
    # TODO: compute surface solar irradiance after cloud attenuation.
    # S_surface = S_top * (1 - cloud_cover * cloud_albedo)
    # S_top derived from planetology (insolation, axial_tilt, eccentricity,
    #   days_to_perihelion, year_length) and pixel latitude (HEALPix grid).
    # Depends on: state["cloud_cover"], planetology.
    # Output: state["sunlight"] (W/m²), shape (n_seasons, n_pixels).
    pass


def _step_temperature(world: "World", state: ClimateState) -> None:
    # TODO: simulate surface temperature via energy balance.
    # Depends on: state["sunlight"], state["albedo"], state["precipitation"],
    #             topography (elevation for lapse rate).
    # Output: state["temperature"] (K), shape (n_seasons, n_pixels).
    pass


def _step_evaporation(world: "World", state: ClimateState) -> None:
    # TODO: calculate potential and actual evapotranspiration.
    # PET from Penman-Monteith or Thornthwaite using state["temperature"] and state["sunlight"].
    # AET = min(PET, available water from state["precipitation"]).
    # Output: state["pet"] (mm/yr), state["aet"] (mm/yr), both (n_seasons, n_pixels).
    pass


def _step_koppen(world: "World", state: ClimateState) -> None:
    # TODO: classify Koppen climate zones.
    # Depends on: state["temperature"], state["precipitation"].
    # Output: (do not create Climate fields yet — classification maps TBD).
    pass


def _step_hersfeldt(world: "World", state: ClimateState) -> None:
    # TODO: classify hersfeldt climate zones.
    # Depends on: state["temperature"], state["pet"], state["aet"].
    # Output: (do not create Climate fields yet — classification maps TBD).
    pass


_STEP_FUNCTIONS = {
    "itcz":          _step_itcz,
    "currents":      _step_currents,
    "pressure":      _step_pressure,
    "precipitation": _step_precipitation,
    "albedo":        _step_albedo,
    "clouds":        _step_clouds,
    "sunlight":      _step_sunlight,
    "temperature":   _step_temperature,
    "evaporation":   _step_evaporation,
    "koppen":        _step_koppen,
    "hersfeldt":      _step_hersfeldt,
}


def _run_step_on_state(step: str, world: "World", state: ClimateState) -> None:
    """Dispatch to the named step function, mutating *state* in-place."""
    fn = _STEP_FUNCTIONS.get(step)
    if fn is None:
        raise ValueError(f"Unknown simulation step: {step!r}")
    fn(world, state)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_step(world: "World", step: str) -> None:
    """Run a single named simulation step and save its output(s) to world.climate.

    Reads the latest climate state from *world.climate*, computes the named
    step, then appends the step's output field(s) to their respective Climate
    histories at ``world.current_time``.

    Args:
        world: The open World.  ``world.climate`` must not be None.
        step:  One of the keys in ``_STEP_ORDER`` (e.g. ``"itcz"``).
    """
    state = _load_working_state(world)
    _run_step_on_state(step, world, state)
    _commit_fields(world, state, _STEP_OUTPUTS[step])


def simulate_climate(world: "World", n_iterations: int = 1) -> None:
    """Run all simulation steps in order and save results to world.climate.

    When *n_iterations* > 1 the full step sequence is repeated that many
    times in memory, with each pass seeded from the previous pass's output.
    Only the final result is committed to the Climate histories.

    Args:
        world:         The open World.  ``world.climate`` must not be None.
        n_iterations:  Number of full passes to run before committing.
    """
    state = _load_working_state(world)

    for iteration in range(n_iterations):
        if n_iterations > 1:
            print(f"  Pass {iteration + 1}/{n_iterations}...")
        for step in _STEP_ORDER:
            _run_step_on_state(step, world, state)

    all_fields = [field for field, _ in _CLIMATE_FIELDS]
    _commit_fields(world, state, all_fields)
