"""Unit tests for Fractal AMD signal primitives.

Tests each signal helper against handcrafted bar fixtures so failures
point at one concept at a time. Higher-level integration is covered
in test_fractal_amd_scaffold.py.
"""

from __future__ import annotations

import datetime as dt

from app.backtest.strategy import Bar
from app.strategies.fractal_amd.signals import (
    ET,
    candle_bounds,
    check_candle_pair,
    detect_rejection,
    detect_smt_at_level,
    get_ohlc,
)


# --- Bar fixtures ------------------------------------------------------


def _bar(
    *,
    symbol: str,
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


def _flat_bars(
    symbol: str, start: dt.datetime, minutes: int, base: float
) -> list[Bar]:
    """Build a sequence of N 1m bars with constant OHLC at `base`."""
    bars = []
    for i in range(minutes):
        ts = start + dt.timedelta(minutes=i)
        bars.append(
            _bar(symbol=symbol, ts=ts, o=base, h=base + 0.25, low=base - 0.25, c=base)
        )
    return bars


# --- candle_bounds + get_ohlc ------------------------------------------


def test_candle_bounds_session_returns_four_globex_sessions():
    day = dt.datetime(2026, 4, 24, 12, 0, tzinfo=ET)
    bounds = candle_bounds(day, "session")
    assert len(bounds) == 4
    # Asia: 18:00 prior day -> 00:00 today
    assert bounds[0][0] == dt.datetime(2026, 4, 23, 18, 0, tzinfo=ET)
    assert bounds[0][1] == dt.datetime(2026, 4, 24, 0, 0, tzinfo=ET)
    # NY_PM: 12:00 -> 17:00
    assert bounds[3][0] == dt.datetime(2026, 4, 24, 12, 0, tzinfo=ET)
    assert bounds[3][1] == dt.datetime(2026, 4, 24, 17, 0, tzinfo=ET)


def test_candle_bounds_1h_covers_full_globex_day():
    day = dt.datetime(2026, 4, 24, 12, 0, tzinfo=ET)
    bounds = candle_bounds(day, "1H")
    # Globex day = 23 hours. Every bound is exactly 60min.
    assert len(bounds) == 23
    for s, e in bounds:
        assert (e - s) == dt.timedelta(hours=1)


def test_get_ohlc_aggregates_bars_in_range():
    start = dt.datetime(2026, 4, 24, 14, 0, tzinfo=dt.timezone.utc)
    bars = [
        _bar(symbol="NQ", ts=start, o=100, h=102, low=99, c=101),
        _bar(
            symbol="NQ",
            ts=start + dt.timedelta(minutes=1),
            o=101,
            h=104,
            low=100,
            c=103,
        ),
        _bar(
            symbol="NQ",
            ts=start + dt.timedelta(minutes=2),
            o=103,
            h=103.5,
            low=98,
            c=99,
        ),
    ]
    ohlc = get_ohlc(bars, start, start + dt.timedelta(minutes=3))
    assert ohlc is not None
    assert ohlc.open == 100
    assert ohlc.high == 104
    assert ohlc.low == 98
    assert ohlc.close == 99


def test_get_ohlc_returns_none_when_no_bars_in_range():
    start = dt.datetime(2026, 4, 24, 14, 0, tzinfo=dt.timezone.utc)
    bars = [_bar(symbol="NQ", ts=start, o=100, h=101, low=99, c=100)]
    out_of_range_start = start + dt.timedelta(hours=2)
    assert get_ohlc(
        bars, out_of_range_start, out_of_range_start + dt.timedelta(minutes=10)
    ) is None


# --- detect_smt_at_level -----------------------------------------------


def test_smt_high_sweep_one_swept_two_held_is_bearish():
    """NQ sweeps prior session high but ES and YM hold. Canonical
    bearish SMT divergence."""
    start = dt.datetime(2026, 4, 24, 14, 0, tzinfo=dt.timezone.utc)
    end = start + dt.timedelta(hours=1)

    # NQ sweeps above its level (110), ES + YM stay below.
    nq_bars = [_bar(symbol="NQ", ts=start, o=109, h=112, low=108, c=110)]
    es_bars = [_bar(symbol="ES", ts=start, o=99, h=99.5, low=98, c=99)]
    ym_bars = [_bar(symbol="YM", ts=start, o=199, h=199.5, low=198, c=199)]

    result = detect_smt_at_level(
        bars_by_asset={"NQ": nq_bars, "ES": es_bars, "YM": ym_bars},
        level_prices={"NQ": 110, "ES": 100, "YM": 200},
        direction="high",
        window_start=start,
        window_end=end,
    )
    assert result.has_smt is True
    assert result.direction == "BEARISH"
    assert result.sweepers == ["NQ"]
    assert sorted(result.holders) == ["ES", "YM"]


def test_smt_low_sweep_one_swept_two_held_is_bullish():
    """NQ sweeps below prior low, ES + YM hold. Bullish SMT."""
    start = dt.datetime(2026, 4, 24, 14, 0, tzinfo=dt.timezone.utc)
    end = start + dt.timedelta(hours=1)

    nq_bars = [_bar(symbol="NQ", ts=start, o=110, h=111, low=108, c=109)]
    es_bars = [_bar(symbol="ES", ts=start, o=101, h=102, low=100.5, c=101)]
    ym_bars = [_bar(symbol="YM", ts=start, o=201, h=202, low=200.5, c=201)]

    result = detect_smt_at_level(
        bars_by_asset={"NQ": nq_bars, "ES": es_bars, "YM": ym_bars},
        level_prices={"NQ": 109, "ES": 100, "YM": 200},
        direction="low",
        window_start=start,
        window_end=end,
    )
    assert result.has_smt is True
    assert result.direction == "BULLISH"
    assert result.sweepers == ["NQ"]


def test_smt_all_swept_no_divergence():
    """All three sweep -> no SMT."""
    start = dt.datetime(2026, 4, 24, 14, 0, tzinfo=dt.timezone.utc)
    end = start + dt.timedelta(hours=1)
    nq = [_bar(symbol="NQ", ts=start, o=109, h=115, low=108, c=110)]
    es = [_bar(symbol="ES", ts=start, o=99, h=105, low=98, c=99)]
    ym = [_bar(symbol="YM", ts=start, o=199, h=205, low=198, c=199)]
    result = detect_smt_at_level(
        bars_by_asset={"NQ": nq, "ES": es, "YM": ym},
        level_prices={"NQ": 110, "ES": 100, "YM": 200},
        direction="high",
        window_start=start,
        window_end=end,
    )
    assert result.has_smt is False


def test_smt_none_swept_no_divergence():
    """No one sweeps -> no SMT."""
    start = dt.datetime(2026, 4, 24, 14, 0, tzinfo=dt.timezone.utc)
    end = start + dt.timedelta(hours=1)
    nq = [_bar(symbol="NQ", ts=start, o=109, h=109.5, low=108, c=109)]
    result = detect_smt_at_level(
        bars_by_asset={"NQ": nq},
        level_prices={"NQ": 110},
        direction="high",
        window_start=start,
        window_end=end,
    )
    assert result.has_smt is False


# --- detect_rejection --------------------------------------------------


def test_rejection_bearish_two_swept_two_rejected():
    """All three sweep prior high, all three close back at-or-below it.
    Strong bearish rejection."""
    ref_start = dt.datetime(2026, 4, 24, 13, 0, tzinfo=dt.timezone.utc)
    ref_end = dt.datetime(2026, 4, 24, 14, 0, tzinfo=dt.timezone.utc)
    cur_start = ref_end
    cur_end = cur_start + dt.timedelta(hours=1)

    # ref candle: NQ high=110, ES high=100, YM high=200
    nq = [_bar(symbol="NQ", ts=ref_start, o=108, h=110, low=107, c=109)]
    es = [_bar(symbol="ES", ts=ref_start, o=98, h=100, low=97, c=99)]
    ym = [_bar(symbol="YM", ts=ref_start, o=198, h=200, low=197, c=199)]

    # cur candle: each sweeps above its prior high, then closes back AT or below
    nq.append(_bar(symbol="NQ", ts=cur_start, o=109, h=112, low=108, c=109))
    es.append(_bar(symbol="ES", ts=cur_start, o=99, h=102, low=98, c=99))
    ym.append(_bar(symbol="YM", ts=cur_start, o=199, h=202, low=198, c=199))

    sigs = detect_rejection(
        bars_by_asset={"NQ": nq, "ES": es, "YM": ym},
        candle_start=cur_start,
        candle_end=cur_end,
        ref_start=ref_start,
        ref_end=ref_end,
    )
    assert len(sigs) == 1
    assert sigs[0].direction == "BEARISH"
    assert sigs[0].n_swept == 3
    assert sigs[0].n_rejected == 3


def test_rejection_no_sweep_no_signal():
    """No one sweeps -> no rejection."""
    ref_start = dt.datetime(2026, 4, 24, 13, 0, tzinfo=dt.timezone.utc)
    ref_end = dt.datetime(2026, 4, 24, 14, 0, tzinfo=dt.timezone.utc)
    cur_start = ref_end
    cur_end = cur_start + dt.timedelta(hours=1)

    nq = [
        _bar(symbol="NQ", ts=ref_start, o=108, h=110, low=107, c=109),
        _bar(symbol="NQ", ts=cur_start, o=109, h=109.5, low=108, c=109),  # never swept
    ]
    es = [
        _bar(symbol="ES", ts=ref_start, o=98, h=100, low=97, c=99),
        _bar(symbol="ES", ts=cur_start, o=99, h=99.5, low=98, c=99),
    ]
    ym = [
        _bar(symbol="YM", ts=ref_start, o=198, h=200, low=197, c=199),
        _bar(symbol="YM", ts=cur_start, o=199, h=199.5, low=198, c=199),
    ]
    sigs = detect_rejection(
        bars_by_asset={"NQ": nq, "ES": es, "YM": ym},
        candle_start=cur_start,
        candle_end=cur_end,
        ref_start=ref_start,
        ref_end=ref_end,
    )
    assert sigs == []


def test_rejection_swept_but_not_rejected_no_signal():
    """All sweep but all close ABOVE the prior high -- not a rejection,
    that's a continuation."""
    ref_start = dt.datetime(2026, 4, 24, 13, 0, tzinfo=dt.timezone.utc)
    ref_end = dt.datetime(2026, 4, 24, 14, 0, tzinfo=dt.timezone.utc)
    cur_start = ref_end
    cur_end = cur_start + dt.timedelta(hours=1)

    nq = [
        _bar(symbol="NQ", ts=ref_start, o=108, h=110, low=107, c=109),
        _bar(symbol="NQ", ts=cur_start, o=109, h=115, low=108, c=114),  # closed ABOVE 110
    ]
    es = [
        _bar(symbol="ES", ts=ref_start, o=98, h=100, low=97, c=99),
        _bar(symbol="ES", ts=cur_start, o=99, h=105, low=98, c=104),
    ]
    ym = [
        _bar(symbol="YM", ts=ref_start, o=198, h=200, low=197, c=199),
        _bar(symbol="YM", ts=cur_start, o=199, h=205, low=198, c=204),
    ]
    sigs = detect_rejection(
        bars_by_asset={"NQ": nq, "ES": es, "YM": ym},
        candle_start=cur_start,
        candle_end=cur_end,
        ref_start=ref_start,
        ref_end=ref_end,
    )
    assert sigs == []


# --- check_candle_pair (combinator) ------------------------------------


def test_check_candle_pair_emits_bearish_on_smt():
    """Pair where NQ sweeps prior high but ES + YM don't -> BEARISH stage signal."""
    ref_start = dt.datetime(2026, 4, 24, 13, 0, tzinfo=dt.timezone.utc)
    ref_end = dt.datetime(2026, 4, 24, 14, 0, tzinfo=dt.timezone.utc)
    cur_start = ref_end
    cur_end = cur_start + dt.timedelta(hours=1)

    # ref candle highs: NQ=110, ES=100, YM=200
    # cur candle: NQ sweeps 110, ES + YM do NOT sweep their highs
    nq = [
        _bar(symbol="NQ.c.0", ts=ref_start, o=108, h=110, low=107, c=109),
        _bar(symbol="NQ.c.0", ts=cur_start, o=109, h=112, low=108, c=110.5),
    ]
    es = [
        _bar(symbol="ES.c.0", ts=ref_start, o=98, h=100, low=97, c=99),
        _bar(symbol="ES.c.0", ts=cur_start, o=99, h=99.8, low=98, c=99.2),
    ]
    ym = [
        _bar(symbol="YM.c.0", ts=ref_start, o=198, h=200, low=197, c=199),
        _bar(symbol="YM.c.0", ts=cur_start, o=199, h=199.8, low=198, c=199.2),
    ]
    sig = check_candle_pair(
        bars_by_asset={"NQ.c.0": nq, "ES.c.0": es, "YM.c.0": ym},
        cur_start=cur_start,
        cur_end=cur_end,
        ref_start=ref_start,
        ref_end=ref_end,
        timeframe="1H",
    )
    assert sig is not None
    assert sig.direction == "BEARISH"
    assert sig.has_smt is True
    assert sig.smt_level_swept == 110  # NQ's prior high


def test_check_candle_pair_returns_none_when_no_signal():
    """Quiet candle pair, no sweep on either side -> None."""
    ref_start = dt.datetime(2026, 4, 24, 13, 0, tzinfo=dt.timezone.utc)
    ref_end = dt.datetime(2026, 4, 24, 14, 0, tzinfo=dt.timezone.utc)
    cur_start = ref_end
    cur_end = cur_start + dt.timedelta(hours=1)

    nq = _flat_bars("NQ.c.0", ref_start, 120, base=110)
    es = _flat_bars("ES.c.0", ref_start, 120, base=100)
    ym = _flat_bars("YM.c.0", ref_start, 120, base=200)
    sig = check_candle_pair(
        bars_by_asset={"NQ.c.0": nq, "ES.c.0": es, "YM.c.0": ym},
        cur_start=cur_start,
        cur_end=cur_end,
        ref_start=ref_start,
        ref_end=ref_end,
        timeframe="1H",
    )
    assert sig is None


def test_check_candle_pair_direction_filter():
    """If only BEARISH signal exists but caller requests BULLISH -> None."""
    ref_start = dt.datetime(2026, 4, 24, 13, 0, tzinfo=dt.timezone.utc)
    ref_end = dt.datetime(2026, 4, 24, 14, 0, tzinfo=dt.timezone.utc)
    cur_start = ref_end
    cur_end = cur_start + dt.timedelta(hours=1)

    nq = [
        _bar(symbol="NQ.c.0", ts=ref_start, o=108, h=110, low=107, c=109),
        _bar(symbol="NQ.c.0", ts=cur_start, o=109, h=112, low=108, c=110.5),
    ]
    es = [
        _bar(symbol="ES.c.0", ts=ref_start, o=98, h=100, low=97, c=99),
        _bar(symbol="ES.c.0", ts=cur_start, o=99, h=99.8, low=98, c=99.2),
    ]
    ym = [
        _bar(symbol="YM.c.0", ts=ref_start, o=198, h=200, low=197, c=199),
        _bar(symbol="YM.c.0", ts=cur_start, o=199, h=199.8, low=198, c=199.2),
    ]
    sig = check_candle_pair(
        bars_by_asset={"NQ.c.0": nq, "ES.c.0": es, "YM.c.0": ym},
        cur_start=cur_start,
        cur_end=cur_end,
        ref_start=ref_start,
        ref_end=ref_end,
        timeframe="1H",
        direction_filter="BULLISH",
    )
    assert sig is None
