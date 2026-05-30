"""Interactive CLI for geosim."""
from __future__ import annotations

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.styles import Style

from geosim.atmosphere.atmosphere import Atmosphere
from geosim.climate.climate import Climate
from geosim.core.world import World, WorldConfig
from geosim.geology.geology import Geology
from geosim.io import store
from geosim.planetology.planetology import Planetology
from geosim.topography.topography import Topography

_STYLE = Style.from_dict({"prompt": "ansigreen bold"})

_GLOBAL_COMMANDS = ["new", "open", "list", "help", "exit", "quit"]
_WORLD_COMMANDS = ["status", "planetology", "geology", "topography", "atmosphere", "climate", "close", "branch", "help", "exit", "quit"]

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
  atmosphere [help]            atmosphere commands
  climate [help]               climate commands
  branch <t> <name>            create a new world branching from time t
  close                        close current world without exiting
  help                         show this message
  exit / quit                  exit geosim"""

_ATMOSPHERE_HELP = """\
Atmosphere commands:
  atmosphere                        show atmosphere details
  atmosphere new                    create a new empty atmosphere
  atmosphere set <field> <value>    set a scalar field at the current world time
  atmosphere help                   show this message

Settable fields:
  n2          nitrogen          (mol frac)
  o2          oxygen            (mol frac)
  ar          argon             (mol frac)
  co2         carbon dioxide    (mol frac)
  ch4         methane           (mol frac)
  n2o         nitrous oxide     (mol frac)
  so2         sulfur dioxide    (mol frac)
  total_mass  total atm. mass   (kg)"""

_PLANETOLOGY_HELP = """\
Planetology commands:
  planetology                       show planetology details
  planetology new                   create a new empty planetology
  planetology set <field> <value>   set a scalar field at the current world time
  planetology help                  show this message

Settable fields:
  radius              planetary radius        (m)
  mass                planetary mass          (kg)
  day_length          length of one day       (hr)
  year_length         length of one year      (days)
  eccentricity        orbital eccentricity    (dimensionless)
  insolation          solar constant          (W/m²)
  axial_tilt          axial tilt              (°)
  days_to_perihelion  days from NH winter solstice to perihelion  (days)"""

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
  climate                        show climate details
  climate new [--seasons <n>]    create a new empty climate (default: 4 seasons)
  climate simulate               run all simulation steps in order
    [--iterations <n>]           (default: 1)
  climate <step> compute         run a single simulation step
  climate <step> compute --help  detailed help for that step
  climate help                   show this message

Simulation steps (run in this order by 'climate simulate'):
  itcz          compute ITCZ probability map
  currents      compute ocean currents and temperature  [stub]
  pressure      compute surface pressure and winds      [stub]
  precipitation compute precipitation                   [stub]
  albedo        compute surface albedo                  [stub]
  clouds        compute cloud cover fraction            [stub]
  sunlight      compute surface solar irradiance        [stub]
  temperature   compute surface temperature             [stub]
  evaporation   compute PET and AET                     [stub]
  koppen        classify Koppen climate zones           [stub]
  herzfeld      classify Herzfeld climate zones         [stub]"""

_CLIMATE_SIMULATE_HELP = """\
climate simulate [--iterations <n>]

  Run all simulation steps in order, committing results to the climate
  history at the current world time.  When --iterations > 1, the full
  sequence is repeated in memory and only the final pass is saved.

Options:
  --iterations <n>   number of full passes to run  (default: 1)

Examples:
  climate simulate
  climate simulate --iterations 5"""

_CLIMATE_ITCZ_HELP = """\
climate itcz compute

  Compute the ITCZ (Intertropical Convergence Zone) probability map and
  save it to the climate history.

  If a surface_temperature map already exists (from a previous run), the
  ITCZ is derived from the thermal equator (latitude of max temperature
  per longitude column).  Otherwise it is estimated from the land/ocean
  distribution in the topography.

  Output: climate.itcz — shape (n_seasons, n_pixels), values 0–1."""

# Mapping from CLI sub-command token to internal step name
_CLI_TO_STEP: dict[str, str] = {
    "itcz":          "itcz",
    "currents":      "currents",
    "pressure":      "pressure",
    "precipitation": "precipitation",
    "albedo":        "albedo",
    "clouds":        "clouds",
    "sunlight":      "sunlight",
    "temperature":   "temperature",
    "evaporation":   "evaporation",
    "koppen":        "koppen",
    "herzfeld":      "herzfeld",
}

# Settable scalar fields per object.  Only objects whose History fields hold
# plain numbers (not per-pixel arrays or per-season tensors) appear here.
_SETTABLE_FIELDS: dict[str, list[tuple[str, str]]] = {
    "planetology": [
        ("radius",             "m"),
        ("mass",               "kg"),
        ("day_length",         "hr"),
        ("year_length",        "days"),
        ("eccentricity",       ""),
        ("insolation",         "W/m²"),
        ("axial_tilt",         "°"),
        ("days_to_perihelion", "days"),
    ],
    "atmosphere": [
        ("n2",         "mol frac"),
        ("o2",         "mol frac"),
        ("ar",         "mol frac"),
        ("co2",        "mol frac"),
        ("ch4",        "mol frac"),
        ("n2o",        "mol frac"),
        ("so2",        "mol frac"),
        ("total_mass", "kg"),
    ],
}

