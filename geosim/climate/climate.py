"""Climate: atmospheric and surface climate maps."""
from __future__ import annotations

from geosim.core.history import History


class Climate:
    """Contains climate maps of the planet's surface.

    Each field is a sparse history of planet-wide maps. Maps may represent
    annual means, or seasonal snapshots — the exact temporal structure within
    a single entry is TBD and will depend on how seasonal variation is modelled.
    """

    def __init__(self, n_seasons: int = 4) -> None:
        self.n_seasons: int = n_seasons
        """Number of seasonal time-slices per year.

        Every surface-map field in this object stores *n_seasons* maps per
        world-time snapshot — one for each equal-length division of the year.
        Season index 0 corresponds to the northern hemisphere winter solstice.
        """
        self.itcz: History = History()                  # (n_seasons, n_pixels) probability 0–1
        self.insolation: History = History()            # (n_seasons, n_pixels) W/m²
        self.surface_albedo: History = History()        # (n_seasons, n_pixels) dimensionless
        self.optical_depth: History = History()         # (n_seasons, n_pixels) τ (dimensionless)
        self.effective_albedo: History = History()      # (n_seasons, n_pixels) dimensionless
        self.surface_temperature: History = History()   # (n_seasons, n_pixels) K
        self.air_pressure: History = History()          # (n_seasons, n_pixels) Pa
        self.precipitation: History = History()         # (n_seasons, n_pixels) mm/yr
        self.humidity: History = History()              # (n_seasons, n_pixels) kg/kg

    def status(self) -> str:
        """Return a human-readable summary of all climate map fields."""
        fields = [
            ("itcz",                "prob"),
            ("insolation",          "W/m²"),
            ("surface_albedo",      ""),
            ("optical_depth",       "τ"),
            ("effective_albedo",    ""),
            ("surface_temperature", "K"),
            ("air_pressure",        "Pa"),
            ("precipitation",       "mm/yr"),
            ("humidity",            "kg/kg"),
        ]
        lines = [f"Climate (n_seasons={self.n_seasons}):"]
        for name, unit in fields:
            h: History = getattr(self, name)
            suffix = f" {unit}" if unit and len(h) > 0 else ""
            lines.append(f"  {name:<24}{h.summary()}{suffix}")
        return "\n".join(lines)

    def __repr__(self) -> str:
        fields = [
            "itcz", "insolation", "surface_albedo", "optical_depth", "effective_albedo",
            "surface_temperature", "air_pressure", "precipitation", "humidity",
        ]
        populated = [f for f in fields if len(getattr(self, f)) > 0]
        return f"Climate(n_seasons={self.n_seasons}, fields set: {populated})"
