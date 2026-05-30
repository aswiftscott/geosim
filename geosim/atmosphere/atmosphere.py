"""Atmosphere: long-timescale atmospheric composition.

Tracks the relative abundance of major atmospheric gases as sparse histories.
Composition changes on geological or biological timescales (volcanic outgassing,
photosynthesis, etc.) but is treated as constant during any single climate
simulation pass.

Derived atmospheric properties — optical depth, surface pressure, and
atmospheric albedo — depend on both composition (stored here) and water-vapour
/ humidity (stored in Climate, because it varies on climate timescales and
varies per surface pixel).  These properties are therefore exposed as
*methods* on this class that accept a humidity array as an optional argument,
rather than being stored as History fields.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from geosim.core.history import History

if TYPE_CHECKING:
    from geosim.planetology.planetology import Planetology


# Greenhouse warming potentials relative to CO₂ (100-year GWP, used to weight
# contributions to optical depth).  Values are approximate and intentionally
# kept as module-level constants so they can be revised without touching the
# class.
_GWP_CO2 = 1.0
_GWP_CH4 = 84.0    # IPCC AR5 (20-yr), simplified here
_GWP_N2O = 265.0


class Atmosphere:
    """Atmospheric composition history for a simulated planet.

    All gas fields are stored as mole fractions (dimensionless, 0–1).
    They should sum to approximately 1.0 at any given time, though this
    is not enforced — untracked minor gases are implicitly assumed to make
    up any remainder.

    ``total_mass`` is the total mass of the atmosphere in kg.  Combined
    with the planetary radius and mass from Planetology, it determines
    surface pressure via ``compute_surface_pressure()``.

    ``FIELDS`` is the authoritative list of settable scalar fields.  Each
    entry is ``(attr_name, unit, description)`` and is consumed by
    ``status()``, ``__repr__``, and the CLI ``set`` command.

    Earth reference values (approximate, modern):
        n2            0.7809
        o2            0.2095
        ar            0.0093
        co2           0.000421  (~421 ppm)
        ch4           1.9e-6    (~1.9 ppm)
        n2o           3.3e-7    (~330 ppb)
        so2           ~1e-9     (background; much higher after large eruptions)
        total_mass    5.15e18 kg
    """

    FIELDS: list[tuple[str, str, str]] = [
        ("n2",         "mol frac", "nitrogen"),
        ("o2",         "mol frac", "oxygen"),
        ("ar",         "mol frac", "argon"),
        ("co2",        "mol frac", "carbon dioxide"),
        ("ch4",        "mol frac", "methane"),
        ("n2o",        "mol frac", "nitrous oxide"),
        ("so2",        "mol frac", "sulfur dioxide"),
        ("total_mass", "kg",       "total atmospheric mass"),
    ]

    def __init__(self) -> None:
        # Bulk gases (by mole fraction)
        self.n2: History = History()    # nitrogen
        self.o2: History = History()    # oxygen  (also drives ozone formation)
        self.ar: History = History()    # argon   (inert; contributes to pressure)

        # Greenhouse gases (by mole fraction)
        self.co2: History = History()   # carbon dioxide
        self.ch4: History = History()   # methane
        self.n2o: History = History()   # nitrous oxide

        # Volcanic / aerosol precursor
        self.so2: History = History()   # sulfur dioxide

        # Total atmospheric mass (kg); determines surface pressure
        self.total_mass: History = History()

    # ------------------------------------------------------------------
    # Status / repr
    # ------------------------------------------------------------------

    def status(self) -> str:
        """Return a human-readable summary of all atmosphere fields."""
        lines = ["Atmosphere:"]
        for name, unit, _ in self.FIELDS:
            h: History = getattr(self, name)
            suffix = f" {unit}" if unit and len(h) > 0 else ""
            lines.append(f"  {name:<14}{h.summary()}{suffix}")
        return "\n".join(lines)

    def __repr__(self) -> str:
        populated = [name for name, _, _ in self.FIELDS if len(getattr(self, name)) > 0]
        return f"Atmosphere(fields set: {populated})"

    # ------------------------------------------------------------------
    # Derived-quantity methods (stubs — physics to be implemented)
    # ------------------------------------------------------------------

    def compute_surface_pressure(
        self,
        t: float,
        planetology: "Planetology",
    ) -> float:
        """Return mean surface pressure in Pa at time *t*.

        Derived from total atmospheric mass, planetary mass (for gravity),
        and planetary radius.

        Formula:
            g = G * M_planet / R²
            P = (M_atm * g) / (4π * R²)
              = G * M_planet * M_atm / (4π * R⁴)

        Returns 0.0 if either total_mass or planetology fields are unset.

        TODO: implement once Planetology.mass and Planetology.radius are
        populated; currently returns 0.0.
        """
        # --- TODO: implement ---
        # G = 6.674e-11  # m³ kg⁻¹ s⁻²
        # if not (len(self.total_mass) > 0
        #         and len(planetology.mass) > 0
        #         and len(planetology.radius) > 0):
        #     return 0.0
        # M_atm  = self.total_mass.get(t)
        # M_planet = planetology.mass.get(t)
        # R      = planetology.radius.get(t)
        # g      = G * M_planet / R**2
        # return M_atm * g / (4 * np.pi * R**2)
        return 0.0

    def compute_dry_optical_depth(self, t: float) -> float:
        """Return the longwave optical depth (τ) from dry greenhouse gases at time *t*.

        Water vapour is excluded; add the humidity contribution separately via
        ``compute_optical_depth()``.

        Simplified model: weight each gas's mole fraction by its GWP relative
        to CO₂, then scale to match Earth (τ_Earth_dry ≈ 0.60, remainder ~0.18
        from water vapour).

        Returns 0.0 if no greenhouse gas data is available.

        TODO: replace with a proper line-by-line or band model.
        """
        # --- TODO: implement ---
        # tau = 0.0
        # earth_co2 = 4.21e-4  # mol frac
        # tau_earth_dry = 0.60
        # for field, gwp in [("co2", _GWP_CO2), ("ch4", _GWP_CH4), ("n2o", _GWP_N2O)]:
        #     h = getattr(self, field)
        #     if len(h) > 0:
        #         tau += (h.get(t) / earth_co2) * gwp * (tau_earth_dry / _GWP_CO2)
        # return tau
        return 0.0

    def compute_optical_depth(
        self,
        t: float,
        humidity: np.ndarray | None = None,
    ) -> float | np.ndarray:
        """Return total longwave optical depth (τ), including water vapour.

        Args:
            t:        Time at which to read composition.
            humidity: Per-pixel specific humidity (kg/kg).  When provided,
                      returns an array of the same shape; when None, returns
                      the scalar dry optical depth.

        TODO: implement water-vapour contribution.
        """
        dry = self.compute_dry_optical_depth(t)
        if humidity is None:
            return dry
        # --- TODO: add per-pixel water-vapour contribution ---
        # water_tau = some_function(humidity)
        # return dry + water_tau
        return np.full(humidity.shape, dry, dtype=np.float32)

    def compute_atmospheric_albedo(
        self,
        t: float,
        humidity: np.ndarray | None = None,
    ) -> float | np.ndarray:
        """Return shortwave atmospheric albedo (0–1), including cloud contribution.

        The dry component comes from SO₂ aerosols and Rayleigh scattering.
        When *humidity* is provided (per-pixel), the cloud contribution is
        added per pixel, returning an array of the same shape.

        Earth reference: ~0.23 total (clouds ≈ 0.19, Rayleigh/aerosol ≈ 0.04).

        TODO: implement SO₂ aerosol and cloud parameterisations.
        """
        # --- TODO: implement ---
        # dry_albedo = rayleigh_albedo() + so2_aerosol_albedo(self.so2.get(t))
        # if humidity is None:
        #     return dry_albedo
        # cloud_albedo = cloud_fraction(humidity) * 0.6  # 0.6 = typical cloud albedo
        # return dry_albedo + (1 - dry_albedo) * cloud_albedo
        if humidity is None:
            return 0.0
        return np.zeros(humidity.shape, dtype=np.float32)
