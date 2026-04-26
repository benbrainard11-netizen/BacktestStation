"""Isolated unit tests for Fractal AMD signal helpers.

`test_fractal_amd_signals.py` already covers `candle_bounds`,
`get_ohlc`, `detect_smt_at_level`, `detect_rejection`, and
`check_candle_pair`. This file fills the gaps the strategy port debug
needs:

- `check_touch` (Setup WATCHING -> TOUCHED transition)
- `resample_bars` (5m / 15m aggregation that feeds FVG detection)
- `detect_fvgs` (Fair Value Gap zone construction)
- `find_nearest_unfilled_fvg` (FVG -> Setup selection)
- `is_in_entry_window` (entry window boundary logic)

Diagnostic-tooling rationale: if any helper here fails, the strategy
port's "188 setups but 0 trades" bug has a primitive-level cause we
can isolate. If they all pass, the bug is in the orchestration
layer (strategy.py), not the math.
"""

from __future__ import annotations

import datetime as dt

from app.backtest.strategy import Bar
from app.strategies.fractal_amd.signals import (
    ET,
    FVG,
    Setup,
    check_touch,
    detect_fvgs,
    find_nearest_unfilled_fvg,
    is_in_entry_window,
    resample_bars,
)


# --- Tiny constructors ---------------------------------------------------


def _bar(
    *,
    symbol: str = "NQ.c.0",
    ts: dt.datetime,
    o: float,
    h: float,
    low: float,
    c: float,
) -> Bar:
    return Bar(
        ts_event=ts,
        symbol=symbol,
        open=o,
        high=h,
        low=low,
        close=c,
        volume=100,
        trade_count=10,
        vwap=(h + low) / 2,
    )


def _setup(
    *,
    direction: str,
    fvg_low: float,
    fvg_high: float,
    status: str = "WATCHING",
) -> Setup:
    return Setup(
        direction=direction,  # type: ignore[arg-type]
        htf_tf="1H",
        htf_candle_start=dt.datetime(2026, 4, 24, 13, 0, tzinfo=dt.timezone.utc),
        htf_candle_end=dt.datetime(2026, 4, 24, 14, 0, tzinfo=dt.timezone.utc),
        ltf_tf="5m",
        ltf_candle_end=dt.datetime(2026, 4, 24, 14, 5, tzinfo=dt.timezone.utc),
        fvg_high=fvg_high,
        fvg_low=fvg_low,
        fvg_mid=(fvg_high + fvg_low) / 2,
        status=status,  # type: ignore[arg-type]
    )


# --- check_touch ---------------------------------------------------------


def test_check_touch_marks_intersecting_setup_touched() -> None:
    """A bar whose [low, high] overlaps the FVG zone -> nearest WATCHING
    setup of that direction flips to TOUCHED."""
    setups = [_setup(direction="BULLISH", fvg_low=21000.0, fvg_high=21010.0)]
    bar = _bar(
        ts=dt.datetime(2026, 4, 24, 14, 30, tzinfo=dt.timezone.utc),
        o=21015.0,
        h=21015.5,
        low=21008.0,
        c=21012.0,
    )

    touched = check_touch(setups, bar)

    assert len(touched) == 1
    assert setups[0].status == "TOUCHED"
    assert setups[0].touch_bar_time == bar.ts_event


def test_check_touch_picks_nearest_zone_per_direction() -> None:
    """When multiple WATCHING setups exist for the same direction, the
    one whose mid is nearest the bar.close is the one that touches."""
    far = _setup(direction="BULLISH", fvg_low=20900.0, fvg_high=20910.0)
    near = _setup(direction="BULLISH", fvg_low=21008.0, fvg_high=21015.0)
    setups = [far, near]
    bar = _bar(
        ts=dt.datetime(2026, 4, 24, 14, 30, tzinfo=dt.timezone.utc),
        o=21013.0,
        h=21015.0,
        low=21010.0,
        c=21012.0,
    )

    touched = check_touch(setups, bar)

    assert touched == [near]
    assert near.status == "TOUCHED"
    assert far.status == "WATCHING"


def test_check_touch_skips_already_touched_or_filled() -> None:
    """A FILLED setup never re-triggers, even when the bar would touch it."""
    filled = _setup(
        direction="BULLISH", fvg_low=21000.0, fvg_high=21010.0, status="FILLED"
    )
    bar = _bar(
        ts=dt.datetime(2026, 4, 24, 14, 30, tzinfo=dt.timezone.utc),
        o=21005.0,
        h=21008.0,
        low=21002.0,
        c=21006.0,
    )
    touched = check_touch([filled], bar)
    assert touched == []
    assert filled.status == "FILLED"


def test_check_touch_no_overlap_no_touch() -> None:
    setups = [_setup(direction="BULLISH", fvg_low=21000.0, fvg_high=21010.0)]
    bar = _bar(
        ts=dt.datetime(2026, 4, 24, 14, 30, tzinfo=dt.timezone.utc),
        o=21100.0,
        h=21105.0,
        low=21095.0,
        c=21102.0,
    )
    touched = check_touch(setups, bar)
    assert touched == []
    assert setups[0].status == "WATCHING"


