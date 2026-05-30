"""Interactive CLI for geosim."""
from __future__ import annotations

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.styles import Style

from geosim.climate.climate import Climate
from geosim.core.world import World, WorldConfig
from geosim.geology.geology import Geology
from geosim.io import store
from geosim.planetology.planetology import Planetology
from geosim.topography.topography import Topography

_STYLE = Style.from_dict({"prompt": "ansigreen bold"})

_GLOBAL_COMMANDS = ["new", "open", "list", "help", "exit", "quit"]
_WORLD_COMMANDS = ["status", "planetology", "geology", "topography", "climate", "close", "branch", "help", "exit", "quit"]

_GLOBAL_HELP = """\
Commands:
  new <name>          create a new world
  open <name>         open an existing world
  list                list all saved worlds
  help                show this message
  exit / quit         exit geosim"""

_WORLD_HELP = """\
Commands (world open):
  status                       show world summary
  planetology [help]           planetology commands
  geology [help]               geology commands
  topography [help]            topography commands
  climate [help]               climate commands
  branch <t> <name>            create a new world branching from time t
  close                        close current world without exiting
  help                         show this message
  exit / quit                  exit geosim"""

_PLANETOLOGY_HELP = """\
Planetology commands:
  planetology                  show planetology details
  planetology new              create a new empty planetology
  planetology help             show this message"""

_GEOLOGY_HELP = """\
Geology commands:
  geology                      show geology details
  geology new                  create a new empty geology
  geology help                 show this message"""

_TOPOGRAPHY_HELP = """\
Topography commands:
  topography                   show topography details
  topography new               create a new empty topography
  topography elevation --help  show elevation sub-command help
  topography elevation load <file>          load elevation from a PNG file
    [--min-elev <m>] [--max-elev <m>]       (defaults: -8000 / 8000 m)
  topography elevation display              display elevation map
    [--time <t>] [--colormap <cmap>]        (default: latest snapshot, colormap 'terrain')
  topography elevation export [<file>]      export elevation map as greyscale PNG
    [--time <t>] [--min-elev <m>] [--max-elev <m>]  (defaults: latest snapshot, auto-scaled)
  topography help              show this message"""

_CLIMATE_HELP = """\
Climate commands:
  climate                      show climate details
  climate new                  create a new empty climate
  climate help                 show this message"""

_TOPOGRAPHY_ELEVATION_HELP = """\
topography elevation <action> [options]

Actions:
  load <file>    load elevation from a greyscale PNG (equirectangular projection)
  display        display the elevation map in a window
  export [file]  save the elevation map as a greyscale PNG

Run 'topography elevation <action> --help' for full details on each action."""

_TOPOGRAPHY_ELEVATION_LOAD_HELP = """\
topography elevation load <file> [--min-elev <m>] [--max-elev <m>] [--max-pixels <n>]

  Load an elevation map from a greyscale PNG file.
  The PNG must use an equirectangular (plate carrée) projection.
  Pixel brightness is linearly mapped to elevation:
    black (0)   → --min-elev
    white (255) → --max-elev

Arguments:
  <file>             path to the input PNG (any resolution, any aspect ratio)

Options:
  --min-elev <m>     elevation value mapped to black  (default: -8000)
  --max-elev <m>     elevation value mapped to white  (default:  8000)
  --max-pixels <n>   if the PNG exceeds this pixel count it is scaled down
                     proportionally before loading  (default: 100000000)
                     pass 0 to disable the limit entirely

Example:
  topography elevation load earth.png --min-elev -11000 --max-elev 8850
  topography elevation load big_map.png --max-pixels 50000000"""

_TOPOGRAPHY_ELEVATION_DISPLAY_HELP = """\
topography elevation display [--time <t>] [--colormap <name>]

  Display the elevation map in an interactive matplotlib window.
  Requires elevation data to have been loaded first.

  By default, a custom elevation colormap is used with a hard colour break
  at sea level (0 m): deep water is dark blue/black, shallow water is light
  blue, and land transitions from green through brown to white.
  Specifying --colormap disables the sea-level break and uses a plain
  matplotlib colormap instead.

Options:
  --time <t>        snapshot time to display (default: latest)
  --colormap <name> use a plain matplotlib colormap (disables sea-level break)

Example:
  topography elevation display
  topography elevation display --colormap viridis"""

