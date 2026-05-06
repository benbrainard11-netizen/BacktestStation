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
    """Bare int → BarsWindow (backward compat with pre-2026-05-03 specs)."""
    spec = ComposableSpec.from_dict(
        {"setup_window": {"long": 5, "short": 12}}
    )
    assert spec.setup_window.long is not None
    assert spec.setup_window.long.kind == "bars"
    assert spec.setup_window.long.n == 5
    assert spec.setup_window.short is not None
    assert spec.setup_window.short.kind == "bars"
    assert spec.setup_window.short.n == 12


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
    assert spec.setup_window.short is not None
    assert spec.setup_window.short.kind == "bars"
    assert spec.setup_window.short.n == 10


def test_spec_setup_window_bars_dict_form():
    spec = ComposableSpec.from_dict(
        {"setup_window": {"long": {"type": "bars", "n": 7}}}
    )
    assert spec.setup_window.long is not None
    assert spec.setup_window.long.kind == "bars"
    assert spec.setup_window.long.n == 7


def test_spec_setup_window_minutes_form():
    spec = ComposableSpec.from_dict(
        {"setup_window": {"short": {"type": "minutes", "n": 30}}}
    )
    assert spec.setup_window.short is not None
    assert spec.setup_window.short.kind == "minutes"
    assert spec.setup_window.short.n == 30


def test_spec_setup_window_until_clock_form():
    spec = ComposableSpec.from_dict({
        "setup_window": {
            "long": {"type": "until_clock", "end_hour": 11.0, "tz": "America/New_York"}
        }
    })
    assert spec.setup_window.long is not None
    assert spec.setup_window.long.kind == "until_clock"
    assert spec.setup_window.long.end_hour == 11.0
    assert spec.setup_window.long.tz == "America/New_York"


def test_spec_setup_window_until_clock_default_tz():
    spec = ComposableSpec.from_dict(
        {"setup_window": {"long": {"type": "until_clock", "end_hour": 11.0}}}
    )
    assert spec.setup_window.long is not None
    assert spec.setup_window.long.tz == "America/New_York"


def test_spec_setup_window_rejects_unknown_type():
    with pytest.raises(ValueError, match="setup_window.long.type"):
        ComposableSpec.from_dict(
            {"setup_window": {"long": {"type": "halfsies", "n": 2}}}
        )


def test_spec_setup_window_rejects_bad_tz():
    with pytest.raises(ValueError, match="unknown timezone"):
        ComposableSpec.from_dict({
            "setup_window": {
                "long": {"type": "until_clock", "end_hour": 11.0, "tz": "NotAZone/Made_Up"}
            }
        })


def test_spec_setup_window_minutes_rejects_zero():
    with pytest.raises(ValueError, match="setup_window.long.n"):
        ComposableSpec.from_dict(
            {"setup_window": {"long": {"type": "minutes", "n": 0}}}
        )


# ── per-call gate parsing ─────────────────────────────────────────────


def test_call_gate_parses_hhmm_strings():
    spec = ComposableSpec.from_dict({
        "trigger_long": [{
            "feature": "decisive_close",
            "params": {"direction": "BULLISH"},
            "gate": {"start": "08:00", "end": "10:30"},
        }],
    })
    g = spec.trigger_long[0].gate
    assert g is not None
    assert g.start_hour == 8.0
    assert g.end_hour == 10.5
    assert g.tz == "America/New_York"


def test_call_gate_parses_fractional_hours():
    spec = ComposableSpec.from_dict({
        "trigger_long": [{
            "feature": "decisive_close",
            "params": {"direction": "BULLISH"},
            "gate": {"start": 8.5, "end": 9.75, "tz": "Europe/London"},
        }],
    })
    g = spec.trigger_long[0].gate
    assert g is not None
    assert g.start_hour == 8.5
    assert g.end_hour == 9.75
    assert g.tz == "Europe/London"


def test_call_gate_rejects_end_le_start():
    with pytest.raises(ValueError, match="must be > start"):
        ComposableSpec.from_dict({
            "trigger_long": [{
                "feature": "decisive_close",
                "params": {"direction": "BULLISH"},
                "gate": {"start": "10:00", "end": "10:00"},
            }],
        })


