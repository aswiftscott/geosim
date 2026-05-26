"""Interactive CLI for geosim."""
from __future__ import annotations

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.styles import Style

from geosim.core.world import World, WorldConfig
from geosim.io import store

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
  status                                         show world summary
  planetology                                    show planetology details
  geology                                        show geology details
  topography                                     show topography details
  topography elevation load <file>               load elevation from a PNG file
    [--min-elev <m>] [--max-elev <m>]            (defaults: -8000 / 8000 m)
  topography elevation display                   display elevation map
    [--time <t>] [--colormap <cmap>]             (default: latest snapshot, colormap 'terrain')
  climate                                        show climate details
  branch <t> <name>                              create a new world branching from time t
  close                                          close current world without exiting
  help                                           show this message
  exit / quit                                    exit geosim"""


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
                self._cmd_subobject("planetology")
            elif cmd == "geology":
                self._cmd_subobject("geology")
            elif cmd == "topography":
                self._cmd_topography(args)
            elif cmd == "climate":
                self._cmd_subobject("climate")
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
        if not self._world:
            print("No world is currently open.")
            return
        obj = getattr(self._world, name)
        if obj is None:
            print(f"This world has no {name} object yet.")
        else:
            print(obj.status())

    def _cmd_topography(self, args: list[str]) -> None:
        if not self._world:
            print("No world is currently open.")
            return

        if not args or args[0] == "status":
            self._cmd_subobject("topography")
            return

        # Field-first dispatch: topography <field> <action> [options]
        if args[0] == "elevation":
            field_args = args[1:]
            if not field_args or field_args[0] == "status":
                self._cmd_subobject("topography")
            elif field_args[0] == "load":
                self._cmd_topography_elevation_load(field_args[1:])
            elif field_args[0] == "display":
                self._cmd_topography_elevation_display(field_args[1:])
            else:
                print(f"Unknown topography elevation sub-command: '{field_args[0]}'. Type 'help' for usage.")
            return

        print(f"Unknown topography sub-command: '{args[0]}'. Type 'help' for usage.")

    def _cmd_topography_elevation_load(self, args: list[str]) -> None:
        """Handle: topography elevation load <file> [--min-elev X] [--max-elev Y]"""
        if not args:
            print("Usage: topography elevation load <file> [--min-elev <m>] [--max-elev <m>]")
            return

        path = args[0]
        remaining = args[1:]

        min_elev = -8000.0
        max_elev = 8000.0
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
            else:
                print(f"Unknown option: {flag!r}")
                return

        if min_elev >= max_elev:
            print("--min-elev must be less than --max-elev.")
            return

        from geosim.topography.loader import load_elevation_png
        from geosim.topography.topography import Topography

        print(f"Loading elevation from '{path}' (min={min_elev} m, max={max_elev} m)…")
        try:
            elevation = load_elevation_png(
                path,
                grid_type=self._world.config.grid_type,
                resolution=self._world.config.base_resolution,
                min_elev=min_elev,
                max_elev=max_elev,
            )
        except FileNotFoundError:
            print(f"File not found: {path!r}")
            return
        except Exception as exc:
            print(f"Failed to load elevation: {exc}")
            return

        if self._world.topography is None:
            self._world.topography = Topography()

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
        if self._world.topography is None:
            print("This world has no topography yet. Use 'topography elevation load' first.")
            return

        tier = self._world.topography.tiers.get(self._world.config.base_resolution)
        if tier is None or len(tier.elevation) == 0:
            print("No elevation data at base resolution. Use 'topography elevation load' first.")
            return

        t = tier.elevation.latest_time
        colormap = "terrain"
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

        display_surface_map(
            elevation,
            grid_type=self._world.config.grid_type,
            resolution=self._world.config.base_resolution,
            title=f"{self._world.name} — elevation (t={t:.4g} yr)",
            colormap=colormap,
            units="m",
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
