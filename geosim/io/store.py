"""HDF5-backed persistence for World objects."""
from __future__ import annotations

from pathlib import Path

import h5py

from geosim.core.world import World, WorldConfig

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
    """Persist a World to disk.

    Currently only saves top-level config and current_time.
    Full serialization of Planetology, Geology, Topography, and Climate
    is not yet implemented.
    """
    path = world_path(world.name)
    with h5py.File(path, "w") as f:
        f.attrs["name"] = world.name
        f.attrs["grid_type"] = world.config.grid_type
        f.attrs["base_resolution"] = world.config.base_resolution
        f.attrs["current_time"] = world.current_time
    # TODO: serialize Planetology, Geology, Topography, Climate histories


def load_world(name: str) -> World:
    """Load a World from disk.

    Currently only restores top-level config and current_time.
    """
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
    # TODO: deserialize Planetology, Geology, Topography, Climate histories
    return world
