"""Help strings for the geosim CLI.

Static help is defined as module-level constants.  Help text for settable
world objects (planetology, atmosphere) is generated dynamically from each
class's ``FIELDS`` registry via :func:`object_help`.
"""
from __future__ import annotations

GLOBAL_HELP = """\
Commands:
  new <name>          create a new world
  open <name>         open an existing world
  list                list all saved worlds
  help                show this message
  exit / quit         exit geosim"""

WORLD_HELP = """\
Commands (world open):
  status                       show world summary
  save                         save the current world to disk
  planetology [help]           planetology commands
  geology [help]               geology commands
  topography [help]            topography commands
  atmosphere [help]            atmosphere commands
  climate [help]               climate commands
  branch <t> <name>            create a new world branching from time t
  close                        close current world without exiting
  help                         show this message
  exit / quit                  exit geosim"""

TOPOGRAPHY_HELP = """\
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

TOPOGRAPHY_ELEVATION_HELP = """\
topography elevation <action> [options]

Actions:
  load <file>    load elevation from a greyscale PNG (equirectangular projection)
  display        display the elevation map in a window
  export [file]  save the elevation map as a greyscale PNG

Run 'topography elevation <action> --help' for full details on each action."""

TOPOGRAPHY_ELEVATION_LOAD_HELP = """\
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

TOPOGRAPHY_ELEVATION_DISPLAY_HELP = """\
topography elevation display [--time <t>] [--colormap <name>]

  Display the elevation map in an interactive matplotlib window.
  Requires elevation data to have been loaded first.

Options:
  --time <t>        snapshot time to display (default: latest)
  --colormap <name> matplotlib colormap name  (default: terrain)

Example:
  topography elevation display --colormap viridis"""

TOPOGRAPHY_ELEVATION_EXPORT_HELP = """\
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

CLIMATE_HELP = """\
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
  hersfeldt     classify hersfeldt climate zones        [stub]"""

CLIMATE_SIMULATE_HELP = """\
climate simulate [--iterations <n>]

  Run all simulation steps in order, committing results to the climate
  history at the current world time.  When --iterations > 1, the full
  sequence is repeated in memory and only the final pass is saved.

Options:
  --iterations <n>   number of full passes to run  (default: 1)

Examples:
  climate simulate
  climate simulate --iterations 5"""

CLIMATE_ITCZ_HELP = """\
climate itcz compute

  Compute the ITCZ (Intertropical Convergence Zone) probability map and
  save it to the climate history.

  If a surface_temperature map already exists (from a previous run), the
  ITCZ is derived from the thermal equator (latitude of max temperature
  per longitude column).  Otherwise it is estimated from the land/ocean
  distribution in the topography.

  Output: climate.itcz — shape (n_seasons, n_pixels), values 0–1."""


def object_help(cmd_name: str, cls: type) -> str:
    """Generate help text for a world-object command.

    If *cls* has a ``FIELDS`` class attribute (a list of
    ``(attr_name, unit, description)`` tuples), the ``set`` command and a
    "Settable fields:" section are included automatically.
    """
    has_fields = hasattr(cls, "FIELDS")
    pad = 36
    lines = [f"{cmd_name.capitalize()} commands:"]
    lines.append(f"  {cmd_name:<{pad}} show {cmd_name} details")
    lines.append(f"  {(cmd_name + ' new'):<{pad}} create a new empty {cmd_name}")
    if has_fields:
        lines.append(
            f"  {(cmd_name + ' set <field> <value>'):<{pad}} "
            f"set a scalar field at the current world time"
        )
    lines.append(f"  {(cmd_name + ' help'):<{pad}} show this message")

    if has_fields:
        lines.append("")
        lines.append("Settable fields:")
        for name, unit, description in cls.FIELDS:
            unit_str = f"({unit})" if unit else ""
            lines.append(f"  {name:<22}{description:<34}{unit_str}")

    return "\n".join(lines)
