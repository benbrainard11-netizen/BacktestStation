"""Unit tests for FVG detection + check_touch.

Phase 2 of the Fractal AMD port. Covers:
- resample_bars: 1m -> N-minute aggregation correctness
- detect_fvgs: 3-candle gap detection + fill / expiry tracking
- find_nearest_unfilled_fvg: distance-by-mid selection
- check_touch: bar [low,high] intersects FVG -> WATCHING -> TOUCHED
"""

from __future__ import annotations

import datetime as dt

import pytest

from app.backtest.strategy import Bar
from app.strategies.fractal_amd.signals import (
    FVG,
    Setup,
    check_touch,
    detect_fvgs,
    find_nearest_unfilled_fvg,
    resample_bars,
)


def _bar(*, ts, o, h, l, c, symbol="NQ.c.0") -> Bar:
    return Bar(
        ts_event=ts,
        symbol=symbol,
        open=o,
        high=h,
        low=l,
        close=c,
        volume=10,
        trade_count=1,
        vwap=(h + l) / 2,
    )


# --- resample_bars -----------------------------------------------------


def test_resample_bars_5min_aggregates_correct_ohlc():
    start = dt.datetime(2026, 4, 24, 14, 0, tzinfo=dt.timezone.utc)
    bars = [
        _bar(ts=start + dt.timedelta(minutes=i), o=100 + i, h=101 + i, l=99 + i, c=100 + i)
        for i in range(10)
    ]
    out = resample_bars(bars, 5)
    assert len(out) == 2
    # First 5 bars (i=0..4): open=100, high=105, low=99, close=104
    assert out[0].open == 100
    assert out[0].high == 105
    assert out[0].low == 99
    assert out[0].close == 104
    assert out[0].timeframe == "5m"
    # Second 5 bars (i=5..9): open=105, high=110, low=104, close=109
    assert out[1].open == 105
    assert out[1].high == 110
    assert out[1].low == 104


def test_resample_bars_empty_input():
    assert resample_bars([], 5) == []


def test_resample_bars_15min_buckets_correctly():
    start = dt.datetime(2026, 4, 24, 14, 0, tzinfo=dt.timezone.utc)
    bars = [
        _bar(ts=start + dt.timedelta(minutes=i), o=100, h=101, l=99, c=100)
        for i in range(30)
    ]
    out = resample_bars(bars, 15)
    assert len(out) == 2
    assert (out[0].end - out[0].start) == dt.timedelta(minutes=15)


# --- detect_fvgs -------------------------------------------------------


def test_fvg_bullish_three_candle_gap():
    """c1.high=100, c3.low=105 => bullish FVG zone (100, 105) of width 5."""
    start = dt.datetime(2026, 4, 24, 14, 0, tzinfo=dt.timezone.utc)
    candles_1m = [
        # c1: high=100, low=95
        _bar(ts=start, o=98, h=100, l=95, c=99),
        # c2: aggressive up displacement
        _bar(ts=start + dt.timedelta(minutes=1), o=99, h=110, l=99, c=109),
        # c3: high=112, low=105
        _bar(ts=start + dt.timedelta(minutes=2), o=109, h=112, l=105, c=110),
    ]
    # Treat 1m as the "candles" input directly via resample_bars(1).
    # Or we can just hand-build HTFCandles -- simpler:
    htf = resample_bars(candles_1m, 1)
    fvgs = detect_fvgs(htf, "BULLISH", min_gap_pct=0.0)
    assert len(fvgs) == 1
    assert fvgs[0].direction == "BULLISH"
    assert fvgs[0].low == 100
    assert fvgs[0].high == 105
    assert fvgs[0].mid == 102.5
    assert fvgs[0].filled is False


