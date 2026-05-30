"""Sparse, append-only time-indexed field storage."""
from __future__ import annotations

import bisect
from typing import Any


class History:
    """Stores a sparse time series of values.

    Only records a new entry when a value is explicitly appended.
    Append-only: once a value is recorded at time t, no entry at or before t
    can ever be modified or removed.

    To retrieve a value at any time t, returns the most recent entry at or
    before t (step-function semantics).
    """

    def __init__(self) -> None:
        self._times: list[float] = []
        self._values: list[Any] = []

    def append(self, t: float, value: Any) -> None:
        """Record a new value at time t.

        t must be strictly greater than all previously recorded times.
        """
        if self._times and t <= self._times[-1]:
            raise ValueError(
                f"Cannot append at t={t}: history already extends to t={self._times[-1]}. "
                "Histories are append-only."
            )
        self._times.append(t)
        self._values.append(value)

    def set(self, t: float, value: Any) -> None:
        """Record or overwrite a value at time t.

        Like :meth:`append`, but if t equals the most recent timestamp the
        existing entry is replaced rather than raising an error.  t must still
        be greater than or equal to the latest recorded time — earlier times
        cannot be altered.
        """
        if self._times and t < self._times[-1]:
            raise ValueError(
                f"Cannot set at t={t}: history already extends to t={self._times[-1]}. "
                "Past entries are immutable."
            )
        if self._times and t == self._times[-1]:
            self._values[-1] = value
        else:
            self._times.append(t)
            self._values.append(value)

    def get(self, t: float) -> Any:
        """Return the most recent value recorded at or before time t."""
        if not self._times:
            raise ValueError("History is empty.")
        idx = bisect.bisect_right(self._times, t) - 1
        if idx < 0:
            raise ValueError(f"No history before t={t} (earliest entry is t={self._times[0]}).")
        return self._values[idx]

    @property
    def latest_time(self) -> float | None:
        return self._times[-1] if self._times else None

    @property
    def earliest_time(self) -> float | None:
        return self._times[0] if self._times else None

    @property
    def times(self) -> list[float]:
        return list(self._times)

    def __len__(self) -> int:
        return len(self._times)

    def summary(self) -> str:
        """Return a compact human-readable description of this history's contents.

        For scalar fields, shows the latest value.
        For array fields (anything with a .shape attribute), shows shape and snapshot count.
        """
        if not self._times:
            return "not set"
        n = len(self._times)
        t_str = (
            f"t={self._times[0]:.4g}"
            if n == 1
            else f"t=[{self._times[0]:.4g} … {self._times[-1]:.4g}]"
        )
        latest = self._values[-1]
        if hasattr(latest, "shape"):
            label = "snapshot" if n == 1 else "snapshots"
            return f"{n} {label}, {t_str}, shape={latest.shape}"
        else:
            entry_label = "entry" if n == 1 else "entries"
            return f"{latest}  ({n} {entry_label}, {t_str})"

    def __repr__(self) -> str:
        return f"History({len(self)} entries, t=[{self.earliest_time}, {self.latest_time}])"
