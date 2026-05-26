"""Tests for developing VWAP + 1st-SD helper.

Pinned invariants:
  * Constant typical price → SD == 0, VWAP == typical.
  * Bars at or after the cutoff are never included (no-lookahead).
  * Adding bars never reduces the bar count.
  * At period close, developing values converge to the static formula
    used by volume_profile.VolumeProfileDetector.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pytest

from app.research.developing_vwap_sd1 import (
    ALL_PERIODS,
    DevelopingSD1,
    compute_developing_vwap_sd1,
    developing_vwap_sd1_all_periods,
    developing_vwap_sd1_at,
)

UTC = timezone.utc
ET = ZoneInfo("America/New_York")


def _ohlc_frame(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows).set_index("ts")
    df.index = pd.to_datetime(df.index, utc=True)
    return df.sort_index()


def _bars_constant_typical(
    *,
    start: datetime,
    minutes: int,
    typical: float = 21_000.0,
    volume: float = 100.0,
) -> pd.DataFrame:
    """OHLC where typical price is constant. Useful for SD == 0 invariant."""
    rows = []
    for i in range(minutes):
        ts = start + timedelta(minutes=i)
        rows.append(
            {
                "ts": ts,
                "open": typical,
                "high": typical,
                "low": typical,
                "close": typical,
                "volume": volume,
            }
        )
    return _ohlc_frame(rows)


def _bars_linear_drift(
    *,
    start: datetime,
    minutes: int,
    base: float = 21_000.0,
    step: float = 1.0,
    volume: float = 100.0,
) -> pd.DataFrame:
    rows = []
    for i in range(minutes):
        ts = start + timedelta(minutes=i)
        typical = base + step * i
        rows.append(
            {
                "ts": ts,
                "open": typical,
                "high": typical,
                "low": typical,
                "close": typical,
                "volume": volume,
            }
        )
    return _ohlc_frame(rows)


def _period_close_vp(bars: pd.DataFrame) -> tuple[float, float]:
    """Compute (vwap, sd) the same way volume_profile.VolumeProfileDetector
    does, treating the entire frame as one closed period."""
    typical = (bars["open"] + bars["high"] + bars["low"] + bars["close"]) / 4.0
    volume = bars["volume"].astype(float)
    total = float(volume.sum())
    vwap = float((typical * volume).sum() / total)
    var = float((volume * (typical - vwap) ** 2).sum() / total)
    sd = math.sqrt(var) if var > 0 else 0.0
    return vwap, sd


# ----------------------------------------------------------------------
# Core math
# ----------------------------------------------------------------------


def test_constant_typical_price_gives_zero_sd() -> None:
    start = datetime(2026, 5, 4, 22, 0, tzinfo=UTC)
    bars = _bars_constant_typical(start=start, minutes=60, typical=21_000.0)
    result = compute_developing_vwap_sd1(
        bars,
        period_start_utc=start,
        period_end_utc=start + timedelta(hours=8),
        as_of_ts=start + timedelta(minutes=60),
        period_kind="session_asia",
    )
    assert result.n_bars == 60
    assert result.vwap == pytest.approx(21_000.0)
    assert result.sd == 0.0
    assert result.sd1_high == pytest.approx(21_000.0)
    assert result.sd1_low == pytest.approx(21_000.0)


def test_linear_drift_matches_hand_computed() -> None:
    start = datetime(2026, 5, 4, 22, 0, tzinfo=UTC)
    bars = _bars_linear_drift(start=start, minutes=10, base=21_000.0, step=1.0)
    result = compute_developing_vwap_sd1(
        bars,
        period_start_utc=start,
        period_end_utc=start + timedelta(hours=8),
        as_of_ts=start + timedelta(minutes=10),
        period_kind="session_asia",
    )
    expected_vwap, expected_sd = _period_close_vp(bars)
    assert result.n_bars == 10
    assert result.vwap == pytest.approx(expected_vwap)
    assert result.sd == pytest.approx(expected_sd)
    assert result.sd1_high == pytest.approx(expected_vwap + expected_sd)
    assert result.sd1_low == pytest.approx(expected_vwap - expected_sd)


def test_period_close_matches_static_volume_profile_formula() -> None:
    """At period close, the developing values must equal what the
    static volume_profile detector would record for the same bars."""
    start = datetime(2026, 5, 4, 22, 0, tzinfo=UTC)
    bars = _bars_linear_drift(start=start, minutes=480, base=21_000.0, step=0.25)
    period_end = start + timedelta(minutes=480)
    result = compute_developing_vwap_sd1(
        bars,
        period_start_utc=start,
        period_end_utc=period_end,
        as_of_ts=period_end,
        period_kind="session_asia",
    )
    expected_vwap, expected_sd = _period_close_vp(bars)
    assert result.vwap == pytest.approx(expected_vwap)
    assert result.sd == pytest.approx(expected_sd)


# ----------------------------------------------------------------------
# No-lookahead invariant
# ----------------------------------------------------------------------


def test_bars_at_or_after_cutoff_are_excluded() -> None:
    start = datetime(2026, 5, 4, 22, 0, tzinfo=UTC)
    bars = _bars_linear_drift(start=start, minutes=60, base=21_000.0, step=1.0)
    cutoff = start + timedelta(minutes=30)
    result = compute_developing_vwap_sd1(
        bars,
        period_start_utc=start,
        period_end_utc=start + timedelta(hours=8),
        as_of_ts=cutoff,
        period_kind="session_asia",
    )
    truncated = bars[bars.index < cutoff]
    expected_vwap, expected_sd = _period_close_vp(truncated)
    assert result.n_bars == 30
    assert result.vwap == pytest.approx(expected_vwap)
    assert result.sd == pytest.approx(expected_sd)


def test_cutoff_at_period_start_returns_empty() -> None:
    start = datetime(2026, 5, 4, 22, 0, tzinfo=UTC)
    bars = _bars_constant_typical(start=start, minutes=60)
    result = compute_developing_vwap_sd1(
        bars,
        period_start_utc=start,
        period_end_utc=start + timedelta(hours=8),
        as_of_ts=start,
        period_kind="session_asia",
    )
    assert result.is_empty
    assert result.n_bars == 0
    assert result.vwap == 0.0
    assert result.sd == 0.0


def test_no_bars_in_period_returns_empty() -> None:
    start = datetime(2026, 5, 4, 22, 0, tzinfo=UTC)
    bars = _bars_constant_typical(
        start=start - timedelta(hours=2), minutes=30
    )
    result = compute_developing_vwap_sd1(
        bars,
        period_start_utc=start,
        period_end_utc=start + timedelta(hours=8),
        as_of_ts=start + timedelta(minutes=30),
        period_kind="session_asia",
    )
    assert result.is_empty


def test_cutoff_past_period_end_clamps_to_period_end() -> None:
    """If a caller asks for an as_of_ts in the future relative to the
    period end, the developing value should equal the period-close
    value, not over-include extra-period bars."""
    start = datetime(2026, 5, 4, 22, 0, tzinfo=UTC)
    period_end = start + timedelta(hours=8)
    # In-period bars + extra post-period bars.
    in_period = _bars_linear_drift(start=start, minutes=480, base=21_000.0, step=0.25)
    extra = _bars_linear_drift(
        start=period_end, minutes=60, base=22_000.0, step=0.25
    )
    bars = pd.concat([in_period, extra]).sort_index()
    result = compute_developing_vwap_sd1(
        bars,
        period_start_utc=start,
        period_end_utc=period_end,
        as_of_ts=period_end + timedelta(hours=2),
        period_kind="session_asia",
    )
    expected_vwap, expected_sd = _period_close_vp(in_period)
    assert result.vwap == pytest.approx(expected_vwap)
    assert result.sd == pytest.approx(expected_sd)


# ----------------------------------------------------------------------
# Monotonicity
# ----------------------------------------------------------------------


def test_bar_count_is_monotone_in_cutoff() -> None:
    start = datetime(2026, 5, 4, 22, 0, tzinfo=UTC)
    bars = _bars_constant_typical(start=start, minutes=120)
    cuts = [
        start + timedelta(minutes=10),
        start + timedelta(minutes=30),
        start + timedelta(minutes=60),
        start + timedelta(minutes=120),
    ]
    results = [
        compute_developing_vwap_sd1(
            bars,
            period_start_utc=start,
            period_end_utc=start + timedelta(hours=8),
            as_of_ts=c,
            period_kind="session_asia",
        )
        for c in cuts
    ]
    counts = [r.n_bars for r in results]
    assert counts == sorted(counts), f"bar count not monotone: {counts}"


# ----------------------------------------------------------------------
# Period resolution via session helpers
# ----------------------------------------------------------------------


def test_developing_at_resolves_globex_day() -> None:
    # Pick a Tue at 14:00 ET, clearly inside the Mon 18:00 -> Tue 17:00 day.
    tue_14_et = datetime(2026, 5, 5, 14, 0, tzinfo=ET)
    tue_14_utc = tue_14_et.astimezone(UTC)
    # Build bars from Globex day start (Mon 18:00 ET) up through 14:00 ET.
    day_start_utc = datetime(2026, 5, 4, 22, 0, tzinfo=UTC)  # Mon 18:00 ET → UTC
    bars = _bars_constant_typical(
        start=day_start_utc, minutes=20 * 60, typical=21_000.0
    )
    result = developing_vwap_sd1_at(
        bars, as_of_ts=tue_14_utc, period_kind="globex_day"
    )
    assert result.period_kind == "globex_day"
    assert result.period_start_utc == day_start_utc
    assert result.n_bars > 0
    assert result.vwap == pytest.approx(21_000.0)
    assert result.sd == 0.0


def test_developing_all_periods_returns_one_per_kind() -> None:
    tue_14_utc = datetime(2026, 5, 5, 14, 0, tzinfo=ET).astimezone(UTC)
    day_start_utc = datetime(2026, 5, 4, 22, 0, tzinfo=UTC)
    bars = _bars_constant_typical(
        start=day_start_utc, minutes=20 * 60, typical=21_000.0
    )
    out = developing_vwap_sd1_all_periods(bars, as_of_ts=tue_14_utc)
    assert set(out.keys()) == set(ALL_PERIODS)
    for kind, snap in out.items():
        assert isinstance(snap, DevelopingSD1)
        assert snap.period_kind == kind


# ----------------------------------------------------------------------
# Edge cases
# ----------------------------------------------------------------------


def test_zero_volume_bars_return_empty() -> None:
    start = datetime(2026, 5, 4, 22, 0, tzinfo=UTC)
    bars = _bars_constant_typical(start=start, minutes=10, volume=0.0)
    result = compute_developing_vwap_sd1(
        bars,
        period_start_utc=start,
        period_end_utc=start + timedelta(hours=8),
        as_of_ts=start + timedelta(minutes=10),
        period_kind="session_asia",
    )
    assert result.is_empty


def test_empty_dataframe_returns_empty() -> None:
    start = datetime(2026, 5, 4, 22, 0, tzinfo=UTC)
    empty = pd.DataFrame(
        columns=["open", "high", "low", "close", "volume"],
        index=pd.DatetimeIndex([], tz="UTC"),
    )
    result = compute_developing_vwap_sd1(
        empty,
        period_start_utc=start,
        period_end_utc=start + timedelta(hours=8),
        as_of_ts=start + timedelta(minutes=10),
        period_kind="session_asia",
    )
    assert result.is_empty


def test_naive_cutoff_treated_as_utc() -> None:
    start = datetime(2026, 5, 4, 22, 0, tzinfo=UTC)
    bars = _bars_constant_typical(start=start, minutes=60)
    naive_cutoff = datetime(2026, 5, 4, 22, 30)  # no tz
    result = compute_developing_vwap_sd1(
        bars,
        period_start_utc=start,
        period_end_utc=start + timedelta(hours=8),
        as_of_ts=naive_cutoff,
        period_kind="session_asia",
    )
    assert result.n_bars == 30