def test_check_touch_handles_per_direction_independently() -> None:
    """A bar can touch one BULLISH setup and one BEARISH setup in the
    same call (one per direction is the rule)."""
    bull = _setup(direction="BULLISH", fvg_low=21000.0, fvg_high=21010.0)
    bear = _setup(direction="BEARISH", fvg_low=21020.0, fvg_high=21030.0)
    setups = [bull, bear]
    # Bar spans both zones.
    bar = _bar(
        ts=dt.datetime(2026, 4, 24, 14, 30, tzinfo=dt.timezone.utc),
        o=21015.0,
        h=21025.0,
        low=21005.0,
        c=21020.0,
    )

    touched = check_touch(setups, bar)
    statuses = sorted(s.status for s in touched)
    assert statuses == ["TOUCHED", "TOUCHED"]


# --- resample_bars -------------------------------------------------------


def test_resample_bars_buckets_by_floor_minute() -> None:
    """Five 1m bars resampled to 5m -> one HTFCandle aligned at minute=0
    of the natural 5m boundary."""
    start = dt.datetime(2026, 4, 24, 14, 0, tzinfo=dt.timezone.utc)
    bars = [
        _bar(ts=start + dt.timedelta(minutes=i), o=100 + i, h=100 + i + 0.5,
             low=100 + i - 0.5, c=100 + i + 0.25)
        for i in range(5)
    ]
    out = resample_bars(bars, tf_minutes=5)
    assert len(out) == 1
    cand = out[0]
    assert cand.start == start
    assert cand.end == start + dt.timedelta(minutes=5)
    assert cand.open == 100
    assert cand.close == 104.25
    assert cand.high == 104.5
    assert cand.low == 99.5


def test_resample_bars_handles_partial_buckets() -> None:
    """Seven 1m bars at 5m bucket size -> two candles (one full, one
    partial). Output ordered by start ascending."""
    start = dt.datetime(2026, 4, 24, 14, 0, tzinfo=dt.timezone.utc)
    bars = [
        _bar(ts=start + dt.timedelta(minutes=i), o=100, h=100.5, low=99.5, c=100)
        for i in range(7)
    ]
    out = resample_bars(bars, tf_minutes=5)
    assert len(out) == 2
    assert out[0].start == start
    assert out[1].start == start + dt.timedelta(minutes=5)


def test_resample_bars_empty_returns_empty() -> None:
    assert resample_bars([], tf_minutes=5) == []


# --- detect_fvgs ---------------------------------------------------------


def test_detect_fvgs_bullish_gap_three_candle_displacement() -> None:
    """Bullish FVG = candle1.high < candle3.low (price gapped UP).

    Build three flat candles plus a strong displacement candle 2,
    such that c1.high (101) < c3.low (103) -> bullish FVG zone
    (101, 103).
    """
    base = dt.datetime(2026, 4, 24, 14, 0, tzinfo=dt.timezone.utc)
    delta = dt.timedelta(minutes=5)

    from app.strategies.fractal_amd.signals import HTFCandle

    candles = [
        HTFCandle(timeframe="5m", start=base, end=base + delta,
                  open=100, high=101, low=99, close=100.5),
        # Displacement candle: huge bullish bar
        HTFCandle(timeframe="5m", start=base + delta, end=base + 2 * delta,
                  open=100.5, high=104, low=100.5, close=103.5),
        HTFCandle(timeframe="5m", start=base + 2 * delta, end=base + 3 * delta,
                  open=103.5, high=104.5, low=103, close=104),
    ]

    fvgs = detect_fvgs(candles, direction="BULLISH", min_gap_pct=0.1)

    assert len(fvgs) == 1
    fvg = fvgs[0]
    assert fvg.direction == "BULLISH"
    assert fvg.high == 103  # c3.low
    assert fvg.low == 101   # c1.high
    assert fvg.creation_bar_idx == 2


def test_detect_fvgs_bearish_gap_three_candle_displacement() -> None:
    """Bearish FVG = candle3.high < candle1.low (price gapped DOWN)."""
    base = dt.datetime(2026, 4, 24, 14, 0, tzinfo=dt.timezone.utc)
    delta = dt.timedelta(minutes=5)

    from app.strategies.fractal_amd.signals import HTFCandle

    candles = [
        HTFCandle(timeframe="5m", start=base, end=base + delta,
                  open=104, high=105, low=103, close=104),
        # Displacement candle: bearish
        HTFCandle(timeframe="5m", start=base + delta, end=base + 2 * delta,
                  open=104, high=104, low=100, close=100.5),
        HTFCandle(timeframe="5m", start=base + 2 * delta, end=base + 3 * delta,
                  open=100.5, high=101, low=100, close=100.5),
    ]

    fvgs = detect_fvgs(candles, direction="BEARISH", min_gap_pct=0.1)
    assert len(fvgs) == 1
    fvg = fvgs[0]
    assert fvg.direction == "BEARISH"
    assert fvg.high == 103  # c1.low
    assert fvg.low == 101   # c3.high


