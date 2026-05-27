"""HDF5-backed persistence for World objects."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import h5py

from geosim.core.world import World, WorldConfig
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
    # TODO: serialize Planetology, Geology, Climate histories


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
    # TODO: deserialize Planetology, Geology, Climate histories
    return world


# ---------------------------------------------------------------------------
# Generic surface-map History serialization
# ---------------------------------------------------------------------------
# Each sub-object (Topography, Geology, Climate, …) stores its fields as
# History objects containing planet-wide numpy arrays.  The two helpers below
# handle the common case: a named field whose History entries are all arrays
# of the same shape.  Sub-object save/load functions enumerate their fields
# and delegate to these helpers.

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
        snaps = raw  # legacy: data was stored as float directly

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
