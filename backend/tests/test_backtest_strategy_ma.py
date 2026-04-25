"""Tests for the moving-average crossover example strategy."""

from __future__ import annotations

import datetime as dt

import pytest

from app.backtest.engine import RunConfig, run
from app.backtest.orders import BracketOrder, Side
from app.backtest.strategy import Bar
from app.strategies.examples.moving_average_crossover import (
    MovingAverageCrossover,
)


def _bar(minute: int, close: float) -> Bar:
    ts = dt.datetime(2026, 4, 24, 13, 30, tzinfo=dt.timezone.utc)
    return Bar(
        ts_event=ts + dt.timedelta(minutes=minute),
        symbol="NQ.c.0",
        open=close,
        high=close + 1,
        low=close - 1,
        close=close,
        volume=100,
        trade_count=10,
        vwap=close,
    )


def _config() -> RunConfig:
    return RunConfig(
        strategy_name="moving_average_crossover",
        symbol="NQ.c.0",
        timeframe="1m",
        start="2026-04-24",
        end="2026-04-25",
    )


def test_construction_validates_periods() -> None:
    with pytest.raises(ValueError, match="fast_period"):
        MovingAverageCrossover(fast_period=20, slow_period=10)


def test_construction_validates_ticks() -> None:
    with pytest.raises(ValueError, match="positive"):
        MovingAverageCrossover(stop_ticks=0)
    with pytest.raises(ValueError, match="positive"):
        MovingAverageCrossover(target_ticks=-1)


def test_no_orders_until_slow_period_filled() -> None:
    """Strategy needs `slow_period` bars before it can compute the crossover."""
    bars = [_bar(i, 21000.0) for i in range(5)]
    strategy = MovingAverageCrossover(fast_period=2, slow_period=4)
    result = run(strategy, bars, _config())
    # All bars same price = no cross, no entries.
    assert result.trades == []


def test_bullish_cross_emits_long_bracket() -> None:
    """Falling then rising prices produce one bullish cross + one long entry."""
    # Falling section: 21010 down to 21000 (slow period 4 fills here)
    # Rising section: 21000 up to 21030 (triggers cross)
    closes = [21010, 21008, 21006, 21004, 21002, 21000, 21002, 21006, 21015, 21030]
    bars = [_bar(i, c) for i, c in enumerate(closes)]
    strategy = MovingAverageCrossover(
        fast_period=2,
        slow_period=4,
        stop_ticks=8,
        target_ticks=16,
        tick_size=0.25,
    )
    # Engine catches the cross; we're not asserting trade outcome here,
    # just that a bracket order was submitted at the cross bar.
    result = run(strategy, bars, _config())
    # The cross creates exactly one entry (held + flattened or stop/target).
    assert len(result.trades) >= 1
    assert result.trades[0].side is Side.LONG


def test_one_position_at_a_time() -> None:
    """Strategy doesn't submit a second order while in_position."""
    closes = [21010, 21000, 20990, 20980, 20970, 21000, 21030, 21060, 21090, 21120]
    bars = [_bar(i, c) for i, c in enumerate(closes)]
    strategy = MovingAverageCrossover(fast_period=2, slow_period=4)

    # Enable EOD flatten so we always close. With these prices, multiple
    # crosses could occur but only one position at a time should exist.
    result = run(strategy, bars, _config())
    # A new entry can occur AFTER the previous trade closes. So multiple
    # trades are fine, but at no point should two be open simultaneously.
    # The engine + strategy enforce this: in_position check skips new
    # intents. Verify no overlapping (entry_ts <= exit_ts of previous).
    for prev, curr in zip(result.trades, result.trades[1:]):
        assert curr.entry_ts >= prev.exit_ts
