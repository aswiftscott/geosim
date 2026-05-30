"""HDF5-backed persistence for World objects."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import h5py

from geosim.atmosphere.atmosphere import Atmosphere
from geosim.climate.climate import Climate
from geosim.core.world import World, WorldConfig
from geosim.geology.geology import Geology
from geosim.planetology.planetology import Planetology
from geosim.topography.topography import Topography, TopographyTier

WORLDS_DIR = Path.home() / ".geosim" / "worlds"
EXPORTS_DIR = Path.home() / ".geosim" / "exports"


def worlds_dir() -> Path:
    WORLDS_DIR.mkdir(parents=True, exist_ok=True)
    return WORLDS_DIR


def exports_dir(world_name: str) -> Path:
    d = EXPORTS_DIR / world_name
    d.mkdir(parents=True, exist_ok=True)
    return d


def world_path(name: str) -> Path:
    return worlds_dir() / f"{name}.h5"


def world_exists(name: str) -> bool:
    return world_path(name).exists()


def list_worlds() -> list[str]:
    return sorted(p.stem for p in worlds_dir().glob("*.h5"))


def save_world(world: World) -> None:
    """Persist a World to disk."""
    path = world_path(world.name)
    with h5py.File(path, "w") as f:
        f.attrs["name"] = world.name
        f.attrs["grid_type"] = world.config.grid_type
        f.attrs["base_resolution"] = world.config.base_resolution
        f.attrs["current_time"] = world.current_time

        if world.topography is not None:
            _save_topography(f, world.topography)
        if world.planetology is not None:
            _save_planetology(f, world.planetology)
        if world.geology is not None:
            _save_geology(f, world.geology)
        if world.atmosphere is not None:
            _save_atmosphere(f, world.atmosphere)
        if world.climate is not None:
            _save_climate(f, world.climate)


def load_world(name: str) -> World:
    """Load a World from disk."""
    path = world_path(name)
    if not path.exists():
        raise FileNotFoundError(f"No world file found at {path}")
    with h5py.File(path, "r") as f:
        config = WorldConfig(
            grid_type=f.attrs["grid_type"],
            base_resolution=int(f.attrs["base_resolution"]),
        )
        world = World(name=str(f.attrs["name"]), config=config)
        world.current_time = float(f.attrs["current_time"])

        if "topography" in f:
            world.topography = _load_topography(f)
        if "planetology" in f:
            world.planetology = _load_planetology(f)
        if "geology" in f:
            world.geology = _load_geology(f)
        if "atmosphere" in f:
            world.atmosphere = _load_atmosphere(f)
        if "climate" in f:
            world.climate = _load_climate(f)
    return world


# ---------------------------------------------------------------------------
# Generic History serialization helpers
# ---------------------------------------------------------------------------

def save_scalar_history(group: h5py.Group, field: str, history) -> None:
    """Write a History of scalar (float) values to an HDF5 group.

    Creates two datasets inside *group*:
      ``<field>/times``  — 1-D float64 array of recorded timestamps
      ``<field>/values`` — 1-D float64 array of corresponding scalar values

    Does nothing if the History is empty.
    """
    times = history.times
    if not times:
        return
    fg = group.require_group(field)
    fg.create_dataset("times",  data=np.array(times, dtype=np.float64))
    fg.create_dataset("values", data=np.array(
        [history.get(t) for t in times], dtype=np.float64
    ))


def load_scalar_history(group: h5py.Group, field: str, history) -> None:
    """Read a History of scalar values from an HDF5 group."""
    if field not in group:
        return
    fg = group[field]
    if "times" not in fg or "values" not in fg:
        return
    for t, v in zip(fg["times"][:], fg["values"][:]):
        history.append(float(t), float(v))


def save_map_history(group: h5py.Group, field: str, history) -> None:
    """Write a History of surface-map arrays to an HDF5 group.

    Creates three objects inside *group*:
      ``<field>/times``     — 1-D float64 array of recorded timestamps
      ``<field>/snapshots`` — uint8 array, gzip-compressed; original shape
                              prefixed by a snapshot axis (n_snapshots, ...)
    The ``snapshots`` dataset carries two scalar attributes:
      ``scale``  — multiply decoded uint8 values by this to recover the
                   original units  (float64)
      ``offset`` — add this after scaling  (float64)

    The encoding is:
      stored = round((value − offset) / scale)   clamped to [0, 255]
      value  = stored × scale + offset

    A single global scale/offset is computed across all snapshots so that
    values remain comparable across time.  Max round-trip error is
    ``scale / 2`` per pixel.

    Does nothing if the History is empty.
    """
    times = history.times
    if not times:
        return
    fg = group.require_group(field)
    fg.create_dataset("times", data=np.array(times, dtype=np.float64))

    snapshots = np.stack([history.get(t) for t in times]).astype(np.float32)

    s_min = float(snapshots.min())
    s_max = float(snapshots.max())
    s_range = s_max - s_min
    scale  = s_range / 255.0 if s_range > 0.0 else 1.0
    offset = s_min

    uint8_data = np.clip(
        np.round((snapshots - offset) / scale), 0, 255
    ).astype(np.uint8)

    ds = fg.create_dataset("snapshots", data=uint8_data, compression="gzip")
    ds.attrs["scale"]  = np.float64(scale)
    ds.attrs["offset"] = np.float64(offset)


def load_map_history(group: h5py.Group, field: str, history) -> None:
    """Read a History of surface-map arrays from an HDF5 group.

    Reads the datasets written by :func:`save_map_history` and appends
    each (time, snapshot) pair into *history* in chronological order.
    If the ``snapshots`` dataset carries ``scale``/``offset`` attributes it
    is decoded from uint8 back to float32; otherwise the raw data is used
    (backwards-compatible with any pre-compression saves).
    """
    if field not in group:
        return
    fg = group[field]
    if "times" not in fg or "snapshots" not in fg:
        return

    snaps_ds = fg["snapshots"]
    raw = snaps_ds[:]

    if raw.dtype == np.uint8 and "scale" in snaps_ds.attrs:
        scale  = float(snaps_ds.attrs["scale"])
        offset = float(snaps_ds.attrs["offset"])
        snaps  = raw.astype(np.float32) * scale + offset
    else:
        snaps = raw

    for t, snap in zip(fg["times"][:], snaps):
        history.append(float(t), snap)


# ---------------------------------------------------------------------------
# Topography serialization
# ---------------------------------------------------------------------------

def _save_topography(f: h5py.File, topo: Topography) -> None:
    tg = f.create_group("topography")
    for res, tier in topo.tiers.items():
        rg = tg.create_group(str(res))
        save_map_history(rg, "elevation", tier.elevation)


def _load_topography(f: h5py.File) -> Topography:
    topo = Topography()
    for res_str in f["topography"]:
        rg = f["topography"][res_str]
        tier = topo.get_tier(int(res_str))
        load_map_history(rg, "elevation", tier.elevation)
    return topo


# ---------------------------------------------------------------------------
# Planetology serialization
# ---------------------------------------------------------------------------

_PLANETOLOGY_FIELDS = [name for name, _, _ in Planetology.FIELDS]


def _save_planetology(f: h5py.File, pl: Planetology) -> None:
    pg = f.create_group("planetology")
    for field in _PLANETOLOGY_FIELDS:
        save_scalar_history(pg, field, getattr(pl, field))


def _load_planetology(f: h5py.File) -> Planetology:
    pl = Planetology()
    pg = f["planetology"]
    for field in _PLANETOLOGY_FIELDS:
        load_scalar_history(pg, field, getattr(pl, field))
    return pl


# ---------------------------------------------------------------------------
# Geology serialization
# ---------------------------------------------------------------------------

_GEOLOGY_MAP_FIELDS = [
    "plates", "orogenies", "subduction_zones", "large_igneous_provinces",
]


def _save_geology(f: h5py.File, geo: Geology) -> None:
    gg = f.create_group("geology")
    for field in _GEOLOGY_MAP_FIELDS:
        save_map_history(gg, field, getattr(geo, field))


def _load_geology(f: h5py.File) -> Geology:
    geo = Geology()
    gg = f["geology"]
    for field in _GEOLOGY_MAP_FIELDS:
        load_map_history(gg, field, getattr(geo, field))
    return geo


# ---------------------------------------------------------------------------
# Atmosphere serialization
# ---------------------------------------------------------------------------

_ATMOSPHERE_FIELDS = [name for name, _, _ in Atmosphere.FIELDS]


def _save_atmosphere(f: h5py.File, atm: Atmosphere) -> None:
    ag = f.create_group("atmosphere")
    for field in _ATMOSPHERE_FIELDS:
        save_scalar_history(ag, field, getattr(atm, field))


def _load_atmosphere(f: h5py.File) -> Atmosphere:
    atm = Atmosphere()
    ag = f["atmosphere"]
    for field in _ATMOSPHERE_FIELDS:
        load_scalar_history(ag, field, getattr(atm, field))
    return atm


# ---------------------------------------------------------------------------
# Climate serialization
# ---------------------------------------------------------------------------

_CLIMATE_MAP_FIELDS = [
    "itcz", "currents", "ocean_temperature", "pressure", "winds",
    "precipitation", "albedo", "cloud_cover", "sunlight",
    "temperature", "pet", "aet",
]


def _save_climate(f: h5py.File, climate: Climate) -> None:
    cg = f.create_group("climate")
    cg.attrs["n_seasons"] = climate.n_seasons
    for field in _CLIMATE_MAP_FIELDS:
        save_map_history(cg, field, getattr(climate, field))


def _load_climate(f: h5py.File) -> Climate:
    cg = f["climate"]
    climate = Climate(n_seasons=int(cg.attrs["n_seasons"]))
    for field in _CLIMATE_MAP_FIELDS:
        load_map_history(cg, field, getattr(climate, field))
    return climate
