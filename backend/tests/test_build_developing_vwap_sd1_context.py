"""Smoke test for the build_developing_vwap_sd1_context script.

Verifies the builder produces the expected column shape and no-NaN
output for a small synthetic anchor matrix + fake bar reader. The
helper math is covered exhaustively in test_developing_vwap_sd1.py;
this test only validates the wiring (column naming, merge keys,
per-row computation).
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

# The script lives outside the app package; add its directory.
THIS = Path(__file__).resolve()
SCRIPTS_ML = THIS.parents[1] / "scripts" / "ml"
sys.path.insert(0, str(SCRIPTS_ML))

from build_developing_vwap_sd1_context import (  # noqa: E402
    PERIOD_SHORT,
    build_context,
    fsd1_columns,
)
from app.research.developing_vwap_sd1 import ALL_PERIODS  # noqa: E402

UTC = timezone.utc
ET = ZoneInfo("America/New_York")


def _flat_bars(start: datetime, minutes: int, price: float = 21_000.0) -> pd.DataFrame:
    rows = []
    for i in range(minutes):
        rows.append(
            {
                "ts": start + timedelta(minutes=i),
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "volume": 100.0,
            }
        )
    df = pd.DataFrame(rows).set_index("ts")
    df.index = pd.to_datetime(df.index, utc=True)
    return df


class FakeBarLoader:
    """Stand-in for read_bars(symbol=, timeframe=, start=, end=)."""

    def __init__(self, frames: dict[str, pd.DataFrame]) -> None:
        self.frames = frames
        self.calls: list[tuple[str, object, object]] = []

    def __call__(self, *, symbol, timeframe, start, end, **kw):
        self.calls.append((symbol, start, end))
        df = self.frames.get(symbol)
        if df is None:
            return pd.DataFrame(
                columns=["open", "high", "low", "close", "volume"],
                index=pd.DatetimeIndex([], tz="UTC", name="ts_event"),
            )
        # Reader returns the frame with ts_event as a column to match
        # the read_bars contract; emulate that.
        out = df.copy()
        out.index.name = "ts_event"
        out = out.reset_index()
        return out


def _anchor_matrix(symbol: str, cutoffs: list[datetime]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "anchor.event_id": [f"evt_{i}" for i in range(len(cutoffs))],
            "asof.snapshot": ["at_fire"] * len(cutoffs),
            "anchor.primary_symbol": [symbol] * len(cutoffs),
            "asof.feature_cutoff_ts": [pd.Timestamp(c) for c in cutoffs],
            "anchor.close_price": [21_000.0] * len(cutoffs),
        }
    )


def test_builder_produces_expected_columns() -> None:
    # Mon 18:00 ET in UTC == Mon 22:00 UTC.
    day_start = datetime(2026, 5, 4, 22, 0, tzinfo=UTC)
    bars = _flat_bars(day_start, minutes=20 * 60)
    loader = FakeBarLoader({"NQ.c.0": bars})

    cutoffs = [
        day_start + timedelta(hours=1),
        day_start + timedelta(hours=5),
        day_start + timedelta(hours=10),
    ]
    matrix = _anchor_matrix("NQ.c.0", cutoffs)
    ctx = build_context(matrix, bar_loader=loader)

    expected = set(fsd1_columns())
    actual = set(c for c in ctx.columns if c.startswith("fsd1."))
    assert expected == actual

    assert len(ctx) == 3
    assert list(ctx["anchor.event_id"]) == ["evt_0", "evt_1", "evt_2"]


def test_builder_no_lookahead() -> None:
    """A cutoff 1h into the day should see ~60 day-period bars; a
    cutoff 5h in should see ~300. Same matrix, two rows, monotone bars."""
    day_start = datetime(2026, 5, 4, 22, 0, tzinfo=UTC)
    bars = _flat_bars(day_start, minutes=20 * 60)
    loader = FakeBarLoader({"NQ.c.0": bars})

    cutoffs = [
        day_start + timedelta(hours=1),
        day_start + timedelta(hours=5),
    ]
    matrix = _anchor_matrix("NQ.c.0", cutoffs)
    ctx = build_context(matrix, bar_loader=loader)

    day_col = f"fsd1.{PERIOD_SHORT['globex_day']}.n_bars"
    assert int(ctx.iloc[0][day_col]) == 60
    assert int(ctx.iloc[1][day_col]) == 300


def test_builder_constant_price_zero_sd() -> None:
    """With constant typical price, SD is 0 and VWAP is the price."""
    day_start = datetime(2026, 5, 4, 22, 0, tzinfo=UTC)
    bars = _flat_bars(day_start, minutes=20 * 60, price=21_000.0)
    loader = FakeBarLoader({"NQ.c.0": bars})

    cutoffs = [day_start + timedelta(hours=2)]
    matrix = _anchor_matrix("NQ.c.0", cutoffs)
    ctx = build_context(matrix, bar_loader=loader)

    day_vwap = ctx.iloc[0][f"fsd1.{PERIOD_SHORT['globex_day']}.vwap_pts"]
    day_sd = ctx.iloc[0][f"fsd1.{PERIOD_SHORT['globex_day']}.sd_pts"]
    assert day_vwap == pytest.approx(21_000.0)
    assert day_sd == pytest.approx(0.0)


def test_builder_periods_filter_limits_columns() -> None:
    day_start = datetime(2026, 5, 4, 22, 0, tzinfo=UTC)
    bars = _flat_bars(day_start, minutes=20 * 60)
    loader = FakeBarLoader({"NQ.c.0": bars})

    cutoffs = [day_start + timedelta(hours=2)]
    matrix = _anchor_matrix("NQ.c.0", cutoffs)
    ctx = build_context(matrix, periods=("globex_day",), bar_loader=loader)

    fsd1_cols = [c for c in ctx.columns if c.startswith("fsd1.")]
    # All retained columns must reference the "day" prefix only.
    for c in fsd1_cols:
        assert c.startswith("fsd1.day.")


def test_builder_missing_symbol_yields_empty_rows() -> None:
    day_start = datetime(2026, 5, 4, 22, 0, tzinfo=UTC)
    loader = FakeBarLoader({})  # no symbols loaded

    cutoffs = [day_start + timedelta(hours=2)]
    matrix = _anchor_matrix("NQ.c.0", cutoffs)
    ctx = build_context(matrix, periods=("globex_day",), bar_loader=loader)

    assert ctx.iloc[0][f"fsd1.day.n_bars"] == 0
    # VWAP/SD are NaN (not 0.0) because no bars were available.
    assert pd.isna(ctx.iloc[0]["fsd1.day.vwap_pts"])