def test_fvg_bearish_three_candle_gap():
    start = dt.datetime(2026, 4, 24, 14, 0, tzinfo=dt.timezone.utc)
    candles_1m = [
        _bar(ts=start, o=110, h=112, l=105, c=109),  # c1: low=105
        _bar(ts=start + dt.timedelta(minutes=1), o=109, h=109, l=95, c=96),  # c2 displaces down
        _bar(ts=start + dt.timedelta(minutes=2), o=96, h=100, l=93, c=97),  # c3: high=100
    ]
    htf = resample_bars(candles_1m, 1)
    fvgs = detect_fvgs(htf, "BEARISH", min_gap_pct=0.0)
    assert len(fvgs) == 1
    assert fvgs[0].direction == "BEARISH"
    assert fvgs[0].low == 100  # c3 high
    assert fvgs[0].high == 105  # c1 low


def test_fvg_filled_when_price_walks_through():
    start = dt.datetime(2026, 4, 24, 14, 0, tzinfo=dt.timezone.utc)
    candles_1m = [
        _bar(ts=start, o=98, h=100, l=95, c=99),
        _bar(ts=start + dt.timedelta(minutes=1), o=99, h=110, l=99, c=109),
        _bar(ts=start + dt.timedelta(minutes=2), o=109, h=112, l=105, c=110),
        # walk-through: low <= 100 fills the bullish gap
        _bar(ts=start + dt.timedelta(minutes=3), o=110, h=110, l=99, c=100),
    ]
    htf = resample_bars(candles_1m, 1)
    fvgs = detect_fvgs(htf, "BULLISH", min_gap_pct=0.0)
    assert len(fvgs) == 1
    assert fvgs[0].filled is True
    assert fvgs[0].fill_bar_idx == 3


def test_fvg_no_gap_no_signal():
    start = dt.datetime(2026, 4, 24, 14, 0, tzinfo=dt.timezone.utc)
    candles_1m = [
        _bar(ts=start + dt.timedelta(minutes=i), o=100, h=101, l=99, c=100)
        for i in range(5)
    ]
    htf = resample_bars(candles_1m, 1)
    assert detect_fvgs(htf, "BULLISH", min_gap_pct=0.0) == []
    assert detect_fvgs(htf, "BEARISH", min_gap_pct=0.0) == []


def test_fvg_min_gap_pct_filters_noise():
    """A gap of 0.1 vs avg range of 1.0 is < 30% (default min_gap_pct) -> filtered."""
    start = dt.datetime(2026, 4, 24, 14, 0, tzinfo=dt.timezone.utc)
    candles_1m = [
        _bar(ts=start + dt.timedelta(minutes=i), o=100, h=101, l=99, c=100)
        for i in range(20)  # build avg_range baseline of ~2
    ]
    # Tiny gap on bars 20-22
    candles_1m.append(_bar(ts=start + dt.timedelta(minutes=20), o=100, h=101, l=99, c=100))
    candles_1m.append(_bar(ts=start + dt.timedelta(minutes=21), o=100, h=101.05, l=99, c=101))
    candles_1m.append(_bar(ts=start + dt.timedelta(minutes=22), o=101, h=102, l=101.05, c=101.5))
    htf = resample_bars(candles_1m, 1)
    # Tiny 0.05 gap < 30% of avg range (2.0) => filtered.
    fvgs = detect_fvgs(htf, "BULLISH", min_gap_pct=0.3)
    assert fvgs == []


# --- find_nearest_unfilled_fvg -----------------------------------------


def test_nearest_fvg_picks_closest_by_mid():
    fvgs = [
        FVG(direction="BULLISH", high=110, low=100, creation_time=dt.datetime.now(dt.timezone.utc), creation_bar_idx=0),
        FVG(direction="BULLISH", high=125, low=120, creation_time=dt.datetime.now(dt.timezone.utc), creation_bar_idx=1),
    ]
    nearest = find_nearest_unfilled_fvg(fvgs, current_price=124, current_bar_idx=10)
    assert nearest is not None
    assert nearest.low == 120


def test_nearest_fvg_skips_filled():
    fvgs = [
        FVG(direction="BULLISH", high=110, low=100, creation_time=dt.datetime.now(dt.timezone.utc), creation_bar_idx=0, filled=True, fill_bar_idx=5),
        FVG(direction="BULLISH", high=130, low=120, creation_time=dt.datetime.now(dt.timezone.utc), creation_bar_idx=1),
    ]
    nearest = find_nearest_unfilled_fvg(fvgs, current_price=105, current_bar_idx=10)
    assert nearest is not None
    assert nearest.low == 120  # the filled one was closer but skipped


