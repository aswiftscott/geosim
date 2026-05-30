"""Shared CLI argument-parsing helpers."""
from __future__ import annotations

from typing import Any


def parse_flags(
    args: list[str],
    spec: dict[str, type | None],
) -> tuple[dict[str, Any], list[str]] | None:
    """Parse ``--flag value`` pairs from *args* according to *spec*.

    *spec* maps each flag name (including the leading ``--``) to a callable
    that converts the raw string value, or ``None`` for boolean flags (no
    following value).  Tokens that do not start with ``--`` are collected as
    positional arguments in the order they appear, regardless of their
    position relative to flags.

    Returns ``(flags, positionals)`` on success.  On error, prints a message
    and returns ``None``.

    Example::

        result = parse_flags(
            ["earth.png", "--min-elev", "-8000", "--max-elev", "8000"],
            {"--min-elev": float, "--max-elev": float},
        )
        # result == ({"--min-elev": -8000.0, "--max-elev": 8000.0}, ["earth.png"])
    """
    flags: dict[str, Any] = {}
    positionals: list[str] = []
    i = 0
    while i < len(args):
        token = args[i]
        if token in spec:
            converter = spec[token]
            if converter is None:
                flags[token] = True
                i += 1
            else:
                if i + 1 >= len(args):
                    print(f"Option {token!r} requires a value.")
                    return None
                raw = args[i + 1]
                try:
                    flags[token] = converter(raw)
                except (ValueError, TypeError):
                    print(f"Invalid value for {token}: {raw!r}")
                    return None
                i += 2
        elif token.startswith("--"):
            print(f"Unknown option: {token!r}")
            return None
        else:
            positionals.append(token)
            i += 1
    return flags, positionals
