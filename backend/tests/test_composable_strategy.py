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


def test_spec_aux_symbols_default_empty():
    """Spec without aux_symbols field returns an empty list, not an error."""
    spec = ComposableSpec.from_dict({"entry_long": [], "entry_short": []})
    assert spec.aux_symbols == []


def test_spec_aux_symbols_round_trip():
    """aux_symbols list flows through from_dict cleanly."""
    spec = ComposableSpec.from_dict(
        {
            "entry_long": [],
            "entry_short": [],
            "aux_symbols": ["ES.c.0", "YM.c.0"],
        }
    )
    assert spec.aux_symbols == ["ES.c.0", "YM.c.0"]


def test_spec_rejects_non_list_aux_symbols():
    with pytest.raises(ValueError, match="aux_symbols must be a list"):
        ComposableSpec.from_dict({"aux_symbols": "ES.c.0"})


def test_spec_rejects_non_string_aux_symbol_entry():
    with pytest.raises(ValueError, match="aux_symbols\\[0\\]"):
        ComposableSpec.from_dict({"aux_symbols": [42]})


# ── role-tagged buckets (setup / trigger / filter) ────────────────────


def test_spec_role_buckets_default_empty():
    spec = ComposableSpec.from_dict({})
    assert spec.setup_long == []
    assert spec.trigger_long == []
    assert spec.setup_short == []
    assert spec.trigger_short == []
    assert spec.filter == []
    assert spec.filter_long == []
    assert spec.filter_short == []


def test_spec_setup_window_default_persistent():
    spec = ComposableSpec.from_dict({})
    assert spec.setup_window.long is None
    assert spec.setup_window.short is None


def test_spec_setup_window_round_trip():
    spec = ComposableSpec.from_dict(
        {"setup_window": {"long": 5, "short": 12}}
    )
    assert spec.setup_window.long == 5
    assert spec.setup_window.short == 12


def test_spec_setup_window_rejects_non_int():
    with pytest.raises(ValueError, match="setup_window.long"):
        ComposableSpec.from_dict({"setup_window": {"long": "five"}})


def test_spec_setup_window_rejects_zero():
    with pytest.raises(ValueError, match="setup_window.short"):
        ComposableSpec.from_dict({"setup_window": {"short": 0}})


def test_spec_setup_window_rejects_negative():
    with pytest.raises(ValueError, match="setup_window.long"):
        ComposableSpec.from_dict({"setup_window": {"long": -3}})


def test_spec_setup_window_null_means_persistent():
    spec = ComposableSpec.from_dict({"setup_window": {"long": None, "short": 10}})
    assert spec.setup_window.long is None
    assert spec.setup_window.short == 10


def test_spec_role_buckets_round_trip_each():
    spec = ComposableSpec.from_dict(
        {
            "setup_long": [{"feature": "prior_level_sweep", "params": {"level": "PDH"}}],
            "trigger_long": [{"feature": "decisive_close", "params": {"direction": "BULLISH"}}],
            "setup_short": [{"feature": "prior_level_sweep", "params": {"level": "PDL"}}],
            "trigger_short": [{"feature": "decisive_close", "params": {"direction": "BEARISH"}}],
            "filter": [{"feature": "time_window", "params": {"start_hour": 9.5, "end_hour": 14}}],
            "filter_long": [{"feature": "volume_filter", "params": {"min_mult": 1.5}}],
            "filter_short": [{"feature": "volume_filter", "params": {"min_mult": 2.0}}],
        }
    )
    assert spec.setup_long[0].feature == "prior_level_sweep"
    assert spec.trigger_long[0].feature == "decisive_close"
    assert spec.setup_short[0].params == {"level": "PDL"}
    assert spec.trigger_short[0].params == {"direction": "BEARISH"}
    assert spec.filter[0].feature == "time_window"
    assert spec.filter_long[0].params == {"min_mult": 1.5}
    assert spec.filter_short[0].params == {"min_mult": 2.0}


def test_spec_filter_rejects_non_object_entry():
    with pytest.raises(ValueError, match="filter:"):
        ComposableSpec.from_dict({"filter": ["not_an_object"]})


# ── backward compatibility: entry_long / entry_short → trigger_* ──────


def test_spec_old_shape_migrates_entry_long_to_trigger_long():
    """Old (pre-2026-05-02) specs with entry_long should populate trigger_long."""
    spec = ComposableSpec.from_dict(
        {
            "entry_long": [{"feature": "decisive_close", "params": {"direction": "BULLISH"}}],
            "entry_short": [{"feature": "decisive_close", "params": {"direction": "BEARISH"}}],
        }
    )
    assert len(spec.trigger_long) == 1
    assert spec.trigger_long[0].feature == "decisive_close"
    assert spec.trigger_long[0].params == {"direction": "BULLISH"}
    assert len(spec.trigger_short) == 1
    assert spec.trigger_short[0].params == {"direction": "BEARISH"}
    # Setup buckets stay empty (old shape had no notion of setup).
    assert spec.setup_long == []
    assert spec.setup_short == []


def test_spec_old_shape_mirrors_into_entry_fields_for_engine_compat():
    """During the migration window, the engine still reads entry_long.
    Mirror triggers back so it keeps working."""
    spec = ComposableSpec.from_dict(
        {"entry_long": [{"feature": "decisive_close", "params": {}}]}
    )
    assert len(spec.entry_long) == 1
    assert spec.entry_long[0].feature == "decisive_close"


def test_spec_new_shape_overrides_old_when_both_present():
    spec = ComposableSpec.from_dict(
        {
            "entry_long": [{"feature": "old_feature", "params": {}}],
            "trigger_long": [{"feature": "new_feature", "params": {}}],
        }
    )
    # New keys win; old is ignored (with a logged warning, not asserted here).
    assert len(spec.trigger_long) == 1
    assert spec.trigger_long[0].feature == "new_feature"


def test_spec_new_shape_alone_works():
    spec = ComposableSpec.from_dict(
        {
            "trigger_long": [{"feature": "decisive_close", "params": {}}],
            "trigger_short": [],
        }
    )
    assert spec.trigger_long[0].feature == "decisive_close"
    assert spec.entry_long[0].feature == "decisive_close"  # mirrored


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