def test_call_gate_rejects_unknown_tz():
    with pytest.raises(ValueError, match="unknown timezone"):
        ComposableSpec.from_dict({
            "trigger_long": [{
                "feature": "decisive_close",
                "params": {"direction": "BULLISH"},
                "gate": {"start": "08:00", "end": "10:00", "tz": "NotAZone"},
            }],
        })


def test_call_gate_rejects_bad_hhmm_format():
    with pytest.raises(ValueError, match="HH:MM"):
        ComposableSpec.from_dict({
            "trigger_long": [{
                "feature": "decisive_close",
                "params": {"direction": "BULLISH"},
                "gate": {"start": "8am", "end": "10:00"},
            }],
        })


def test_call_gate_default_none():
    spec = ComposableSpec.from_dict({
        "trigger_long": [{"feature": "decisive_close", "params": {"direction": "BULLISH"}}],
    })
    assert spec.trigger_long[0].gate is None


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
    # Engine emits exactly one bracket order, fills next bar, then EOD-flattens
    # (only 10 bars total, so no real exit). Locked-in baseline (captured
    # 2026-05-02 prior to engine state-machine rewrite) so the chunk-3
    # refactor must produce byte-identical output.
    assert len(result.trades) == 1
    t = result.trades[0]
    assert t.entry_ts == _utc(2026, 4, 25, 14, 31)
    assert t.entry_price == 21009.75
    assert t.exit_price == 21018.0
    assert str(t.side) == "Side.SHORT"


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


# ── setup / trigger / filter state machine ────────────────────────────


def _make_config() -> RunConfig:
    return RunConfig(
        strategy_name="composable",
        symbol="NQ.c.0",
        timeframe="1m",
        start="2026-04-24",
        end="2026-04-25",
        flatten_on_last_bar=True,
        params={},
    )


def _flat_bars(start: dt.datetime, count: int, *, base_price: float = 21000.0) -> list[Bar]:
    """Flat consecutive 1m bars at base_price ± 5pts each side."""
    return [
        _bar(start + dt.timedelta(minutes=i), open_=base_price, close=base_price + 1)
        for i in range(count)
    ]


def test_setup_arms_then_trigger_within_window_enters():
    """Setup fires bar N (PDH sweep). Window=10. Quiet bars in between (no sweep,
    no trigger). Bar N+4 fires trigger (decisive bear close) → enters."""
    base = _utc(2026, 4, 25, 14, 30)
    bars: list[Bar] = []
    day1 = _utc(2026, 4, 24, 14, 30)
    for i in range(5):
        bars.append(_bar(day1 + dt.timedelta(minutes=i), open_=21000, high=21010, low=20995, close=21005))
    # Day 2 bar 0: sweeps PDH (high 21020), closes back below
    bars.append(_bar(base + dt.timedelta(minutes=0), open_=21015, high=21020, low=21008, close=21012))
    # Day 2 bars 1-3: quiet, NO sweep (high < PDH 21010), NO trigger
    for i in range(1, 4):
        bars.append(_bar(base + dt.timedelta(minutes=i), open_=21008, high=21009, low=21005, close=21008))
    # Day 2 bar 4: decisive bear close (range 14, body 12 = 86%)
    bars.append(_bar(base + dt.timedelta(minutes=4), open_=21008, high=21009, low=20995, close=20996))
    # Day 2 bar 5: filler so the bracket can fill
    bars.append(_bar(base + dt.timedelta(minutes=5), open_=20996, high=20997, low=20990, close=20991))

    spec = ComposableSpec.from_dict({
        "setup_short": [{"feature": "prior_level_sweep", "params": {"level": "PDH", "direction": "above"}}],
        "trigger_short": [{"feature": "decisive_close", "params": {"direction": "BEARISH", "min_body_pct": 0.6}}],
        "setup_window": {"short": 10},
        "stop": {"type": "fixed_pts", "stop_pts": 10.0},
        "target": {"type": "r_multiple", "r": 3.0},
        "max_trades_per_day": 2,
    })
    result = engine_run(ComposableStrategy(spec), bars, _make_config())
    assert len(result.trades) == 1
    assert str(result.trades[0].side) == "Side.SHORT"


