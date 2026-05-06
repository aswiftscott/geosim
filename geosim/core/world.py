"""World: the top-level container for a simulated planet."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from geosim.climate.climate import Climate
from geosim.geology.geology import Geology
from geosim.planetology.planetology import Planetology
from geosim.topography.topography import Topography


@dataclass(frozen=True)
class WorldConfig:
    """Immutable configuration for a World, fixed at creation time."""
    grid_type: Literal["spherical", "flat"] = "spherical"
    base_resolution: int = 5  # HEALPix order for spherical; coarsest tier resolution


class World:
    """A simulated planet with an append-only history.

    A World's timeline only ever moves forward. To explore an alternative
    history (e.g. running erosion from a past state), use branch_at() to
    produce a new World object up to that point.
    """

    def __init__(self, name: str, config: WorldConfig) -> None:
        self.name: str = name
        self.config: WorldConfig = config
        self.current_time: float = 0.0  # years

        self.planetology: Planetology | None = None
        self.geology: Geology | None = None
        self.topography: Topography | None = None
        self.climate: Climate | None = None

    def status(self) -> str:
        """Return a human-readable summary of this World's current state."""
        def present(obj: object) -> str:
            return repr(obj) if obj is not None else "none"

        lines = [
            f"World:        {self.name}",
            f"Grid type:    {self.config.grid_type}",
            f"Resolution:   {self.config.base_resolution}",
            f"Current time: {self.current_time:.2f} yr",
            f"Planetology:  {present(self.planetology)}",
            f"Geology:      {present(self.geology)}",
            f"Topography:   {present(self.topography)}",
            f"Climate:      {present(self.climate)}",
        ]
        return "\n".join(lines)

    def __repr__(self) -> str:
        return f"World(name={self.name!r}, t={self.current_time:.2f} yr)"
