"""HDF5-backed persistence for World objects."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import h5py

from geosim.core.world import World, WorldConfig
from geosim.topography.topography import Topography, TopographyTier

WORLDS_DIR = Path.home() / ".geosim" / "worlds"


def worlds_dir() -> Path:
    WORLDS_DIR.mkdir(parents=True, exist_ok=True)
    return WORLDS_DIR


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


def _save_topography(f: h5py.File, topo: Topography) -> None:
    tg = f.create_group("topography")
    for res, tier in topo.tiers.items():
        rg = tg.create_group(str(res))
        times = tier.elevation.times
        if not times:
            continue
        rg.create_dataset("times", data=np.array(times, dtype=np.float64))
        snapshots = np.stack([tier.elevation.get(t) for t in times])
        rg.create_dataset("elevation", data=snapshots, compression="gzip")


def _load_topography(f: h5py.File) -> Topography:
    topo = Topography()
    tg = f["topography"]
    for res_str in tg:
        rg = tg[res_str]
        if "times" not in rg or "elevation" not in rg:
            continue
        res = int(res_str)
        tier = topo.get_tier(res)
        times = rg["times"][:]
        snapshots = rg["elevation"][:]
        for t, snap in zip(times, snapshots):
            tier.elevation.append(float(t), snap)
    return topo