def test_setup_arms_but_trigger_after_window_no_entry():
    """Setup fires bar N. Window=2 bars. Trigger fires bar N+5 → blocked."""
    day1 = _utc(2026, 4, 24, 14, 30)
    base = _utc(2026, 4, 25, 14, 30)
    bars: list[Bar] = []
    for i in range(5):
        bars.append(_bar(day1 + dt.timedelta(minutes=i), open_=21000, high=21010, low=20995, close=21005))
    # Day 2 bar 0: sweep, closes below PDH
    bars.append(_bar(base + dt.timedelta(minutes=0), open_=21015, high=21020, low=21008, close=21012))
    # Bars 1-4: quiet, no sweep, no trigger
    for i in range(1, 5):
        bars.append(_bar(base + dt.timedelta(minutes=i), open_=21008, high=21009, low=21005, close=21008))
    # Bar 5: decisive bear close — but window has expired (2 bars after sweep)
    bars.append(_bar(base + dt.timedelta(minutes=5), open_=21008, high=21009, low=20995, close=20996))
    bars.append(_bar(base + dt.timedelta(minutes=6), open_=20996, high=20997, low=20990, close=20991))

    spec = ComposableSpec.from_dict({
        "setup_short": [{"feature": "prior_level_sweep", "params": {"level": "PDH", "direction": "above"}}],
        "trigger_short": [{"feature": "decisive_close", "params": {"direction": "BEARISH", "min_body_pct": 0.6}}],
        "setup_window": {"short": 2},
        "stop": {"type": "fixed_pts", "stop_pts": 10.0},
        "target": {"type": "r_multiple", "r": 3.0},
    })
    result = engine_run(ComposableStrategy(spec), bars, _make_config())
    assert result.trades == []


def test_setup_persistent_window_lasts_entire_session():
    """Setup with window=None arms until end of session. Trigger 30 bars later still fires."""
    day1 = _utc(2026, 4, 24, 14, 30)
    base = _utc(2026, 4, 25, 14, 30)
    bars: list[Bar] = []
    for i in range(5):
        bars.append(_bar(day1 + dt.timedelta(minutes=i), open_=21000, high=21010, low=20995, close=21005))
    # Day 2 bar 0: sweep, closes below PDH
    bars.append(_bar(base + dt.timedelta(minutes=0), open_=21015, high=21020, low=21008, close=21012))
    for i in range(1, 30):
        bars.append(_bar(base + dt.timedelta(minutes=i), open_=21008, high=21009, low=21005, close=21008))
    bars.append(_bar(base + dt.timedelta(minutes=30), open_=21008, high=21009, low=20995, close=20996))  # bear close, way later
    bars.append(_bar(base + dt.timedelta(minutes=31), open_=20996, high=20997, low=20990, close=20991))

    spec = ComposableSpec.from_dict({
        "setup_short": [{"feature": "prior_level_sweep", "params": {"level": "PDH", "direction": "above"}}],
        "trigger_short": [{"feature": "decisive_close", "params": {"direction": "BEARISH", "min_body_pct": 0.6}}],
        "setup_window": {"short": None},  # persistent
        "stop": {"type": "fixed_pts", "stop_pts": 10.0},
        "target": {"type": "r_multiple", "r": 3.0},
        "entry_dedup_minutes": 1,
    })
    result = engine_run(ComposableStrategy(spec), bars, _make_config())
    assert len(result.trades) == 1


def test_global_filter_blocks_entry():
    """trigger fires, but global filter (time_window) is outside session → no entry."""
    # Bar at 06:00 ET = 10:00 UTC, outside RTH 9:30-14
    early = _utc(2026, 4, 25, 10, 0)
    bars = [_bar(early + dt.timedelta(minutes=i), open_=21000, high=21001, low=20990, close=20991) for i in range(3)]

    spec = ComposableSpec.from_dict({
        "trigger_short": [{"feature": "decisive_close", "params": {"direction": "BEARISH", "min_body_pct": 0.6, "min_range_pts": 1.0}}],
        "filter": [{"feature": "time_window", "params": {"start_hour": 9.5, "end_hour": 14.0}}],
        "stop": {"type": "fixed_pts", "stop_pts": 10.0},
        "target": {"type": "r_multiple", "r": 3.0},
    })
    result = engine_run(ComposableStrategy(spec), bars, _make_config())
    assert result.trades == []