# Per-step help strings (None = use the generic stub message)
_STEP_HELP: dict[str, str] = {
    "itcz": _CLIMATE_ITCZ_HELP,
}

_TOPOGRAPHY_ELEVATION_HELP = """\
topography elevation <action> [options]

Actions:
  load <file>    load elevation from a greyscale PNG (equirectangular projection)
  display        display the elevation map in a window
  export [file]  save the elevation map as a greyscale PNG

Run 'topography elevation <action> --help' for full details on each action."""

_TOPOGRAPHY_ELEVATION_LOAD_HELP = """\
topography elevation load <file> [--min-elev <m>] [--max-elev <m>]

  Load an elevation map from a greyscale PNG file.
  The PNG must use an equirectangular (plate carrée) projection.
  Pixel brightness is linearly mapped to elevation:
    black (0)   → --min-elev
    white (255) → --max-elev

Arguments:
  <file>          path to the input PNG (any resolution, any aspect ratio)

Options:
  --min-elev <m>  elevation value mapped to black  (default: -8000)
  --max-elev <m>  elevation value mapped to white  (default:  8000)

Example:
  topography elevation load earth.png --min-elev -11000 --max-elev 8850"""

_TOPOGRAPHY_ELEVATION_DISPLAY_HELP = """\
topography elevation display [--time <t>] [--colormap <name>]

  Display the elevation map in an interactive matplotlib window.
  Requires elevation data to have been loaded first.

Options:
  --time <t>        snapshot time to display (default: latest)
  --colormap <name> matplotlib colormap name  (default: terrain)

Example:
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
            elif cmd == "atmosphere":
                self._cmd_object("atmosphere", Atmosphere, args, _ATMOSPHERE_HELP)
            elif cmd == "climate":
                self._cmd_climate(args)
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
        """Generic dispatcher for top-level objects: handles 'new', 'help', 'set', and status."""
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

        if args[0] == "set":
            self._cmd_object_set(attr, args[1:])
            return

        print(f"Unknown {attr} sub-command: '{args[0]}'. Type '{attr} help' for usage.")

    def _cmd_object_set(self, attr: str, args: list[str]) -> None:
        """Handle: <object> set <field> <value>"""
        settable = _SETTABLE_FIELDS.get(attr, [])
        if not settable:
            print(f"'{attr}' has no settable scalar fields.")
            return

        field_units = {name: unit for name, unit in settable}

        if len(args) < 2:
            field_list = "\n".join(
                f"  {name:<22}{unit}" for name, unit in settable
            )
            print(f"Usage: {attr} set <field> <value>\n\nFields:\n{field_list}")
            return

        field, value_str = args[0], args[1]

        if field not in field_units:
            names = ", ".join(n for n, _ in settable)
            print(f"Unknown field '{field}'. Settable fields: {names}")
            return

        try:
            value = float(value_str)
        except ValueError:
            print(f"Invalid value {value_str!r} — must be a number.")
            return

        obj = getattr(self._world, attr)
        h = getattr(obj, field)
        t = self._world.current_time
        try:
            h.append(t, value)
        except ValueError as exc:
            print(f"Cannot set {attr}.{field}: {exc}")
            return

        store.save_world(self._world)
        unit = field_units[field]
        suffix = f" {unit}" if unit else ""
        print(f"Set {attr}.{field} = {value}{suffix} at t={t:.4g} yr.")

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
        """Handle: topography elevation load <file> [--min-elev X] [--max-elev Y]"""
        if not args or "--help" in args:
            print(_TOPOGRAPHY_ELEVATION_LOAD_HELP)
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

    # --- climate commands ---

    def _cmd_climate(self, args: list[str]) -> None:
        if not self._world:
            print("No world is currently open.")
            return

        if not args or args[0] == "status":
            self._cmd_subobject("climate")
            return

        if args[0] in ("help", "--help"):
            print(_CLIMATE_HELP)
            return

        if args[0] == "new":
            if self._world.climate is not None:
                print("This world already has a climate.")
                return
            n_seasons = 4
            new_args = args[1:]
            i = 0
            ok = True
            while i < len(new_args):
                flag = new_args[i]
                if flag == "--seasons" and i + 1 < len(new_args):
                    try:
                        n_seasons = int(new_args[i + 1])
                    except ValueError:
                        print(f"Invalid --seasons value: {new_args[i + 1]!r} (must be a positive even integer)")
                        ok = False
                        break
                    if n_seasons < 1 or n_seasons % 2 != 0:
                        print("--seasons must be a positive even integer (e.g. 2, 4, 6, 8).")
                        ok = False
                        break
                    i += 2
                else:
                    print(f"Unknown option: {flag!r}. Usage: climate new [--seasons <n>]")
                    ok = False
                    break
            if not ok:
                return

            # Validate that the planetology is compatible with the rapid-rotator
            # climate model before creating the climate object.
            pl = self._world.planetology
            if pl is None or len(pl.day_length) == 0 or len(pl.year_length) == 0:
                print(
                    "Cannot create a climate: planetology must exist and have "
                    "day_length and year_length set first."
                )
                return

            day_hr  = pl.day_length.get(pl.day_length.latest_time)    # hours
            year_dy = pl.year_length.get(pl.year_length.latest_time)  # days
            day_dy  = day_hr / 24.0

            errors = []
            if day_dy >= 30:
                errors.append(
                    f"  Day length {day_dy:.2f} Earth days is ≥ 30 days "
                    "(rapid-rotator model requires < 30 days)."
                )
            if year_dy >= 36500:
                errors.append(
                    f"  Year length {year_dy:.2f} Earth days is ≥ 100 Earth years "
                    "(climate model requires < 100 Earth years)."
                )
            if year_dy < 10 * day_dy:
                errors.append(
                    f"  Year ({year_dy:.2f} days) is less than 10× the day "
                    f"({day_dy:.4g} days); climate model requires year ≥ 10 × day."
                )
            if errors:
                print("Cannot create a climate — planetology is outside supported range:")
                print("\n".join(errors))
                return

            self._world.climate = Climate(n_seasons=n_seasons)
            store.save_world(self._world)
            print(f"Created new climate (n_seasons={n_seasons}).")
            return

        # All sub-commands below require a Climate object
        if self._world.climate is None:
            print("No climate yet. Run 'climate new' first.")
            return

        if args[0] == "simulate":
            self._cmd_climate_simulate(args[1:])
            return

        # climate <step> <action> [options]
        if args[0] in _CLI_TO_STEP:
            step_args = args[1:]
            if not step_args or step_args[0] in ("help", "--help"):
                self._cmd_climate_step_help(args[0])
            elif step_args[0] == "compute":
                self._cmd_climate_step_compute(args[0], step_args[1:])
            else:
                print(f"Unknown action '{step_args[0]}' for 'climate {args[0]}'. "
                      f"Try 'climate {args[0]} compute' or 'climate {args[0]} --help'.")
            return

        print(f"Unknown climate sub-command: '{args[0]}'. Type 'climate help' for usage.")

    def _cmd_climate_step_help(self, cli_name: str) -> None:
        """Print help for a single simulation step."""
        from geosim.climate.simulator import _STEP_OUTPUTS
        help_text = _STEP_HELP.get(cli_name)
        if help_text:
            print(help_text)
        else:
            step = _CLI_TO_STEP[cli_name]
            outputs = ", ".join(_STEP_OUTPUTS.get(step, [step]))
            print(f"climate {cli_name} compute\n\n"
                  f"  Run the '{cli_name}' simulation step.\n"
                  f"  Output field(s): {outputs}\n\n"
                  f"  [Not yet implemented — runs as a no-op.]")

    def _cmd_climate_step_compute(self, cli_name: str, args: list[str]) -> None:
        """Handle: climate <step> compute [--help]"""
        if "--help" in args:
            self._cmd_climate_step_help(cli_name)
            return

        from geosim.climate.simulator import run_step, _STEP_OUTPUTS
        step = _CLI_TO_STEP[cli_name]
        outputs = _STEP_OUTPUTS.get(step, [step])

        print(f"Computing {cli_name}...")
        run_step(self._world, step)
        store.save_world(self._world)

        t = self._world.current_time
        print(f"Saved to climate history at t={t:.4g} yr:")
        for field in outputs:
            arr = getattr(self._world.climate, field).get(t)
            print(f"  {field}: shape={arr.shape}")

    def _cmd_climate_simulate(self, args: list[str]) -> None:
        """Handle: climate simulate [--iterations <n>]"""
        if "--help" in args:
            print(_CLIMATE_SIMULATE_HELP)
            return

        iterations = 1
        i = 0
        while i < len(args):
            flag = args[i]
            if flag == "--iterations" and i + 1 < len(args):
                try:
                    iterations = int(args[i + 1])
                except ValueError:
                    print(f"Invalid --iterations value: {args[i + 1]!r} (must be a positive integer)")
                    return
                if iterations < 1:
                    print("--iterations must be at least 1.")
                    return
                i += 2
            else:
                print(f"Unknown option: {flag!r}. Run 'climate simulate --help' for usage.")
                return

        from geosim.climate.simulator import simulate_climate, _CLIMATE_FIELDS

        world = self._world
        iter_word = "iteration" if iterations == 1 else "iterations"
        print(f"Running climate simulation ({iterations} {iter_word})...")

        simulate_climate(world, n_iterations=iterations)

        store.save_world(world)
        t = world.current_time
        print(f"Climate simulation complete. Results stored at t={t:.4g} yr.")



def main() -> None:
    GeoSimREPL().run()


if __name__ == "__main__":
    main()
