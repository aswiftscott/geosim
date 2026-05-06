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
        self.radius: History = History()        # metres
        self.mass: History = History()          # kg
        self.day_length: History = History()    # hours
        self.year_length: History = History()   # days
        self.eccentricity: History = History()  # dimensionless
        self.insolation: History = History()    # W/m^2
        # atmospheric composition and further fields: TBD

    def __repr__(self) -> str:
        fields = ["radius", "mass", "day_length", "year_length", "eccentricity", "insolation"]
        populated = [f for f in fields if len(getattr(self, f)) > 0]
        return f"Planetology(fields set: {populated})"