def test_nearest_fvg_skips_expired():
    fvgs = [
        FVG(direction="BULLISH", high=110, low=100, creation_time=dt.datetime.now(dt.timezone.utc), creation_bar_idx=0),
    ]
    # Current bar 200 is beyond 60-bar expiry from creation_bar_idx=0
    assert find_nearest_unfilled_fvg(fvgs, current_price=105, current_bar_idx=200) is None


# --- check_touch -------------------------------------------------------


def _setup(direction, fvg_low, fvg_high, status="WATCHING"):
    return Setup(
        direction=direction,
        htf_tf="1H",
        htf_candle_start=dt.datetime(2026, 4, 24, 14, tzinfo=dt.timezone.utc),
        htf_candle_end=dt.datetime(2026, 4, 24, 15, tzinfo=dt.timezone.utc),
        ltf_tf="5m",
        ltf_candle_end=dt.datetime(2026, 4, 24, 15, tzinfo=dt.timezone.utc),
        fvg_low=fvg_low,
        fvg_high=fvg_high,
        fvg_mid=(fvg_low + fvg_high) / 2,
        status=status,
    )


def test_check_touch_marks_setup_when_bar_intersects_fvg():
    setups = [_setup("BEARISH", 105, 110)]
    # Bar high=108 within zone => touched
    bar = _bar(ts=dt.datetime(2026, 4, 24, 15, 5, tzinfo=dt.timezone.utc), o=104, h=108, l=103, c=107)
    touched = check_touch(setups, bar)
    assert len(touched) == 1
    assert setups[0].status == "TOUCHED"
    assert setups[0].touch_bar_time == bar.ts_event


def test_check_touch_no_intersection_leaves_setup_watching():
    setups = [_setup("BEARISH", 105, 110)]
    bar = _bar(ts=dt.datetime(2026, 4, 24, 15, 5, tzinfo=dt.timezone.utc), o=99, h=100, l=98, c=99)
    touched = check_touch(setups, bar)
    assert touched == []
    assert setups[0].status == "WATCHING"


def test_check_touch_picks_nearest_when_multiple_setups_match():
    """The 'nearest' selection per direction was the load-bearing fix
    in the trusted bot: among all WATCHING-direction setups, only the
    one with closest fvg_mid to current bar close is eligible."""
    setups = [
        _setup("BEARISH", 100, 105),  # mid=102.5
        _setup("BEARISH", 108, 112),  # mid=110 -- this is closest to bar.close=109
    ]
    bar = _bar(ts=dt.datetime(2026, 4, 24, 15, 5, tzinfo=dt.timezone.utc), o=109, h=111, l=108, c=109)
    touched = check_touch(setups, bar)
    assert len(touched) == 1
    # Only the nearest got touched; the other stays WATCHING.
    assert setups[0].status == "WATCHING"
    assert setups[1].status == "TOUCHED"


def test_check_touch_independent_per_direction():
    setups = [
        _setup("BEARISH", 105, 110),
        _setup("BULLISH", 90, 95),
    ]
    bar = _bar(ts=dt.datetime(2026, 4, 24, 15, 5, tzinfo=dt.timezone.utc), o=92, h=108, l=92, c=107)
    # bar high=108 touches BEARISH zone, bar low=92 touches BULLISH zone
    touched = check_touch(setups, bar)
    assert len(touched) == 2
    assert all(s.status == "TOUCHED" for s in setups)


def test_check_touch_skips_already_touched_setup():
    setups = [_setup("BEARISH", 105, 110, status="TOUCHED")]
    bar = _bar(ts=dt.datetime(2026, 4, 24, 15, 5, tzinfo=dt.timezone.utc), o=104, h=108, l=103, c=107)
    touched = check_touch(setups, bar)
    assert touched == []  # nothing newly touched
    # Status stays TOUCHED (not flipped back).
    assert setups[0].status == "TOUCHED"
