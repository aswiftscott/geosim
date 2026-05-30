"""CLI handlers for topography commands."""
from __future__ import annotations

from typing import TYPE_CHECKING

from .args import parse_flags
from .help import (
    TOPOGRAPHY_HELP,
    TOPOGRAPHY_ELEVATION_HELP,
    TOPOGRAPHY_ELEVATION_LOAD_HELP,
    TOPOGRAPHY_ELEVATION_DISPLAY_HELP,
    TOPOGRAPHY_ELEVATION_EXPORT_HELP,
)

if TYPE_CHECKING:
    from geosim.core.world import World


def cmd_topography(world: "World", args: list[str]) -> None:
    """Dispatch a topography sub-command."""
    from geosim.topography.topography import Topography

    if not args or args[0] == "status":
        if world.topography is None:
            print("This world has no topography yet. Use 'topography new' to create one.")
        else:
            print(world.topography.status())
        return

    if args[0] == "help":
        print(TOPOGRAPHY_HELP)
        return

    if args[0] == "new":
        if world.topography is not None:
            print("This world already has a topography.")
            return
        world.topography = Topography()
        print("Created new topography.")
        return

    if world.topography is None:
        print("No topography yet. Run 'topography new' first.")
        return

    if args[0] == "elevation":
        field_args = args[1:]
        if not field_args or field_args[0] == "status":
            print(world.topography.status())
        elif field_args[0] in ("help", "--help"):
            print(TOPOGRAPHY_ELEVATION_HELP)
        elif field_args[0] == "load":
            _elevation_load(world, field_args[1:])
        elif field_args[0] == "display":
            _elevation_display(world, field_args[1:])
        elif field_args[0] == "export":
            _elevation_export(world, field_args[1:])
        else:
            print(
                f"Unknown topography elevation sub-command: '{field_args[0]}'. "
                "Type 'topography elevation --help' for usage."
            )
        return

    print(f"Unknown topography sub-command: '{args[0]}'. Type 'topography help' for usage.")


def _elevation_load(world: "World", args: list[str]) -> None:
    if not args or "--help" in args:
        print(TOPOGRAPHY_ELEVATION_LOAD_HELP)
        return

    result = parse_flags(args, {"--min-elev": float, "--max-elev": float})
    if result is None:
        return
    flags, positionals = result

    if not positionals:
        print("Usage: topography elevation load <file> [--min-elev M] [--max-elev M]")
        return

    path = positionals[0]
    min_elev = flags.get("--min-elev", -8000.0)
    max_elev = flags.get("--max-elev",  8000.0)

    if min_elev >= max_elev:
        print("--min-elev must be less than --max-elev.")
        return

    from geosim.topography.loader import load_elevation_png

    print(f"Loading elevation from '{path}' (min={min_elev} m, max={max_elev} m)…")
    try:
        elevation = load_elevation_png(
            path,
            grid_type=world.config.grid_type,
            resolution=world.config.base_resolution,
            min_elev=min_elev,
            max_elev=max_elev,
        )
    except FileNotFoundError:
        print(f"File not found: {path!r}")
        return
    except Exception as exc:
        print(f"Failed to load elevation: {exc}")
        return

    tier = world.topography.get_tier(world.config.base_resolution)
    tier.elevation.append(world.current_time, elevation)

    print(
        f"Loaded elevation map: {elevation.shape[0]:,} pixels, "
        f"range {elevation.min():.0f} – {elevation.max():.0f} m."
    )


def _elevation_display(world: "World", args: list[str]) -> None:
    if "--help" in args:
        print(TOPOGRAPHY_ELEVATION_DISPLAY_HELP)
        return

    tier = world.topography.tiers.get(world.config.base_resolution)
    if tier is None or len(tier.elevation) == 0:
        print("No elevation data at base resolution. Use 'topography elevation load' first.")
        return

    result = parse_flags(args, {"--time": float, "--colormap": str})
    if result is None:
        return
    flags, _ = result

    t = flags.get("--time", tier.elevation.latest_time)
    colormap = flags.get("--colormap", "terrain")

    try:
        elevation = tier.elevation.get(t)
    except ValueError as exc:
        print(f"No elevation data at t={t}: {exc}")
        return

    from geosim.viz.display import display_surface_map

    display_surface_map(
        elevation,
        grid_type=world.config.grid_type,
        resolution=world.config.base_resolution,
        title=f"{world.name} — elevation (t={t:.4g} yr)",
        colormap=colormap,
        units="m",
    )


def _elevation_export(world: "World", args: list[str]) -> None:
    if "--help" in args:
        print(TOPOGRAPHY_ELEVATION_EXPORT_HELP)
        return

    result = parse_flags(
        args,
        {"--time": float, "--min-elev": float, "--max-elev": float},
    )
    if result is None:
        return
    flags, positionals = result

    out_path_arg: str | None = positionals[0] if positionals else None
    t: float | None = flags.get("--time")
    min_elev: float | None = flags.get("--min-elev")
    max_elev: float | None = flags.get("--max-elev")

    from geosim.io.store import exports_dir
    from geosim.core.grid import natural_equirectangular_size, null_surface_map_png

    grid_type  = world.config.grid_type
    resolution = world.config.base_resolution
    tier       = world.topography.tiers.get(resolution)
    has_data   = tier is not None and len(tier.elevation) > 0
    export_root = exports_dir(world.name)

    if not has_data:
        fname = out_path_arg or f"{world.name}_elevation_blank.png"
        out   = export_root / fname if out_path_arg is None else fname
        null_surface_map_png(out, grid_type, resolution)
        nat_h, nat_w = natural_equirectangular_size(grid_type, resolution)
        print(
            f"No elevation data — saved blank template ({nat_w}×{nat_h}) to:\n  {out}\n"
            f"Paint on it and reload with:\n"
            f"  topography elevation load <file> --min-elev -8000 --max-elev 8000"
        )
        return

    snap_t = tier.elevation.latest_time if t is None else t
    try:
        elevation = tier.elevation.get(snap_t)
    except ValueError as exc:
        print(f"No elevation data at t={snap_t}: {exc}")
        return

    from geosim.topography.exporter import export_elevation_png

    t_tag = f"_t{snap_t:.4g}".replace(".", "p") if snap_t != 0.0 else ""
    fname = out_path_arg or f"{world.name}_elevation{t_tag}.png"
    out   = export_root / fname if out_path_arg is None else fname

    used_min, used_max = export_elevation_png(
        elevation, out, grid_type, resolution, min_elev, max_elev
    )
    print(
        f"Exported elevation map to:\n  {out}\n"
        f"Colour scale: black = {used_min:.0f} m, white = {used_max:.0f} m\n"
        f"To reload: topography elevation load <file> "
        f"--min-elev {used_min:.0f} --max-elev {used_max:.0f}"
    )
