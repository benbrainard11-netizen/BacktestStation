"""Engine-enforced trading-hours window.

Verifies the `session_start_hour` / `session_end_hour` fields on
`RunConfig` actually gate `strategy.on_bar()` — bars outside the
window must not produce strategy decisions, even from a strategy
that always wants to enter.
"""

from __future__ import annotations

import datetime as dt

import pytest

from app.backtest.engine import RunConfig, run
from app.backtest.orders import BracketOrder, OrderIntent, Side
from app.backtest.strategy import Bar, Context, Strategy


def _utc(year: int, month: int, day: int, hour: int, minute: int) -> dt.datetime:
    return dt.datetime(year, month, day, hour, minute, tzinfo=dt.timezone.utc)


def _bar(ts: dt.datetime, price: float = 21000.0) -> Bar:
    return Bar(
        ts_event=ts,
        symbol="NQ.c.0",
        open=price,
        high=price + 5,
        low=price - 5,
        close=price + 1,
        volume=100,
        trade_count=10,
        vwap=price,
    )


class AlwaysEnterStrategy(Strategy):
    """Records every bar it sees and submits one entry per bar."""

    name = "always_enter"

    def __init__(self) -> None:
        self.bars_seen: list[dt.datetime] = []

    def on_bar(self, bar: Bar, context: Context) -> list[OrderIntent]:
        self.bars_seen.append(bar.ts_event)
        return []  # don't actually need to submit; just record


def test_session_window_gates_on_bar():
    """With session 9-14 ET, only bars at ET hours 9-13 reach on_bar()."""
    # April 24 2026 (DST in effect; ET = UTC-4).
    # 5:00 ET = 9:00 UTC  → outside window
    # 9:30 ET = 13:30 UTC → inside (hour=9)
    # 13:00 ET = 17:00 UTC → inside (hour=13)
    # 14:00 ET = 18:00 UTC → outside window (end is exclusive)
    # 16:00 ET = 20:00 UTC → outside window
    bars = [
        _bar(_utc(2026, 4, 24, 9, 0)),   # 5:00 ET — outside
        _bar(_utc(2026, 4, 24, 13, 30)), # 9:30 ET — inside
        _bar(_utc(2026, 4, 24, 13, 31)), # 9:31 ET — inside
        _bar(_utc(2026, 4, 24, 17, 0)),  # 13:00 ET — inside
        _bar(_utc(2026, 4, 24, 18, 0)),  # 14:00 ET — outside
        _bar(_utc(2026, 4, 24, 20, 0)),  # 16:00 ET — outside
    ]
    config = RunConfig(
        strategy_name="t",
        symbol="NQ.c.0",
        timeframe="1m",
        start="2026-04-24",
        end="2026-04-25",
        session_start_hour=9,
        session_end_hour=14,
        session_tz="America/New_York",
    )
    strat = AlwaysEnterStrategy()
    run(strat, bars, config)

    seen_hours_et = sorted(
        {b.astimezone(__import__("zoneinfo").ZoneInfo("America/New_York")).hour for b in strat.bars_seen}
    )
    # Only ET hours 9 and 13 should have shown up.
    assert seen_hours_et == [9, 13], f"unexpected ET hours: {seen_hours_et}"
    assert len(strat.bars_seen) == 3  # 9:30, 9:31, 13:00


def test_session_window_off_by_default():
    """When session_*_hour is unset, strategy sees every bar (current behavior)."""
    bars = [
        _bar(_utc(2026, 4, 24, 5, 0)),
        _bar(_utc(2026, 4, 24, 14, 0)),
        _bar(_utc(2026, 4, 24, 22, 0)),
    ]
    config = RunConfig(
        strategy_name="t",
        symbol="NQ.c.0",
        timeframe="1m",
        start="2026-04-24",
        end="2026-04-25",
    )
    strat = AlwaysEnterStrategy()
    run(strat, bars, config)
    assert len(strat.bars_seen) == 3
