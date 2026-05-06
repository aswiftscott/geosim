"""Climate: atmospheric and surface climate maps."""
from __future__ import annotations

from geosim.core.history import History


class Climate:
    """Contains climate maps of the planet's surface.

    Each field is a sparse history of planet-wide maps. Maps may represent
    annual means, or seasonal snapshots — the exact temporal structure within
    a single entry is TBD and will depend on how seasonal variation is modelled.
    """

    def __init__(self) -> None:
        self.surface_temperature: History = History()   # K per pixel
        self.air_pressure: History = History()          # Pa per pixel
        self.precipitation: History = History()         # mm/yr per pixel
        # additional fields: TBD

    def __repr__(self) -> str:
        fields = ["surface_temperature", "air_pressure", "precipitation"]
        populated = [f for f in fields if len(getattr(self, f)) > 0]
        return f"Climate(fields set: {populated})"
