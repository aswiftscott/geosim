"""Planetology: basic planetary and orbital properties."""
from __future__ import annotations

from geosim.core.history import History


class Planetology:
    """Contains basic planetary and orbital information.

    All fields are stored as sparse histories so their evolution over time
    can be tracked. Fields that never change will contain a single entry.
    Units are noted in comments; these are conventions only and are not
    enforced by the code.

    ``FIELDS`` is the authoritative list of settable scalar fields.  Each
    entry is ``(attr_name, unit, description)`` and is consumed by
    ``status()``, ``__repr__``, and the CLI ``set`` command.
    """

    FIELDS: list[tuple[str, str, str]] = [
        ("radius",             "m",    "planetary radius"),
        ("mass",               "kg",   "planetary mass"),
        ("day_length",         "hr",   "length of one day"),
        ("year_length",        "days", "length of one year"),
        ("eccentricity",       "",     "orbital eccentricity"),
        ("insolation",         "W/m²", "solar constant"),
        ("axial_tilt",         "°",    "axial tilt"),
        ("days_to_perihelion", "days", "days from NH winter solstice to perihelion"),
    ]

    def __init__(self) -> None:
        self.radius: History = History()              # metres
        self.mass: History = History()                # kg
        self.day_length: History = History()          # hours
        self.year_length: History = History()         # days
        self.eccentricity: History = History()        # dimensionless (0 = circular)
        self.insolation: History = History()          # W/m² (at 1 AU equivalent)
        self.axial_tilt: History = History()          # degrees (0 = no tilt relative to orbital plane)
        self.days_to_perihelion: History = History()     # days from northern winter solstice to orbital perihelion
        # Atmospheric composition is tracked by the separate Atmosphere object.
        # Further orbital / physical fields: TBD

    def status(self) -> str:
        """Return a human-readable summary of all planetology fields."""
        lines = ["Planetology:"]
        for name, unit, _ in self.FIELDS:
            h: History = getattr(self, name)
            suffix = f" {unit}" if unit and len(h) > 0 else ""
            lines.append(f"  {name:<20}{h.summary()}{suffix}")
        return "\n".join(lines)

    def __repr__(self) -> str:
        populated = [name for name, _, _ in self.FIELDS if len(getattr(self, name)) > 0]
        return f"Planetology(fields set: {populated})"
