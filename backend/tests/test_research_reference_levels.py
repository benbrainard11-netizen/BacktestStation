"""Tests for reference-level computation."""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import pytest

from app.research.reference_levels import compute_reference_level

UTC = timezone.utc


def _bars(rows: list[tuple[datetime, float, float, float, float]]) -> pd.DataFrame:
    """Build an OHLC frame with a tz-aware UTC DatetimeIndex.
    rows = [(ts, open, high, low, close), ...]"""
    df = pd.DataFrame(
        [{"open": o, "high": h, "low": lo, "close": c} for ts, o, h, lo, c in rows],
        index=pd.DatetimeIndex([r[0] for r in rows], tz=UTC),
    )
    return df


def _ts(d: int, h: int = 12, m: int = 0) -> datetime:
    return datetime(2026, 5, d, h, m, tzinfo=UTC)


def test_high_returns_max_with_ts():
    df = _bars([
        (_ts(1, 10), 100, 105, 99, 104),
        (_ts(1, 11), 104, 110, 103, 109),  # max here
        (_ts(1, 12), 109, 108, 102, 105),
    ])
    ref = compute_reference_level(
        df, side="high", start_utc=_ts(1, 0), end_utc=_ts(2, 0),
    )
    assert ref is not None
    assert ref.value == pytest.approx(110.0)
    assert ref.ts_utc == _ts(1, 11)
    assert ref.n_bars == 3


def test_low_returns_min_with_ts():
    df = _bars([
        (_ts(1, 10), 100, 105, 99, 104),
        (_ts(1, 11), 104, 110, 95, 100),  # min here
        (_ts(1, 12), 100, 102, 98, 99),
    ])
    ref = compute_reference_level(
        df, side="low", start_utc=_ts(1, 0), end_utc=_ts(2, 0),
    )
    assert ref is not None
    assert ref.value == pytest.approx(95.0)
    assert ref.ts_utc == _ts(1, 11)


def test_half_open_excludes_end():
    df = _bars([
        (_ts(1, 10), 100, 200, 50, 150),  # included
        (_ts(2, 0), 150, 999, 100, 200),  # at end_utc → excluded
    ])
    ref = compute_reference_level(
        df, side="high", start_utc=_ts(1, 0), end_utc=_ts(2, 0),
    )
    assert ref is not None
    assert ref.value == pytest.approx(200.0)
    assert ref.ts_utc == _ts(1, 10)


def test_empty_period_returns_none():
    df = _bars([
        (_ts(1, 10), 100, 105, 99, 104),
    ])
    ref = compute_reference_level(
        df, side="high", start_utc=_ts(2, 0), end_utc=_ts(3, 0),
    )
    assert ref is None


def test_empty_dataframe_returns_none():
    df = pd.DataFrame(columns=["open", "high", "low", "close"])
    df.index = pd.DatetimeIndex([], tz=UTC)
    ref = compute_reference_level(
        df, side="high", start_utc=_ts(1, 0), end_utc=_ts(2, 0),
    )
    assert ref is None


def test_tied_extreme_first_ts_wins():
    """Two bars with the same high → the EARLIEST ts wins (stable)."""
    df = _bars([
        (_ts(1, 10), 100, 110, 95, 105),  # high = 110, earliest
        (_ts(1, 11), 105, 110, 100, 108),  # high = 110, later
        (_ts(1, 12), 108, 109, 100, 105),
    ])
    ref = compute_reference_level(
        df, side="high", start_utc=_ts(1, 0), end_utc=_ts(2, 0),
    )
    assert ref is not None
    assert ref.ts_utc == _ts(1, 10)