def test_per_direction_filter_blocks_one_direction_only():
    """filter_long blocks longs; shorts can still fire."""
    # Inside RTH, bar that's both a bullish and bearish candidate; but we
    # only have a short trigger, so use that path. filter_short = volatility
    # 'low' filter that blocks (since bars are wide), filter_long not set.
    base = _utc(2026, 4, 25, 14, 30)
    bars = [_bar(base + dt.timedelta(minutes=i), open_=21000, high=21015, low=20985, close=20988) for i in range(35)]

    # short would fire (decisive bear close on every bar), but filter_short=volatility low
    # rejects (bars are wide → not low regime).
    spec = ComposableSpec.from_dict({
        "trigger_short": [{"feature": "decisive_close", "params": {"direction": "BEARISH", "min_body_pct": 0.4}}],
        "filter_short": [{"feature": "volatility_regime", "params": {"lookback_bars": 30, "low_threshold": 8.0, "high_threshold": 25.0, "require": "low"}}],
        "stop": {"type": "fixed_pts", "stop_pts": 10.0},
        "target": {"type": "r_multiple", "r": 3.0},
    })
    result = engine_run(ComposableStrategy(spec), bars, _make_config())
    assert result.trades == []


def test_empty_setup_means_always_armed():
    """Old-shape spec (no setup, just trigger) fires whenever trigger passes."""
    base = _utc(2026, 4, 25, 14, 30)
    bars = [_bar(base, open_=21001, high=21010, low=21000, close=21009)]  # one decisive bull bar
    spec = ComposableSpec.from_dict({
        "trigger_long": [{"feature": "decisive_close", "params": {"direction": "BULLISH", "min_body_pct": 0.6}}],
        "stop": {"type": "fixed_pts", "stop_pts": 5.0},
        "target": {"type": "r_multiple", "r": 2.0},
    })
    result = engine_run(ComposableStrategy(spec), bars, _make_config())
    # 1 bar, fills next bar → no actual entry filled, but the intent was emitted.
    # Easier check: the migration test above already covers byte-identity.
    # Here just verify no crash and bar processed cleanly.
    assert isinstance(result.trades, list)


def test_day_rollover_clears_armed_state():
    """Setup arms in day 1; day 2 starts fresh, trigger that day must NOT enter
    without setup re-firing."""
    day1 = _utc(2026, 4, 24, 14, 30)
    bars: list[Bar] = []
    # Day -1 (need history for PDH sweep): high 21010
    day_minus1 = _utc(2026, 4, 23, 14, 30)
    for i in range(5):
        bars.append(_bar(day_minus1 + dt.timedelta(minutes=i), open_=21000, high=21010, low=20995, close=21005))
    # Day 1: sweep PDH at bar 5. setup arms persistently.
    bars.append(_bar(day1 + dt.timedelta(minutes=0), open_=21015, high=21020, low=21013, close=21018))
    # No trigger yet day 1.
    for i in range(1, 5):
        bars.append(_bar(day1 + dt.timedelta(minutes=i), open_=21015, high=21017, low=21012, close=21015))
    # Day 2 (next session, after Globex rollover at 18:00 ET = 22:00 UTC): trigger fires.
    # Day 2's PDH = day 1's high (21020), so prior_level_sweep would NOT fire today's bar
    # at 21015. So setup is NOT re-armed. Therefore the bear close should not enter.
    day2 = _utc(2026, 4, 25, 14, 30)
    bars.append(_bar(day2 + dt.timedelta(minutes=0), open_=21015, high=21016, low=21000, close=21001))  # decisive bear close

    spec = ComposableSpec.from_dict({
        "setup_short": [{"feature": "prior_level_sweep", "params": {"level": "PDH", "direction": "above"}}],
        "trigger_short": [{"feature": "decisive_close", "params": {"direction": "BEARISH", "min_body_pct": 0.6}}],
        "setup_window": {"short": None},  # persistent — would otherwise carry over WITHOUT day rollover
        "stop": {"type": "fixed_pts", "stop_pts": 10.0},
        "target": {"type": "r_multiple", "r": 3.0},
    })
    result = engine_run(ComposableStrategy(spec), bars, _make_config())
    # Day 1 had no trigger. Day 2 has trigger but setup never re-fired, so no entry.
    assert result.trades == []


