"""Planetology: basic planetary and orbital properties."""
from __future__ import annotations

from geosim.core.history import History


class Planetology:
    """Contains basic planetary and orbital information.

    All fields are stored as sparse histories so their evolution over time
    can be tracked. Fields that never change will contain a single entry.
    Units are noted in comments; these are conventions only and are not
    enforced by the code.
    """

    def __init__(self) -> None:
        self.radius: History = History()              # metres
        self.mass: History = History()                # kg
        self.day_length: History = History()          # hours
        self.year_length: History = History()         # days
        self.eccentricity: History = History()        # dimensionless (0 = circular)
        self.insolation: History = History()          # W/m² (at 1 AU equivalent)
        self.axial_tilt: History = History()          # degrees (0 = no tilt relative to orbital plane)
        self.days_to_perigee: History = History()     # days from northern winter solstice to orbital perigee
        # Atmospheric composition is tracked by the separate Atmosphere object.
        # Further orbital / physical fields: TBD

    def status(self) -> str:
        """Return a human-readable summary of all planetology fields.
            days_to_perigee is how many days after the northern hemisphere winter solstice perigee occurs"""
        fields = [
            ("radius",           "m"),
            ("mass",             "kg"),
            ("day_length",       "hr"),
            ("year_length",      "days"),
            ("eccentricity",     ""),
            ("insolation",       "W/m²"),
            ("axial_tilt",       "°"),
            ("days_to_perigee",  "days"),
        ]
        lines = ["Planetology:"]
        for name, unit in fields:
            h: History = getattr(self, name)
            suffix = f" {unit}" if unit and len(h) > 0 else ""
            lines.append(f"  {name:<20}{h.summary()}{suffix}")
        return "\n".join(lines)

    def __repr__(self) -> str:
        fields = [
            "radius", "mass", "day_length", "year_length",
            "eccentricity", "insolation", "axial_tilt", "days_to_perigee",
        ]
        populated = [f for f in fields if len(getattr(self, f)) > 0]
        return f"Planetology(fields set: {populated})"