def test_detect_fvgs_no_gap_returns_empty() -> None:
    """Three flat candles. No price displacement, no FVG."""
    base = dt.datetime(2026, 4, 24, 14, 0, tzinfo=dt.timezone.utc)
    delta = dt.timedelta(minutes=5)

    from app.strategies.fractal_amd.signals import HTFCandle

    candles = [
        HTFCandle(timeframe="5m", start=base + delta * i,
                  end=base + delta * (i + 1),
                  open=100, high=100.5, low=99.5, close=100)
        for i in range(5)
    ]
    assert detect_fvgs(candles, direction="BULLISH") == []
    assert detect_fvgs(candles, direction="BEARISH") == []


def test_detect_fvgs_too_few_candles_returns_empty() -> None:
    base = dt.datetime(2026, 4, 24, 14, 0, tzinfo=dt.timezone.utc)
    from app.strategies.fractal_amd.signals import HTFCandle
    candles = [
        HTFCandle(timeframe="5m", start=base, end=base + dt.timedelta(minutes=5),
                  open=100, high=101, low=99, close=100),
    ]
    assert detect_fvgs(candles, direction="BULLISH") == []


# --- find_nearest_unfilled_fvg ------------------------------------------


def test_find_nearest_unfilled_fvg_picks_closest_to_price() -> None:
    """Two unfilled FVGs at different distances from price -> the closer
    mid wins."""
    creation = dt.datetime(2026, 4, 24, 14, 0, tzinfo=dt.timezone.utc)
    near = FVG(
        direction="BULLISH",
        high=21010.0,
        low=21000.0,
        creation_time=creation,
        creation_bar_idx=2,
    )
    far = FVG(
        direction="BULLISH",
        high=20910.0,
        low=20900.0,
        creation_time=creation,
        creation_bar_idx=3,
    )

    chosen = find_nearest_unfilled_fvg(
        [near, far], current_price=21008.0, current_bar_idx=10
    )
    assert chosen is near


def test_find_nearest_unfilled_fvg_skips_filled() -> None:
    """A filled FVG is never returned."""
    creation = dt.datetime(2026, 4, 24, 14, 0, tzinfo=dt.timezone.utc)
    filled = FVG(
        direction="BULLISH",
        high=21010.0,
        low=21000.0,
        creation_time=creation,
        creation_bar_idx=2,
        filled=True,
        fill_bar_idx=4,
    )
    open_far = FVG(
        direction="BULLISH",
        high=20910.0,
        low=20900.0,
        creation_time=creation,
        creation_bar_idx=3,
    )
    chosen = find_nearest_unfilled_fvg(
        [filled, open_far], current_price=21008.0, current_bar_idx=10
    )
    assert chosen is open_far


def test_find_nearest_unfilled_fvg_skips_expired_by_window() -> None:
    """An FVG older than expiry_bars is ignored."""
    creation = dt.datetime(2026, 4, 24, 14, 0, tzinfo=dt.timezone.utc)
    stale = FVG(
        direction="BULLISH",
        high=21010.0,
        low=21000.0,
        creation_time=creation,
        creation_bar_idx=2,
    )
    chosen = find_nearest_unfilled_fvg(
        [stale],
        current_price=21008.0,
        current_bar_idx=200,  # 200 - 2 = 198 >> default expiry 60
        expiry_bars=60,
    )
    assert chosen is None


# --- is_in_entry_window --------------------------------------------------


def test_is_in_entry_window_inside_returns_true() -> None:
    et_now = dt.datetime(2026, 4, 24, 10, 0, tzinfo=ET)
    assert is_in_entry_window(
        et_now, open_hour=9, open_min=30, close_hour=14
    )


def test_is_in_entry_window_before_open_returns_false() -> None:
    et_now = dt.datetime(2026, 4, 24, 9, 15, tzinfo=ET)
    assert not is_in_entry_window(
        et_now, open_hour=9, open_min=30, close_hour=14
    )


def test_is_in_entry_window_at_open_minute_returns_true() -> None:
    et_now = dt.datetime(2026, 4, 24, 9, 30, tzinfo=ET)
    assert is_in_entry_window(
        et_now, open_hour=9, open_min=30, close_hour=14
    )


def test_is_in_entry_window_at_close_hour_returns_false() -> None:
    """close_hour is exclusive — 14:00 is OUT of window."""
    et_now = dt.datetime(2026, 4, 24, 14, 0, tzinfo=ET)
    assert not is_in_entry_window(
        et_now, open_hour=9, open_min=30, close_hour=14
    )


def test_is_in_entry_window_one_minute_before_close_returns_true() -> None:
    et_now = dt.datetime(2026, 4, 24, 13, 59, tzinfo=ET)
    assert is_in_entry_window(
        et_now, open_hour=9, open_min=30, close_hour=14
    )