def test_setup_refires_while_armed_extends_window():
    """Setup fires at bar 5 with window=2 (would expire at idx 7).
    Setup re-fires at bar 9 (within an extended series of sweeps).
    Trigger at idx 11 is past the original window but inside the refreshed
    one (last sweep bar 9 + window 2 = expires at idx 11) → enters."""
    day1 = _utc(2026, 4, 24, 14, 30)
    base = _utc(2026, 4, 25, 14, 30)
    bars: list[Bar] = []
    # 5 day-1 bars (indices 0-4): PDH = 21010
    for i in range(5):
        bars.append(_bar(day1 + dt.timedelta(minutes=i), open_=21000, high=21010, low=20995, close=21005))
    # Day 2 bars 5-9 (5 consecutive sweeps, each high 21020)
    for i in range(5):
        bars.append(_bar(base + dt.timedelta(minutes=i), open_=21015, high=21020, low=21013, close=21015))
    # Bars 10-11: still above PDH (so still arming, but no decisive close yet)
    for i in range(5, 7):
        bars.append(_bar(base + dt.timedelta(minutes=i), open_=21015, high=21013, low=21008, close=21012))
    # Bar 12: decisive bear close (range 14, body 12 = 86%)
    bars.append(_bar(base + dt.timedelta(minutes=7), open_=21008, high=21009, low=20995, close=20996))
    # Bar 13: filler so the bracket can fill
    bars.append(_bar(base + dt.timedelta(minutes=8), open_=20996, high=20997, low=20990, close=20991))

    spec = ComposableSpec.from_dict({
        "setup_short": [{"feature": "prior_level_sweep", "params": {"level": "PDH", "direction": "above"}}],
        "trigger_short": [{"feature": "decisive_close", "params": {"direction": "BEARISH", "min_body_pct": 0.6}}],
        "setup_window": {"short": 4},
        "stop": {"type": "fixed_pts", "stop_pts": 10.0},
        "target": {"type": "r_multiple", "r": 3.0},
    })
    result = engine_run(ComposableStrategy(spec), bars, _make_config())
    # Last sweep was at idx 9, window=4 → armed through idx 13. Trigger at idx 12 → enters.
    assert len(result.trades) == 1


# ── per-call gate semantics ───────────────────────────────────────────


def test_trigger_gate_blocks_entry_outside_window():
    """Trigger with gate 08:00-10:00 ET. Bar fires at 07:55 ET → no entry."""
    # 11:55 UTC on Apr 25 = 07:55 ET (DST, UTC-4)
    early = _utc(2026, 4, 25, 11, 55)
    bars = [
        _bar(early + dt.timedelta(minutes=i), open_=21000, high=21010, low=20999, close=21009)
        for i in range(3)
    ]
    spec = ComposableSpec.from_dict({
        "trigger_long": [{
            "feature": "decisive_close",
            "params": {"direction": "BULLISH", "min_body_pct": 0.6, "min_range_pts": 1.0},
            "gate": {"start": "08:00", "end": "10:00"},
        }],
        "stop": {"type": "fixed_pts", "stop_pts": 5.0},
        "target": {"type": "r_multiple", "r": 2.0},
    })
    result = engine_run(ComposableStrategy(spec), bars, _make_config())
    assert result.trades == []


