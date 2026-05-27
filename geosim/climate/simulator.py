"""Climate simulation engine.

Each simulation step is exposed as both a standalone function and a CLI
command (``climate <step> compute``).  ``simulate_climate`` is a thin wrapper
that runs all steps in order.

Step order and the Climate fields each step produces:

  1. itcz            -> climate.itcz
  2. insolation      -> climate.insolation
  3. surface_albedo  -> climate.surface_albedo
  4. optical_depth   -> climate.optical_depth, climate.effective_albedo
  5. temperature     -> climate.surface_temperature
  6. pressure        -> climate.air_pressure
  7. precipitation   -> climate.precipitation
  8. humidity        -> climate.humidity
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
    ("itcz",                "prob"),
    ("insolation",          "W/m2"),
    ("surface_albedo",      ""),
    ("optical_depth",       "tau"),
    ("effective_albedo",    ""),
    ("surface_temperature", "K"),
    ("air_pressure",        "Pa"),
    ("precipitation",       "mm/yr"),
    ("humidity",            "kg/kg"),
]

# Each step name maps to the Climate field(s) it produces.
_STEP_OUTPUTS: dict[str, list[str]] = {
    "itcz":          ["itcz"],
    "insolation":    ["insolation"],
    "surface_albedo": ["surface_albedo"],
    "optical_depth": ["optical_depth", "effective_albedo"],
    "temperature":   ["surface_temperature"],
    "pressure":      ["air_pressure"],
    "precipitation": ["precipitation"],
    "humidity":      ["humidity"],
}

# Canonical step order for simulate_climate.
_STEP_ORDER: list[str] = [
    "itcz",
    "insolation",
    "surface_albedo",
    "optical_depth",
    "temperature",
    "pressure",
    "precipitation",
    "humidity",
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
    prior_temp = state["surface_temperature"]
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


def _step_insolation(world: "World", state: ClimateState) -> None:
    # TODO: compute per-pixel, per-season solar irradiance (W/m2).
    # Depends on: planetology (insolation, axial_tilt, days_to_perihelion,
    #   eccentricity, year_length, day_length).
    # Output: state["insolation"], shape (n_seasons, n_pixels).
    pass


def _step_surface_albedo(world: "World", state: ClimateState) -> None:
    # TODO: compute per-pixel surface albedo from land/ocean/ice classification.
    # Depends on: topography (elevation -> ocean/land/ice), geology (rock type).
    # Output: state["surface_albedo"], shape (n_seasons, n_pixels).
    pass


def _step_optical_depth(world: "World", state: ClimateState) -> None:
    # TODO: compute per-pixel longwave optical depth and effective albedo.
    # tau = atmosphere.compute_optical_depth(t, humidity)
    # atm_a = atmosphere.compute_atmospheric_albedo(t, humidity)
    # effective_albedo = atm_a + surface_albedo * (1 - atm_a)
    # Output: state["optical_depth"], state["effective_albedo"], both (n_seasons, n_pixels).
    pass


def _step_temperature(world: "World", state: ClimateState) -> None:
    # TODO: grey-atmosphere energy balance.
    # T_eff = (S * (1 - alpha) / (4 * sigma))^0.25
    # T_surface = T_eff * (1 + tau/2)^0.25
    # Depends on: state["insolation"], state["effective_albedo"], state["optical_depth"].
    # Output: state["surface_temperature"], shape (n_seasons, n_pixels).
    pass


def _step_pressure(world: "World", state: ClimateState) -> None:
    # TODO: surface pressure from atmospheric mass and planetary gravity.
    # P = atmosphere.compute_surface_pressure(t, planetology)
    # Output: state["air_pressure"], shape (n_seasons, n_pixels).
    pass


def _step_precipitation(world: "World", state: ClimateState) -> None:
    # TODO: precipitation from atmospheric circulation and orographic lifting.
    # Depends on: state["itcz"], state["surface_temperature"], topography.
    # Output: state["precipitation"], shape (n_seasons, n_pixels).
    pass


def _step_humidity(world: "World", state: ClimateState) -> None:
    # TODO: specific humidity from precipitation and evaporation.
    # Depends on: state["precipitation"], state["surface_temperature"].
    # Output: state["humidity"], shape (n_seasons, n_pixels).
    pass


_STEP_FUNCTIONS = {
    "itcz":           _step_itcz,
    "insolation":     _step_insolation,
    "surface_albedo": _step_surface_albedo,
    "optical_depth":  _step_optical_depth,
    "temperature":    _step_temperature,
    "pressure":       _step_pressure,
    "precipitation":  _step_precipitation,
    "humidity":       _step_humidity,
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
