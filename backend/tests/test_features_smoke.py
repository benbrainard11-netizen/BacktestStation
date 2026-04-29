"""Smoke tests for the feature library primitives.

One synthetic-bar test per feature, focused on:
  - happy path passes
  - non-matching path fails cleanly (no exceptions)
  - metadata contract for downstream chaining
"""

from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

from app.backtest.strategy import Bar
from app.features import FEATURES, FeatureResult
from app.features.co_score import co_score
from app.features.decisive_close import decisive_close
from app.features.fvg_touch_recent import fvg_touch_recent
from app.features.prior_level_sweep import prior_level_sweep
from app.features.smt_at_level import smt_at_level
from app.features.swing_sweep import swing_sweep
from app.features.time_window import time_window
from app.features.volatility_regime import volatility_regime


ET = ZoneInfo("America/New_York")
UTC = dt.timezone.utc


def _bar(
    ts: dt.datetime,
    open_: float = 21000.0,
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


# ── time_window ───────────────────────────────────────────────────────


def test_time_window_inside_passes():
    bars = [_bar(_utc(2026, 4, 24, 13, 30))]  # 9:30 ET
    r = time_window(
        bars=bars, aux={}, current_idx=0,
        start_hour=9.5, end_hour=14.0, tz="America/New_York",
    )
    assert r.passed, r.metadata


def test_time_window_outside_fails():
    bars = [_bar(_utc(2026, 4, 24, 9, 0))]  # 5:00 ET
    r = time_window(
        bars=bars, aux={}, current_idx=0,
        start_hour=9.5, end_hour=14.0, tz="America/New_York",
    )
    assert not r.passed


def test_time_window_end_is_exclusive():
    bars = [_bar(_utc(2026, 4, 24, 18, 0))]  # 14:00 ET — boundary
    r = time_window(
        bars=bars, aux={}, current_idx=0,
        start_hour=9.5, end_hour=14.0, tz="America/New_York",
    )
    assert not r.passed


# ── co_score ──────────────────────────────────────────────────────────


def test_co_score_returns_passed_or_not_without_crashing():
    """CO needs ≥18 bars (lookback+3). Fewer = passes False, no error."""
    bars = [_bar(_utc(2026, 4, 24, 13, 30))]
    r = co_score(
        bars=bars, aux={}, current_idx=0,
        min_score=3, direction="BULLISH", lookback=15, atr=40.0,
    )
    assert isinstance(r, FeatureResult)
    assert r.passed is False  # not enough history


def test_co_score_full_history_returns_metadata():
    """Synthetic ~20-bar history; just verify metadata shape."""
    base = _utc(2026, 4, 24, 13, 30)
    bars = [_bar(base + dt.timedelta(minutes=i)) for i in range(25)]
    r = co_score(
        bars=bars, aux={}, current_idx=24,
        min_score=0, direction="BULLISH", lookback=15, atr=40.0,
    )
    # min_score=0 forces passed=True so we can inspect metadata
    assert r.passed
    assert "co_score" in r.metadata
    assert "sub_features" in r.metadata


# ── prior_level_sweep ─────────────────────────────────────────────────


def test_prior_level_sweep_pdh_pierced():
    """Day 1 high = 21010; day 2 bar prints high = 21020 → swept."""
    day1_open = _utc(2026, 4, 24, 14, 30)  # 10:30 ET, day-1 trading
    day2_open = _utc(2026, 4, 25, 14, 30)  # 10:30 ET, day-2 trading
    bars = [
        _bar(day1_open, open_=21000, high=21010, low=20995, close=21005),
        _bar(day2_open, open_=21015, high=21020, low=21010, close=21018),
    ]
    r = prior_level_sweep(
        bars=bars, aux={}, current_idx=1,
        level="PDH", direction="above", tz="America/New_York",
    )
    assert r.passed
    assert r.metadata["swept_level"] == 21010
    assert r.direction == "BEARISH"


def test_prior_level_sweep_not_pierced():
    day1_open = _utc(2026, 4, 24, 14, 30)
    day2_open = _utc(2026, 4, 25, 14, 30)
    bars = [
        _bar(day1_open, open_=21000, high=21010, low=20995, close=21005),
        _bar(day2_open, open_=21000, high=21008, low=20990, close=21000),
    ]
    r = prior_level_sweep(
        bars=bars, aux={}, current_idx=1,
        level="PDH", direction="above",
    )
    assert not r.passed


# ── smt_at_level ──────────────────────────────────────────────────────


def test_smt_at_level_synthetic_divergence():
    """NQ sweeps high in 2nd half; ES holds → SMT BEARISH."""
    base = _utc(2026, 4, 24, 13, 30)
    nq = []
    es = []
    # First half: range 21000-21010 for both
    for i in range(15):
        ts = base + dt.timedelta(minutes=i)
        nq.append(_bar(ts, open_=21005, high=21010, low=21000, close=21005))
        es.append(_bar(ts, open_=5000, high=5010, low=5000, close=5005, symbol="ES.c.0"))
    # Second half: NQ pushes to 21020, ES stays under 5010
    for i in range(15, 30):
        ts = base + dt.timedelta(minutes=i)
        nq.append(_bar(ts, open_=21015, high=21020, low=21010, close=21018))
        es.append(_bar(ts, open_=5005, high=5008, low=5000, close=5004, symbol="ES.c.0"))
    r = smt_at_level(
        bars=nq, aux={"ES.c.0": es}, current_idx=29,
        direction="BEARISH", side="high", window_bars=30,
    )
    assert r.passed, r.metadata
    assert r.direction == "BEARISH"
    assert "ES.c.0" in r.metadata["holders"]


def test_smt_at_level_no_divergence():
    """Both NQ and ES sweep their highs → no SMT, fails."""
    base = _utc(2026, 4, 24, 13, 30)
    nq, es = [], []
    for i in range(15):
        ts = base + dt.timedelta(minutes=i)
        nq.append(_bar(ts, open_=21005, high=21010, low=21000, close=21005))
        es.append(_bar(ts, open_=5005, high=5010, low=5000, close=5005, symbol="ES.c.0"))
    for i in range(15, 30):
        ts = base + dt.timedelta(minutes=i)
        nq.append(_bar(ts, open_=21015, high=21020, low=21010, close=21018))
        es.append(_bar(ts, open_=5012, high=5020, low=5008, close=5018, symbol="ES.c.0"))
    r = smt_at_level(
        bars=nq, aux={"ES.c.0": es}, current_idx=29,
        direction="BEARISH", side="high", window_bars=30,
    )
    assert not r.passed


# ── fvg_touch_recent ──────────────────────────────────────────────────


def test_fvg_touch_recent_no_history_fails_cleanly():
    bars = [_bar(_utc(2026, 4, 24, 13, 30))]
    r = fvg_touch_recent(
        bars=bars, aux={}, current_idx=0,
        direction="BULLISH",
    )
    assert isinstance(r, FeatureResult)
    assert r.passed is False


# ── swing_sweep ───────────────────────────────────────────────────────


def test_swing_sweep_pierces_recent_high():
    """Build bars that have a clear swing high at index 5, then a
    bar at index 12 that pierces it."""
    base = _utc(2026, 4, 24, 13, 30)
    bars: list[Bar] = []
    # bars 0-4: low values
    for i in range(5):
        bars.append(_bar(base + dt.timedelta(minutes=i), open_=21000, high=21005, low=20995, close=21002))
    # bar 5: pivot high at 21030
    bars.append(_bar(base + dt.timedelta(minutes=5), open_=21010, high=21030, low=21008, close=21025))
    # bars 6-10: pull back below pivot
    for i in range(6, 11):
        bars.append(_bar(base + dt.timedelta(minutes=i), open_=21015, high=21020, low=21010, close=21015))
    # bar 11: still below
    bars.append(_bar(base + dt.timedelta(minutes=11), open_=21015, high=21025, low=21010, close=21020))
    # bar 12: pierces 21030
    bars.append(_bar(base + dt.timedelta(minutes=12), open_=21025, high=21035, low=21022, close=21032))

    r = swing_sweep(
        bars=bars, aux={}, current_idx=12,
        side="high", pivot_strength=2, lookback_bars=20,
    )
    assert r.passed, r.metadata
    assert r.direction == "BEARISH"
    assert r.metadata["swept_level"] == 21030


def test_swing_sweep_no_pivot_in_window():
    """All bars same price → no pivot → fails cleanly."""
    base = _utc(2026, 4, 24, 13, 30)
    bars = [_bar(base + dt.timedelta(minutes=i), open_=21000, high=21005, low=20995) for i in range(20)]
    r = swing_sweep(
        bars=bars, aux={}, current_idx=15,
        side="high", pivot_strength=3, lookback_bars=20,
    )
    assert not r.passed


# ── volatility_regime ─────────────────────────────────────────────────


def test_volatility_regime_classifies_low():
    """Tight bars → low regime."""
    base = _utc(2026, 4, 24, 13, 30)
    bars = [_bar(base + dt.timedelta(minutes=i), open_=21000, high=21002, low=20999) for i in range(35)]
    r = volatility_regime(
        bars=bars, aux={}, current_idx=34,
        lookback_bars=30, low_threshold=8.0, high_threshold=25.0,
        require="low",
    )
    assert r.passed
    assert r.metadata["regime"] == "low"


def test_volatility_regime_not_low_filter():
    """Wider bars → not_low passes; require=low fails."""
    base = _utc(2026, 4, 24, 13, 30)
    bars = [_bar(base + dt.timedelta(minutes=i), open_=21000, high=21015, low=20995) for i in range(35)]
    r_not_low = volatility_regime(
        bars=bars, aux={}, current_idx=34,
        lookback_bars=30, low_threshold=8.0, high_threshold=25.0,
        require="not_low",
    )
    assert r_not_low.passed
    r_low = volatility_regime(
        bars=bars, aux={}, current_idx=34,
        lookback_bars=30, low_threshold=8.0, high_threshold=25.0,
        require="low",
    )
    assert not r_low.passed


# ── decisive_close ────────────────────────────────────────────────────


def test_decisive_close_bullish_momentum_passes():
    """Body 80% of range, close > open → BULLISH passes."""
    base = _utc(2026, 4, 24, 13, 30)
    # range = 10 (from 21000 to 21010), body = close-open = 8 → 80%
    bars = [_bar(base, open_=21001, high=21010, low=21000, close=21009)]
    r = decisive_close(
        bars=bars, aux={}, current_idx=0,
        direction="BULLISH", min_body_pct=0.6, min_range_pts=1.0,
    )
    assert r.passed
    assert r.metadata["body_pct"] >= 0.6


def test_decisive_close_indecision_fails():
    """Tiny body / wick-fade bar → fails."""
    base = _utc(2026, 4, 24, 13, 30)
    # range 10, body 1 → 10%
    bars = [_bar(base, open_=21001, high=21010, low=21000, close=21002)]
    r = decisive_close(
        bars=bars, aux={}, current_idx=0,
        direction="BULLISH", min_body_pct=0.6,
    )
    assert not r.passed


def test_decisive_close_wrong_direction_fails():
    """Bullish bar fails BEARISH check."""
    base = _utc(2026, 4, 24, 13, 30)
    bars = [_bar(base, open_=21001, high=21010, low=21000, close=21009)]
    r = decisive_close(
        bars=bars, aux={}, current_idx=0,
        direction="BEARISH", min_body_pct=0.6,
    )
    assert not r.passed


# ── registry ──────────────────────────────────────────────────────────


def test_all_features_registered():
    expected = {"time_window", "co_score", "prior_level_sweep",
                "smt_at_level", "fvg_touch_recent",
                "swing_sweep", "volatility_regime", "decisive_close"}
    assert expected.issubset(set(FEATURES.keys()))
    for name in expected:
        spec = FEATURES[name]
        assert callable(spec.fn)
        assert spec.label
        assert spec.description
        assert isinstance(spec.param_schema, dict)
