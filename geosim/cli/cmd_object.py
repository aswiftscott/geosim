"""Generic CLI handlers for simple world objects.

Handles the ``planetology``, ``geology``, and ``atmosphere`` commands, which
all share the same sub-command structure: bare status, ``new``, ``help``, and
(for objects with a ``FIELDS`` registry) ``set``.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from .help import object_help

if TYPE_CHECKING:
    from geosim.core.world import World


def cmd_object(world: "World", attr: str, cls: type, args: list[str]) -> None:
    """Dispatch a world-object sub-command.

    Args:
        world: The open world.
        attr:  Attribute name on the world (e.g. ``"planetology"``).
        cls:   Domain class to instantiate on ``new`` (e.g. ``Planetology``).
        args:  Remaining CLI tokens after the object name.
    """
    if not args or args[0] == "status":
        obj = getattr(world, attr)
        if obj is None:
            print(f"This world has no {attr} yet. Use '{attr} new' to create one.")
        else:
            print(obj.status())
        return

    if args[0] == "help":
        print(object_help(attr, cls))
        return

    if args[0] == "new":
        if getattr(world, attr) is not None:
            print(f"This world already has a {attr}.")
            return
        setattr(world, attr, cls())
        print(f"Created new {attr}.")
        return

    if getattr(world, attr) is None:
        print(f"No {attr} yet. Run '{attr} new' first.")
        return

    if args[0] == "set":
        _cmd_object_set(world, attr, cls, args[1:])
        return

    print(f"Unknown {attr} sub-command: '{args[0]}'. Type '{attr} help' for usage.")


def _cmd_object_set(world: "World", attr: str, cls: type, args: list[str]) -> None:
    """Handle: <object> set <field> <value>"""
    if not hasattr(cls, "FIELDS"):
        print(f"'{attr}' has no settable scalar fields.")
        return

    field_info = {name: (unit, desc) for name, unit, desc in cls.FIELDS}

    if len(args) < 2:
        field_list = "\n".join(
            f"  {name:<22}{desc}" for name, _, desc in cls.FIELDS
        )
        print(f"Usage: {attr} set <field> <value>\n\nFields:\n{field_list}")
        return

    field, value_str = args[0], args[1]

    if field not in field_info:
        names = ", ".join(name for name, _, _ in cls.FIELDS)
        print(f"Unknown field '{field}'. Settable fields: {names}")
        return

    try:
        value = float(value_str)
    except ValueError:
        print(f"Invalid value {value_str!r} — must be a number.")
        return

    obj = getattr(world, attr)
    h = getattr(obj, field)
    t = world.current_time
    try:
        h.append(t, value)
    except ValueError as exc:
        print(f"Cannot set {attr}.{field}: {exc}")
        return

    unit, _ = field_info[field]
    suffix = f" {unit}" if unit else ""
    print(f"Set {attr}.{field} = {value}{suffix} at t={t:.4g} yr.")
