"""Topography: multi-resolution elevation histories."""
from __future__ import annotations

from geosim.core.history import History


class TopographyTier:
    """A single spatial-resolution tier of elevation history.

    resolution is the HEALPix order for spherical worlds, or the grid
    dimensions for flat worlds. Each entry in the elevation History is a
    full planet-wide array at that resolution.
    """

    def __init__(self, resolution: int) -> None:
        self.resolution: int = resolution
        self.elevation: History = History()  # metres per pixel

    def __repr__(self) -> str:
        return f"TopographyTier(resolution={self.resolution}, {len(self.elevation)} snapshots)"


class Topography:
    """Multi-resolution elevation history.

    Stores one or more TopographyTier objects, each at a different spatial
    resolution. Coarse tiers cover geological timescales; fine tiers cover
    short windows of detailed simulation (erosion, etc.).

    Fine-resolution windows feed back into coarser tiers by downsampling
    to the coarse pixels that overlap with the fine region.
    """

    def __init__(self) -> None:
        self.tiers: dict[int, TopographyTier] = {}  # keyed by resolution (HEALPix order)

    def get_tier(self, resolution: int) -> TopographyTier:
        """Return the tier for the given resolution, creating it if necessary."""
        if resolution not in self.tiers:
            self.tiers[resolution] = TopographyTier(resolution)
        return self.tiers[resolution]

    def __repr__(self) -> str:
        tier_info = ", ".join(f"order {r}" for r in sorted(self.tiers))
        return f"Topography(tiers: [{tier_info}])"
