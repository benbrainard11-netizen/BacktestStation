"""Engine asserts UTC bar timestamps.

The engine assumes tz-aware UTC timestamps internally (HTF candle
bounds, session gating, aux-bar lookups all rely on it). Catch the
silent class of bug where ET-localized bars get fed in.
"""

from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

import pytest

from app.backtest.engine import RunConfig, run
from app.backtest.strategy import Bar, Strategy


def _make_bar(ts: dt.datetime) -> Bar:
    return Bar(
        ts_event=ts,
        symbol="NQ.c.0",
        open=21000.0,
        high=21010.0,
        low=20995.0,
        close=21005.0,
        volume=100,
        trade_count=10,
        vwap=21002.0,
    )


def _config() -> RunConfig:
    return RunConfig(
        strategy_name="t",
        symbol="NQ.c.0",
        timeframe="1m",
        start="2026-04-24",
        end="2026-04-25",
    )


def test_rejects_naive_timestamps():
    """Bars without tzinfo raise a clear ValueError."""
    naive = dt.datetime(2026, 4, 24, 13, 30)  # no tzinfo
    with pytest.raises(ValueError, match="must be tz-aware"):
        run(Strategy(), [_make_bar(naive)], _config())


def test_accepts_et_localized_timestamps():
    """ET-localized bars are tz-aware; engine accepts them. Existing
    fractal-amd regression tests rely on this (their fixtures use ET)."""
    et_ts = dt.datetime(2026, 4, 24, 9, 30, tzinfo=ZoneInfo("America/New_York"))
    run(Strategy(), [_make_bar(et_ts)], _config())  # no exception


def test_accepts_utc_timestamps():
    """UTC timestamps pass without error (canonical / runner path)."""
    utc_ts = dt.datetime(2026, 4, 24, 13, 30, tzinfo=dt.timezone.utc)
    run(Strategy(), [_make_bar(utc_ts)], _config())


def test_empty_bars_list_does_not_raise():
    """No bars = nothing to validate; engine handles it."""
    run(Strategy(), [], _config())
