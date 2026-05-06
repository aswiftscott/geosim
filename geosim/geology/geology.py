"""Geology: tectonic and geological surface maps."""
from __future__ import annotations

from geosim.core.history import History


class Geology:
    """Contains geological maps of the planet's surface.

    Each field is a sparse history of planet-wide maps (HEALPix arrays for
    spherical worlds, 2-D numpy arrays for flat worlds). Only snapshots at
    explicitly simulated timesteps are stored.
    """

    def __init__(self) -> None:
        self.plates: History = History()                    # tectonic plate ID per pixel
        self.orogenies: History = History()                 # orogeny intensity per pixel
        self.subduction_zones: History = History()          # subduction indicator per pixel
        self.large_igneous_provinces: History = History()   # LIP indicator per pixel
        # additional map fields: TBD

    def __repr__(self) -> str:
        fields = ["plates", "orogenies", "subduction_zones", "large_igneous_provinces"]
        populated = [f for f in fields if len(getattr(self, f)) > 0]
        return f"Geology(fields set: {populated})"
