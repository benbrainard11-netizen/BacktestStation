"""Composable strategy plugin — end-to-end + determinism."""

from __future__ import annotations

import datetime as dt

import pytest

from app.backtest.engine import RunConfig, run as engine_run
from app.backtest.strategy import Bar
from app.strategies.composable import ComposableStrategy
from app.strategies.composable.config import ComposableSpec


UTC = dt.timezone.utc


def _bar(
    ts: dt.datetime,
    open_: float = 21000.0,
    *,
    high: float | None = None,
    low: float | None = None,
    close: float | None = None,
    symbol: str = "NQ.c.0",
) -> Bar:
    return Bar(
        ts_event=ts,
        symbol=symbol,
        open=open_,
        high=open_ + 5 if high is None else high,
        low=open_ - 5 if low is None else low,
        close=open_ + 1 if close is None else close,
        volume=100,
        trade_count=10,
        vwap=open_,
    )


def _utc(year, month, day, hour, minute) -> dt.datetime:
    return dt.datetime(year, month, day, hour, minute, tzinfo=UTC)


# ── spec parsing ──────────────────────────────────────────────────────


def test_spec_from_dict_round_trips_minimal():
    raw = {
        "entry_long": [{"feature": "time_window", "params": {"start_hour": 9, "end_hour": 14}}],
        "entry_short": [],
        "stop": {"type": "fixed_pts", "stop_pts": 5.0},
        "target": {"type": "r_multiple", "r": 2.0},
        "qty": 1,
    }
    spec = ComposableSpec.from_dict(raw)
    assert len(spec.entry_long) == 1
    assert spec.entry_long[0].feature == "time_window"
    assert spec.stop.stop_pts == 5.0
    assert spec.target.r == 2.0


def test_spec_rejects_unknown_feature():
    raw = {
        "entry_long": [{"feature": "i_do_not_exist", "params": {}}],
    }
    spec = ComposableSpec.from_dict(raw)
    with pytest.raises(ValueError, match="Unknown feature"):
        ComposableStrategy(spec)


def test_spec_rejects_bad_stop_type():
    with pytest.raises(ValueError, match="stop.type"):
        ComposableSpec.from_dict({"stop": {"type": "totally_made_up"}})


# ── e2e: PDH-sweep + time-window ──────────────────────────────────────


def test_composable_fires_on_pdh_sweep_inside_session():
    """Day 1: high = 21010. Day 2 inside RTH: bar prints high 21020 →
    PDH swept above → BEARISH bias → SHORT entry fires."""
    base = _utc(2026, 4, 24, 14, 30)  # 10:30 ET, day 1
    bars: list[Bar] = []
    # Day 1: 5 bars, high 21010
    for i in range(5):
        bars.append(
            _bar(base + dt.timedelta(minutes=i),
                 open_=21000, high=21010 if i == 2 else 21008,
                 low=20995, close=21005)
        )
    # Day 2: 5 bars, last bar at 14:35 UTC (10:35 ET) sweeps high
    base2 = _utc(2026, 4, 25, 14, 30)
    for i in range(5):
        if i == 4:
            bars.append(_bar(base2 + dt.timedelta(minutes=i),
                             open_=21015, high=21020, low=21013, close=21018))
        else:
            bars.append(_bar(base2 + dt.timedelta(minutes=i),
                             open_=21010, high=21013, low=21008, close=21012))

    spec = ComposableSpec.from_dict({
        "entry_long": [],
        "entry_short": [
            {"feature": "prior_level_sweep", "params": {"level": "PDH", "direction": "above"}},
            {"feature": "time_window", "params": {"start_hour": 9.5, "end_hour": 14.0}},
        ],
        "stop": {"type": "fixed_pts", "stop_pts": 10.0},
        "target": {"type": "r_multiple", "r": 3.0},
        "qty": 1,
        "max_trades_per_day": 2,
    })
    strat = ComposableStrategy(spec)

    config = RunConfig(
        strategy_name="composable",
        symbol="NQ.c.0",
        timeframe="1m",
        start="2026-04-24",
        end="2026-04-25",
        flatten_on_last_bar=True,
        params={},
    )
    result = engine_run(strat, bars, config)
    # Engine emits one bracket order, fills next bar, then EOD-flattens
    # (only 10 bars total, so no real exit). Just assert the entry fired.
    assert len(result.trades) >= 1


def test_composable_no_entry_outside_session():
    """Same day-1/day-2 sweep, but day 2's sweep happens at 06:00 ET
    (outside time_window 9:30-14) → no entry."""
    base = _utc(2026, 4, 24, 14, 30)
    bars: list[Bar] = []
    for i in range(5):
        bars.append(
            _bar(base + dt.timedelta(minutes=i),
                 open_=21000, high=21010, low=20995, close=21005)
        )
    # Day 2 at 06:00 ET = 10:00 UTC
    base2 = _utc(2026, 4, 25, 10, 0)
    for i in range(5):
        if i == 4:
            bars.append(_bar(base2 + dt.timedelta(minutes=i),
                             open_=21015, high=21025, low=21013, close=21020))
        else:
            bars.append(_bar(base2 + dt.timedelta(minutes=i),
                             open_=21010, high=21013, low=21008, close=21012))

    spec = ComposableSpec.from_dict({
        "entry_long": [],
        "entry_short": [
            {"feature": "prior_level_sweep", "params": {"level": "PDH"}},
            {"feature": "time_window", "params": {"start_hour": 9.5, "end_hour": 14.0}},
        ],
        "stop": {"type": "fixed_pts", "stop_pts": 10.0},
        "target": {"type": "r_multiple", "r": 3.0},
    })
    strat = ComposableStrategy(spec)
    config = RunConfig(
        strategy_name="composable",
        symbol="NQ.c.0",
        timeframe="1m",
        start="2026-04-24",
        end="2026-04-25",
        flatten_on_last_bar=True,
        params={},
    )
    result = engine_run(strat, bars, config)
    # Time filter blocks the entry → 0 trades
    assert result.trades == []


# ── determinism ───────────────────────────────────────────────────────


def test_composable_determinism_same_inputs_same_outputs():
    """Run the same spec on the same bars twice. Trades must match."""
    base = _utc(2026, 4, 24, 14, 30)
    bars = [
        _bar(base + dt.timedelta(minutes=i), open_=21000 + i, close=21001 + i)
        for i in range(20)
    ]
    spec_raw = {
        "entry_long": [
            {"feature": "time_window", "params": {"start_hour": 0, "end_hour": 24}},
        ],
        "stop": {"type": "fixed_pts", "stop_pts": 5.0},
        "target": {"type": "r_multiple", "r": 2.0},
        "max_trades_per_day": 5,
        "entry_dedup_minutes": 1,
    }
    config = RunConfig(
        strategy_name="composable",
        symbol="NQ.c.0",
        timeframe="1m",
        start="2026-04-24",
        end="2026-04-25",
        flatten_on_last_bar=True,
        params={},
    )

    a_trades = engine_run(
        ComposableStrategy(ComposableSpec.from_dict(spec_raw)), bars, config
    ).trades
    b_trades = engine_run(
        ComposableStrategy(ComposableSpec.from_dict(spec_raw)), bars, config
    ).trades
    assert len(a_trades) == len(b_trades)
    for a, b in zip(a_trades, b_trades):
        assert a.entry_ts == b.entry_ts
        assert a.entry_price == b.entry_price
        assert a.exit_price == b.exit_price
        assert a.r_multiple == b.r_multiple
