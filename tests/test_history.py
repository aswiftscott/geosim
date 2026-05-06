"""Tests for geosim.core.history."""
import pytest

from geosim.core.history import History


def test_append_and_get() -> None:
    h = History()
    h.append(0.0, "a")
    h.append(10.0, "b")
    h.append(100.0, "c")

    assert h.get(0.0) == "a"
    assert h.get(5.0) == "a"   # between entries: returns most recent
    assert h.get(10.0) == "b"
    assert h.get(99.9) == "b"
    assert h.get(100.0) == "c"
    assert h.get(1e9) == "c"   # beyond last entry: returns last


def test_append_only_enforced() -> None:
    h = History()
    h.append(10.0, "x")
    with pytest.raises(ValueError):
        h.append(10.0, "y")   # same time
    with pytest.raises(ValueError):
        h.append(5.0, "z")    # earlier time


def test_get_before_start_raises() -> None:
    h = History()
    h.append(50.0, "x")
    with pytest.raises(ValueError):
        h.get(0.0)


def test_empty_history_raises() -> None:
    h = History()
    with pytest.raises(ValueError):
        h.get(0.0)


def test_len_and_times() -> None:
    h = History()
    assert len(h) == 0
    h.append(1.0, None)
    h.append(2.0, None)
    assert len(h) == 2
    assert h.times == [1.0, 2.0]
    assert h.earliest_time == 1.0
    assert h.latest_time == 2.0
