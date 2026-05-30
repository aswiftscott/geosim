"""CLI handlers for climate commands."""
from __future__ import annotations

from typing import TYPE_CHECKING

from .args import parse_flags
from .help import CLIMATE_HELP, CLIMATE_SIMULATE_HELP, CLIMATE_ITCZ_HELP

if TYPE_CHECKING:
    from geosim.core.world import World

# Mapping from CLI sub-command token to internal step name.
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
    "hersfeldt":     "hersfeldt",
}

# Per-step help strings; None falls back to the generic stub message.
_STEP_HELP: dict[str, str] = {
    "itcz": CLIMATE_ITCZ_HELP,
}


def cmd_climate(world: "World", args: list[str]) -> None:
    """Dispatch a climate sub-command."""
    if not args or args[0] == "status":
        if world.climate is None:
            print("This world has no climate yet. Use 'climate new' to create one.")
        else:
            print(world.climate.status())
        return

    if args[0] in ("help", "--help"):
        print(CLIMATE_HELP)
        return

    if args[0] == "new":
        _climate_new(world, args[1:])
        return

    if world.climate is None:
        print("No climate yet. Run 'climate new' first.")
        return

    if args[0] == "simulate":
        _climate_simulate(world, args[1:])
        return

    if args[0] in _CLI_TO_STEP:
        step_args = args[1:]
        if not step_args or step_args[0] in ("help", "--help"):
            _climate_step_help(args[0])
        elif step_args[0] == "compute":
            _climate_step_compute(world, args[0], step_args[1:])
        else:
            print(
                f"Unknown action '{step_args[0]}' for 'climate {args[0]}'. "
                f"Try 'climate {args[0]} compute' or 'climate {args[0]} --help'."
            )
        return

    print(f"Unknown climate sub-command: '{args[0]}'. Type 'climate help' for usage.")


def _climate_new(world: "World", args: list[str]) -> None:
    from geosim.climate.climate import Climate

    if world.climate is not None:
        print("This world already has a climate.")
        return

    result = parse_flags(args, {"--seasons": int})
    if result is None:
        return
    flags, _ = result

    n_seasons = flags.get("--seasons", 4)
    if n_seasons < 1 or n_seasons % 2 != 0:
        print("--seasons must be a positive even integer (e.g. 2, 4, 6, 8).")
        return

    pl = world.planetology
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

    world.climate = Climate(n_seasons=n_seasons)
    print(f"Created new climate (n_seasons={n_seasons}).")


def _climate_step_help(cli_name: str) -> None:
    from geosim.climate.simulator import _STEP_OUTPUTS

    help_text = _STEP_HELP.get(cli_name)
    if help_text:
        print(help_text)
        return

    step = _CLI_TO_STEP[cli_name]
    outputs = ", ".join(_STEP_OUTPUTS.get(step, [step]))
    print(
        f"climate {cli_name} compute\n\n"
        f"  Run the '{cli_name}' simulation step.\n"
        f"  Output field(s): {outputs}\n\n"
        f"  [Not yet implemented — runs as a no-op.]"
    )


def _climate_step_compute(world: "World", cli_name: str, args: list[str]) -> None:
    if "--help" in args:
        _climate_step_help(cli_name)
        return

    from geosim.climate.simulator import run_step, _STEP_OUTPUTS

    step    = _CLI_TO_STEP[cli_name]
    outputs = _STEP_OUTPUTS.get(step, [step])

    print(f"Computing {cli_name}...")
    run_step(world, step)

    t = world.current_time
    print(f"Computed {cli_name} at t={t:.4g} yr:")
    for field in outputs:
        arr = getattr(world.climate, field).get(t)
        print(f"  {field}: shape={arr.shape}")


def _climate_simulate(world: "World", args: list[str]) -> None:
    if "--help" in args:
        print(CLIMATE_SIMULATE_HELP)
        return

    result = parse_flags(args, {"--iterations": int})
    if result is None:
        return
    flags, _ = result

    iterations = flags.get("--iterations", 1)
    if iterations < 1:
        print("--iterations must be at least 1.")
        return

    from geosim.climate.simulator import simulate_climate

    iter_word = "iteration" if iterations == 1 else "iterations"
    print(f"Running climate simulation ({iterations} {iter_word})...")
    simulate_climate(world, n_iterations=iterations)

    t = world.current_time
    print(f"Climate simulation complete. Results at t={t:.4g} yr.")