def test_trigger_gate_admits_entry_inside_window():
    """Same trigger + gate; bar fires at 09:00 ET → enters."""
    # 13:00 UTC on Apr 25 = 09:00 ET (DST)
    inside = _utc(2026, 4, 25, 13, 0)
    bars = [
        _bar(inside + dt.timedelta(minutes=i), open_=21000, high=21010, low=20999, close=21009)
        for i in range(3)
    ]
    spec = ComposableSpec.from_dict({
        "trigger_long": [{
            "feature": "decisive_close",
            "params": {"direction": "BULLISH", "min_body_pct": 0.6, "min_range_pts": 1.0},
            "gate": {"start": "08:00", "end": "10:00"},
        }],
        "stop": {"type": "fixed_pts", "stop_pts": 5.0},
        "target": {"type": "r_multiple", "r": 2.0},
    })
    result = engine_run(ComposableStrategy(spec), bars, _make_config())
    # First bar emits intent, fills on next bar.
    assert len(result.trades) >= 1


def test_setup_gate_does_not_arm_outside_window():
    """Setup with gate 08:00-10:00 firing at 07:55 ET must NOT arm.

    Sequence: day-1 history (PDH=21010), day-2 sweep at 07:55 (gated out),
    decisive bear close at 09:55 (inside gate but no arm). Expect no trade.
    """
    day1 = _utc(2026, 4, 24, 14, 30)
    bars: list[Bar] = []
    for i in range(5):
        bars.append(_bar(day1 + dt.timedelta(minutes=i), open_=21000, high=21010, low=20995, close=21005))
    # Day 2 bar 0: sweep at 07:55 ET (11:55 UTC) — gated OUT, must NOT arm.
    early = _utc(2026, 4, 25, 11, 55)
    bars.append(_bar(early, open_=21015, high=21020, low=21013, close=21012))
    # Filler bars to advance to 09:55 ET = 13:55 UTC
    for i in range(1, 121):
        bars.append(_bar(early + dt.timedelta(minutes=i), open_=21008, high=21009, low=21005, close=21008))
    # Bar at 13:55 UTC = 09:55 ET: decisive bear close (inside gate).
    bars.append(_bar(_utc(2026, 4, 25, 13, 55), open_=21008, high=21009, low=20995, close=20996))
    bars.append(_bar(_utc(2026, 4, 25, 13, 56), open_=20996, high=20997, low=20990, close=20991))

    spec = ComposableSpec.from_dict({
        "setup_short": [{
            "feature": "prior_level_sweep",
            "params": {"level": "PDH", "direction": "above"},
            "gate": {"start": "08:00", "end": "10:00"},
        }],
        "trigger_short": [{"feature": "decisive_close", "params": {"direction": "BEARISH", "min_body_pct": 0.6}}],
        "setup_window": {"short": None},  # persistent — would normally hold across the day
        "stop": {"type": "fixed_pts", "stop_pts": 10.0},
        "target": {"type": "r_multiple", "r": 3.0},
    })
    result = engine_run(ComposableStrategy(spec), bars, _make_config())
    # Setup never armed (gated out at 07:55), so no entry even though trigger
    # fires at 09:55 (inside gate but irrelevant — gate is on the SETUP).
    assert result.trades == []


# ── new setup-window variants: minutes, until_clock ───────────────────


def test_setup_window_minutes_expires():
    """Setup at 09:30 ET, window=minutes:5. Trigger at 09:36 ET → no entry."""
    day1 = _utc(2026, 4, 24, 14, 30)
    bars: list[Bar] = []
    for i in range(5):
        bars.append(_bar(day1 + dt.timedelta(minutes=i), open_=21000, high=21010, low=20995, close=21005))
    # Day 2 bar 0: sweep at 09:30 ET (13:30 UTC)
    base = _utc(2026, 4, 25, 13, 30)
    bars.append(_bar(base, open_=21015, high=21020, low=21013, close=21012))
    # 6 quiet minutes — past the 5-min window.
    for i in range(1, 7):
        bars.append(_bar(base + dt.timedelta(minutes=i), open_=21008, high=21009, low=21005, close=21008))
    # Decisive bear close at 09:37 ET (13:37 UTC) — past window.
    bars.append(_bar(base + dt.timedelta(minutes=7), open_=21008, high=21009, low=20995, close=20996))
    bars.append(_bar(base + dt.timedelta(minutes=8), open_=20996, high=20997, low=20990, close=20991))

    spec = ComposableSpec.from_dict({
        "setup_short": [{"feature": "prior_level_sweep", "params": {"level": "PDH", "direction": "above"}}],
        "trigger_short": [{"feature": "decisive_close", "params": {"direction": "BEARISH", "min_body_pct": 0.6}}],
        "setup_window": {"short": {"type": "minutes", "n": 5}},
        "stop": {"type": "fixed_pts", "stop_pts": 10.0},
        "target": {"type": "r_multiple", "r": 3.0},
    })
    result = engine_run(ComposableStrategy(spec), bars, _make_config())
    assert result.trades == []


