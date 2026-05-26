# geosim
A command-line tool for creating and simulating the climate and geography of a planet. Create a **World**, then build up its **Planetology**, **Geology**, **Topography**, and **Climate** — each storing a full history so you can inspect or animate any point in time.

## Installation

Requires Python 3.11+. Install in editable mode from the repo root:

> pip install -e .

## Running

The most reliable way to launch geosim (works with or without installing):

> python -m geosim

Alternatively, after `pip install -e .` you can use the `geosim` command directly — but only if Python's Scripts directory is on your `PATH`. If `geosim` isn't found, use `python -m geosim` instead.

## Usage

At the `geosim >>>` prompt:

| Command | Description |
|---|---|
| `new <name>` | Create a new world |
| `open <name>` | Open a saved world |
| `list` | List all saved worlds |
| `help` | Show available commands |
| `exit` / `quit` | Exit geosim |

Once a world is open (`geosim [name] >>>`):

| Command | Description |
|---|---|
| `status` | Show a summary of the world |
| `planetology` | Show planetology details |
| `geology` | Show geology details |
| `topography` | Show topography details |
| `topography load elevation <file> [--min-elev M] [--max-elev M]` | Load a PNG as an elevation map (equirectangular; default range −8000 to 8000 m) |
| `climate` | Show climate details |
| `branch <t> <name>` | Create a new world branching from time `t` |
| `close` | Close the current world |
| `help` | Show available commands |

## Project structure

```
geosim/
  cli/          Interactive REPL entry point
  core/         World and WorldConfig models
  planetology/  Planetary/orbital data
  geology/      Tectonic plates, rock types, etc.
  topography/   Elevation maps
  climate/      Temperature, pressure, precipitation maps
  viz/          Map and figure generation
  io/           Save/load worlds to disk
```
