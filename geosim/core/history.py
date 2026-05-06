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

    def __repr__(self) -> str:
        return f"History({len(self)} entries, t=[{self.earliest_time}, {self.latest_time}])"