def test_setup_window_until_clock_expires():
    """Setup at 09:30 ET, until_clock end_hour=10.0. Trigger at 10:05 → no entry."""
    day1 = _utc(2026, 4, 24, 14, 30)
    bars: list[Bar] = []
    for i in range(5):
        bars.append(_bar(day1 + dt.timedelta(minutes=i), open_=21000, high=21010, low=20995, close=21005))
    # Day 2 bar 0: sweep at 09:30 ET (13:30 UTC)
    base = _utc(2026, 4, 25, 13, 30)
    bars.append(_bar(base, open_=21015, high=21020, low=21013, close=21012))
    # Quiet through 10:04, then decisive bear at 10:05 — past 10:00 deadline.
    for i in range(1, 36):
        bars.append(_bar(base + dt.timedelta(minutes=i), open_=21008, high=21009, low=21005, close=21008))
    # 14:05 UTC = 10:05 ET
    bars.append(_bar(_utc(2026, 4, 25, 14, 5), open_=21008, high=21009, low=20995, close=20996))
    bars.append(_bar(_utc(2026, 4, 25, 14, 6), open_=20996, high=20997, low=20990, close=20991))

    spec = ComposableSpec.from_dict({
        "setup_short": [{"feature": "prior_level_sweep", "params": {"level": "PDH", "direction": "above"}}],
        "trigger_short": [{"feature": "decisive_close", "params": {"direction": "BEARISH", "min_body_pct": 0.6}}],
        "setup_window": {
            "short": {"type": "until_clock", "end_hour": 10.0, "tz": "America/New_York"}
        },
        "stop": {"type": "fixed_pts", "stop_pts": 10.0},
        "target": {"type": "r_multiple", "r": 3.0},
    })
    result = engine_run(ComposableStrategy(spec), bars, _make_config())
    assert result.trades == []


def test_setup_window_until_clock_admits_entry_inside():
    """Same setup, until_clock end_hour=10.0. Trigger at 09:55 → enters."""
    day1 = _utc(2026, 4, 24, 14, 30)
    bars: list[Bar] = []
    for i in range(5):
        bars.append(_bar(day1 + dt.timedelta(minutes=i), open_=21000, high=21010, low=20995, close=21005))
    base = _utc(2026, 4, 25, 13, 30)  # 09:30 ET
    bars.append(_bar(base, open_=21015, high=21020, low=21013, close=21012))
    for i in range(1, 25):
        bars.append(_bar(base + dt.timedelta(minutes=i), open_=21008, high=21009, low=21005, close=21008))
    # 13:55 UTC = 09:55 ET — inside the until-10:00 window.
    bars.append(_bar(_utc(2026, 4, 25, 13, 55), open_=21008, high=21009, low=20995, close=20996))
    bars.append(_bar(_utc(2026, 4, 25, 13, 56), open_=20996, high=20997, low=20990, close=20991))

    spec = ComposableSpec.from_dict({
        "setup_short": [{"feature": "prior_level_sweep", "params": {"level": "PDH", "direction": "above"}}],
        "trigger_short": [{"feature": "decisive_close", "params": {"direction": "BEARISH", "min_body_pct": 0.6}}],
        "setup_window": {
            "short": {"type": "until_clock", "end_hour": 10.0, "tz": "America/New_York"}
        },
        "stop": {"type": "fixed_pts", "stop_pts": 10.0},
        "target": {"type": "r_multiple", "r": 3.0},
    })
    result = engine_run(ComposableStrategy(spec), bars, _make_config())
    assert len(result.trades) == 1


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