_TOPOGRAPHY_ELEVATION_EXPORT_HELP = """\
topography elevation export [<file>] [--time <t>] [--min-elev <m>] [--max-elev <m>]

  Save the elevation map as a greyscale PNG.
  If no elevation data exists, a blank mid-grey template is saved instead.

Arguments:
  <file>          output file path (default: exports/<name>/<name>_elevation.png)

Options:
  --time <t>      snapshot time to export (default: latest)
  --min-elev <m>  elevation mapped to black  (default: auto, data minimum)
  --max-elev <m>  elevation mapped to white  (default: auto, data maximum)

Example:
  topography elevation export my_map.png --min-elev -8000 --max-elev 8000"""


class GeoSimREPL:
    def __init__(self) -> None:
        self._world: World | None = None
        self._session: PromptSession = PromptSession()

    @property
    def _prompt(self) -> str:
        if self._world:
            return f"geosim [{self._world.name}] >>> "
        return "geosim >>> "

    @property
    def _completer(self) -> WordCompleter:
        cmds = _WORLD_COMMANDS if self._world else _GLOBAL_COMMANDS
        return WordCompleter(cmds, ignore_case=True)

    def run(self) -> None:
        print("geosim  —  type 'help' for available commands\n")
        while True:
            try:
                text = self._session.prompt(
                    self._prompt,
                    completer=self._completer,
                    style=_STYLE,
                ).strip()
            except (EOFError, KeyboardInterrupt):
                print("\nExiting.")
                break

            if not text:
                continue

            parts = text.split()
            cmd, args = parts[0].lower(), parts[1:]

            if cmd in ("exit", "quit"):
                print("Exiting.")
                break
            elif cmd == "help":
                print(_WORLD_HELP if self._world else _GLOBAL_HELP)
            elif cmd == "list":
                self._cmd_list()
            elif cmd == "new":
                self._cmd_new(args)
            elif cmd == "open":
                self._cmd_open(args)
            elif cmd == "close":
                self._cmd_close()
            elif cmd == "status":
                self._cmd_status()
            elif cmd == "planetology":
                self._cmd_object("planetology", Planetology, args, _PLANETOLOGY_HELP)
            elif cmd == "geology":
                self._cmd_object("geology", Geology, args, _GEOLOGY_HELP)
            elif cmd == "topography":
                self._cmd_topography(args)
            elif cmd == "climate":
                self._cmd_object("climate", Climate, args, _CLIMATE_HELP)
            elif cmd == "branch":
                self._cmd_branch(args)
            else:
                print(f"Unknown command: '{cmd}'. Type 'help' for available commands.")

    # --- global commands ---

    def _cmd_list(self) -> None:
        worlds = store.list_worlds()
        if worlds:
            print("\n".join(f"  {w}" for w in worlds))
        else:
            print("No saved worlds found.")

    def _cmd_new(self, args: list[str]) -> None:
        if not args:
            print("Usage: new <name>")
            return
        name = args[0]
        if store.world_exists(name):
            print(f"A world named '{name}' already exists. Use 'open {name}' to open it.")
            return
        config = WorldConfig()  # TODO: prompt for config options
        world = World(name=name, config=config)
        store.save_world(world)
        self._world = world
        print(f"Created and opened world '{name}'.")

    def _cmd_open(self, args: list[str]) -> None:
        if not args:
            print("Usage: open <name>")
            return
        name = args[0]
        if not store.world_exists(name):
            print(f"No world named '{name}' found. Use 'new {name}' to create it.")
            return
        self._world = store.load_world(name)
        print(f"Opened world '{name}'.")

    # --- world commands ---

    def _cmd_close(self) -> None:
        if not self._world:
            print("No world is currently open.")
            return
        print(f"Closed world '{self._world.name}'.")
        self._world = None

    def _cmd_status(self) -> None:
        if not self._world:
            print("No world is currently open.")
            return
        print(self._world.status())

    def _cmd_subobject(self, name: str) -> None:
        """Show status for a top-level object (used by _cmd_object and _cmd_topography)."""
        if not self._world:
            print("No world is currently open.")
            return
        obj = getattr(self._world, name)
        if obj is None:
            print(f"This world has no {name} yet. Use '{name} new' to create one.")
        else:
            print(obj.status())

    def _cmd_object(self, attr: str, cls, args: list[str], help_text: str) -> None:
        """Generic dispatcher for top-level objects: handles 'new', 'help', and status.

        Objects without field sub-commands yet (Planetology, Geology, Climate)
        use this dispatcher.  When they gain sub-commands they will get their
        own method like _cmd_topography.
        """
        if not self._world:
            print("No world is currently open.")
            return

        if not args or args[0] == "status":
            self._cmd_subobject(attr)
            return

        if args[0] == "help":
            print(help_text)
            return

        if args[0] == "new":
            if getattr(self._world, attr) is not None:
                print(f"This world already has a {attr}.")
                return
            setattr(self._world, attr, cls())
            store.save_world(self._world)
            print(f"Created new {attr}.")
            return

        # Any other sub-command requires the object to exist
        if getattr(self._world, attr) is None:
            print(f"No {attr} yet. Run '{attr} new' first.")
            return

        print(f"Unknown {attr} sub-command: '{args[0]}'. Type '{attr} help' for usage.")

    def _cmd_topography(self, args: list[str]) -> None:
        if not self._world:
            print("No world is currently open.")
            return

        if not args or args[0] == "status":
            self._cmd_subobject("topography")
            return

        if args[0] == "help":
            print(_TOPOGRAPHY_HELP)
            return

        if args[0] == "new":
            if self._world.topography is not None:
                print("This world already has a topography.")
                return
            self._world.topography = Topography()
            store.save_world(self._world)
            print("Created new topography.")
            return

        # All field sub-commands require topography to exist
        if self._world.topography is None:
            print("No topography yet. Run 'topography new' first.")
            return

        # Field-first dispatch: topography <field> <action> [options]
        if args[0] == "elevation":
            field_args = args[1:]
            if not field_args or field_args[0] == "status":
                print(self._world.topography.status())
            elif field_args[0] in ("help", "--help"):
                print(_TOPOGRAPHY_ELEVATION_HELP)
            elif field_args[0] == "load":
                self._cmd_topography_elevation_load(field_args[1:])
            elif field_args[0] == "display":
                self._cmd_topography_elevation_display(field_args[1:])
            elif field_args[0] == "export":
                self._cmd_topography_elevation_export(field_args[1:])
            else:
                print(f"Unknown topography elevation sub-command: '{field_args[0]}'. Type 'topography elevation --help' for usage.")
            return

        print(f"Unknown topography sub-command: '{args[0]}'. Type 'topography help' for usage.")

    def _cmd_topography_elevation_load(self, args: list[str]) -> None:
        """Handle: topography elevation load <file> [--min-elev X] [--max-elev Y] [--max-pixels N]"""
        if not args or "--help" in args:
            print(_TOPOGRAPHY_ELEVATION_LOAD_HELP)
            return

        path = args[0]
        remaining = args[1:]

        min_elev = -8000.0
        max_elev = 8000.0
        max_pixels: int | None = 100_000_000
        i = 0
        while i < len(remaining):
            flag = remaining[i]
            if flag == "--min-elev" and i + 1 < len(remaining):
                try:
                    min_elev = float(remaining[i + 1])
                except ValueError:
                    print(f"Invalid --min-elev value: {remaining[i + 1]!r}")
                    return
                i += 2
            elif flag == "--max-elev" and i + 1 < len(remaining):
                try:
                    max_elev = float(remaining[i + 1])
                except ValueError:
                    print(f"Invalid --max-elev value: {remaining[i + 1]!r}")
                    return
                i += 2
            elif flag == "--max-pixels" and i + 1 < len(remaining):
                try:
                    v = int(remaining[i + 1])
                    max_pixels = None if v == 0 else v
                except ValueError:
                    print(f"Invalid --max-pixels value: {remaining[i + 1]!r}")
                    return
                i += 2
            else:
                print(f"Unknown option: {flag!r}")
                return

        if min_elev >= max_elev:
            print("--min-elev must be less than --max-elev.")
            return

        from geosim.topography.loader import load_elevation_png

        print(f"Loading elevation from '{path}' (min={min_elev} m, max={max_elev} m)…")
        try:
            elevation = load_elevation_png(
                path,
                grid_type=self._world.config.grid_type,
                resolution=self._world.config.base_resolution,
                min_elev=min_elev,
                max_elev=max_elev,
                max_pixels=max_pixels,
            )
        except FileNotFoundError:
            print(f"File not found: {path!r}")
            return
        except Exception as exc:
            print(f"Failed to load elevation: {exc}")
            return

        tier = self._world.topography.get_tier(self._world.config.base_resolution)
        t = self._world.current_time
        tier.elevation.append(t, elevation)

        store.save_world(self._world)
        print(
            f"Loaded elevation map: {elevation.shape[0]:,} pixels, "
            f"range {elevation.min():.0f} – {elevation.max():.0f} m. World saved."
        )

    def _cmd_topography_elevation_display(self, args: list[str]) -> None:
        """Handle: topography elevation display [--time T] [--colormap cmap]"""
        if "--help" in args:
            print(_TOPOGRAPHY_ELEVATION_DISPLAY_HELP)
            return
        tier = self._world.topography.tiers.get(self._world.config.base_resolution)
        if tier is None or len(tier.elevation) == 0:
            print("No elevation data at base resolution. Use 'topography elevation load' first.")
            return

        t = tier.elevation.latest_time
        colormap: str | None = None
        i = 0
        while i < len(args):
            flag = args[i]
            if flag == "--time" and i + 1 < len(args):
                try:
                    t = float(args[i + 1])
                except ValueError:
                    print(f"Invalid --time value: {args[i + 1]!r}")
                    return
                i += 2
            elif flag == "--colormap" and i + 1 < len(args):
                colormap = args[i + 1]
                i += 2
            else:
                print(f"Unknown option: {flag!r}")
                return

        try:
            elevation = tier.elevation.get(t)
        except ValueError as exc:
            print(f"No elevation data at t={t}: {exc}")
            return

        from geosim.viz.display import display_surface_map

        # Default: sea-level colormap with a hard break at 0 m.
        # Override with --colormap to use a plain named colormap instead.
        display_surface_map(
            elevation,
            grid_type=self._world.config.grid_type,
            resolution=self._world.config.base_resolution,
            title=f"{self._world.name} — elevation (t={t:.4g} yr)",
            colormap=colormap or "terrain",
            units="m",
            sea_level=None if colormap else 0.0,
        )

    def _cmd_topography_elevation_export(self, args: list[str]) -> None:
        """Handle: topography elevation export [<file>] [--time T] [--min-elev M] [--max-elev M]"""
        if "--help" in args:
            print(_TOPOGRAPHY_ELEVATION_EXPORT_HELP)
            return
        out_path_arg: str | None = None
        t: float | None = None
        min_elev: float | None = None
        max_elev: float | None = None

        i = 0
        while i < len(args):
            flag = args[i]
            if flag == "--time" and i + 1 < len(args):
                try:
                    t = float(args[i + 1])
                except ValueError:
                    print(f"Invalid --time value: {args[i + 1]!r}")
                    return
                i += 2
            elif flag == "--min-elev" and i + 1 < len(args):
                try:
                    min_elev = float(args[i + 1])
                except ValueError:
                    print(f"Invalid --min-elev value: {args[i + 1]!r}")
                    return
                i += 2
            elif flag == "--max-elev" and i + 1 < len(args):
                try:
                    max_elev = float(args[i + 1])
                except ValueError:
                    print(f"Invalid --max-elev value: {args[i + 1]!r}")
                    return
                i += 2
            elif not flag.startswith("--") and out_path_arg is None:
                out_path_arg = flag
                i += 1
            else:
                print(f"Unknown option: {flag!r}")
                return

        from geosim.io.store import exports_dir
        from geosim.core.grid import natural_equirectangular_size, null_surface_map_png

        grid_type = self._world.config.grid_type
        resolution = self._world.config.base_resolution

        tier = self._world.topography.tiers.get(resolution)
        has_data = tier is not None and len(tier.elevation) > 0

        export_root = exports_dir(self._world.name)

        if not has_data:
            # Save a blank mid-grey template at the natural size for this grid
            fname = out_path_arg or f"{self._world.name}_elevation_blank.png"
            out = export_root / fname if out_path_arg is None else fname
            null_surface_map_png(out, grid_type, resolution)
            nat_h, nat_w = natural_equirectangular_size(grid_type, resolution)
            print(
                f"No elevation data — saved blank template ({nat_w}×{nat_h}) to:\n  {out}\n"
                f"Paint on it and reload with:\n"
                f"  topography elevation load <file> --min-elev -8000 --max-elev 8000"
            )
            return

        # Export actual elevation data
        snap_t = tier.elevation.latest_time if t is None else t
        try:
            elevation = tier.elevation.get(snap_t)
        except ValueError as exc:
            print(f"No elevation data at t={snap_t}: {exc}")
            return

        from geosim.topography.exporter import export_elevation_png

        t_tag = f"_t{snap_t:.4g}".replace(".", "p") if snap_t != 0.0 else ""
        fname = out_path_arg or f"{self._world.name}_elevation{t_tag}.png"
        out = export_root / fname if out_path_arg is None else fname

        used_min, used_max = export_elevation_png(
            elevation, out, grid_type, resolution, min_elev, max_elev
        )
        print(
            f"Exported elevation map to:\n  {out}\n"
            f"Colour scale: black = {used_min:.0f} m, white = {used_max:.0f} m\n"
            f"To reload: topography elevation load <file> --min-elev {used_min:.0f} --max-elev {used_max:.0f}"
        )

    def _cmd_branch(self, args: list[str]) -> None:
        if not self._world:
            print("No world is currently open.")
            return
        # TODO: implement branching
        print("branch: not yet implemented.")


def main() -> None:
    GeoSimREPL().run()


if __name__ == "__main__":
    main()
