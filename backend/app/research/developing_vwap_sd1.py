"""Developing VWAP and 1st-standard-deviation band helper.

Pure-math, no-IO helper. Given 1m OHLCV bars and an as-of timestamp,
computes the developing volume-weighted average price (VWAP) and the
1st standard deviation band from session/day/week start up to (but
NOT including) the as-of timestamp.

Matches the volume-weighted variance formula used by
`research.detectors.volume_profile`:

    typical = (open + high + low + close) / 4
    vwap    = (typical * volume).sum() / volume.sum()
    var     = (volume * (typical - vwap) ** 2).sum() / volume.sum()
    sd      = sqrt(var)

The "developing" version of these values is the version computable
in real time inside an active period. At period close, the developing
values converge to the static `vwap` / `vwap_sd` recorded by the
volume_profile detector.

No-lookahead invariant: only bars with timestamp strictly less than
`as_of_ts` are used. Callers feeding ML pipelines must respect this.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

import pandas as pd

from app.research.sessions import (
    GlobexPeriod,
    globex_day_for,
    globex_week_for,
    session_for,
)

UTC = timezone.utc

PeriodKind = Literal[
    "session_asia",
    "session_london",
    "session_ny",
    "globex_day",
    "globex_week",
]

ALL_PERIODS: tuple[PeriodKind, ...] = (
    "session_asia",
    "session_london",
    "session_ny",
    "globex_day",
    "globex_week",
)


@dataclass(frozen=True, slots=True)
class DevelopingSD1:
    """Developing VWAP + 1st-SD band over a single period.

    Attributes
    ----------
    period_start_utc, period_end_utc:
        The period bounds. `vwap` and `sd` are computed over
        [period_start_utc, as_of_ts).
    as_of_ts:
        The cutoff. Bars at or after this timestamp are excluded.
    n_bars:
        How many 1m bars contributed. 0 means the period has not yet
        produced any bars (or the cutoff lands at period start).
    total_volume:
        Sum of bar volumes used.
    vwap, sd:
        Volume-weighted price and its (volume-weighted) standard
        deviation. `sd` is 0.0 when `n_bars` is 0 or when all bars
        share one typical price.
    sd1_high, sd1_low:
        VWAP + sd and VWAP - sd. Convenience.
    """

    period_kind: PeriodKind
    period_start_utc: datetime
    period_end_utc: datetime
    as_of_ts: datetime
    n_bars: int
    total_volume: float
    vwap: float
    sd: float
    sd1_high: float
    sd1_low: float

    @property
    def is_empty(self) -> bool:
        return self.n_bars == 0 or self.total_volume <= 0.0


def _ensure_utc(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        return ts.replace(tzinfo=UTC)
    return ts.astimezone(UTC)


def _period_for(kind: PeriodKind, as_of_ts: datetime) -> GlobexPeriod:
    if kind == "globex_day":
        return globex_day_for(as_of_ts)
    if kind == "globex_week":
        return globex_week_for(as_of_ts)
    if kind == "session_asia":
        return session_for(as_of_ts, "asia")
    if kind == "session_london":
        return session_for(as_of_ts, "london")
    if kind == "session_ny":
        return session_for(as_of_ts, "ny")
    raise ValueError(f"unknown period kind: {kind!r}")


def compute_developing_vwap_sd1(
    bars: pd.DataFrame,
    *,
    period_start_utc: datetime,
    period_end_utc: datetime,
    as_of_ts: datetime,
    period_kind: PeriodKind = "globex_day",
) -> DevelopingSD1:
    """Compute developing VWAP / SD over [period_start_utc, as_of_ts).

    Parameters
    ----------
    bars:
        1m OHLCV DataFrame with a tz-aware UTC DatetimeIndex and the
        columns `open`, `high`, `low`, `close`, `volume`. Bars whose
        index falls outside [period_start_utc, as_of_ts) are ignored.
    period_start_utc, period_end_utc:
        The bounds of the period this developing snapshot belongs to.
        Stored on the result for traceability; only `period_start_utc`
        gates the calculation.
    as_of_ts:
        The cutoff. Bars at or after this timestamp are excluded.

    Returns
    -------
    DevelopingSD1
        Always returned. When no bars qualify, `n_bars == 0` and the
        numeric fields are zero (callers should branch on `is_empty`).
    """
    period_start_utc = _ensure_utc(period_start_utc)
    period_end_utc = _ensure_utc(period_end_utc)
    as_of_ts = _ensure_utc(as_of_ts)

    # Cutoff cannot exceed the period's natural end. If the caller
    # passed a future timestamp, clamp to the period end so the
    # "developing" semantics still hold (post-close behaves identically
    # to the static volume_profile values).
    effective_cutoff = min(as_of_ts, period_end_utc)

    if bars is None or bars.empty or effective_cutoff <= period_start_utc:
        return _empty_result(period_kind, period_start_utc, period_end_utc, as_of_ts)

    if bars.index.tz is None:
        bars = bars.tz_localize(UTC)
    elif str(bars.index.tz) != "UTC":
        bars = bars.tz_convert(UTC)

    in_period = bars[
        (bars.index >= period_start_utc) & (bars.index < effective_cutoff)
    ]
    if in_period.empty:
        return _empty_result(period_kind, period_start_utc, period_end_utc, as_of_ts)

    typical = (
        in_period["open"]
        + in_period["high"]
        + in_period["low"]
        + in_period["close"]
    ) / 4.0
    volume = in_period["volume"].astype(float)

    total_volume = float(volume.sum())
    if total_volume <= 0.0:
        return _empty_result(period_kind, period_start_utc, period_end_utc, as_of_ts)

    vwap = float((typical * volume).sum() / total_volume)
    var = float((volume * (typical - vwap) ** 2).sum() / total_volume)
    sd = math.sqrt(var) if var > 0 else 0.0

    return DevelopingSD1(
        period_kind=period_kind,
        period_start_utc=period_start_utc,
        period_end_utc=period_end_utc,
        as_of_ts=as_of_ts,
        n_bars=int(len(in_period)),
        total_volume=total_volume,
        vwap=vwap,
        sd=sd,
        sd1_high=vwap + sd,
        sd1_low=vwap - sd,
    )


def developing_vwap_sd1_at(
    bars: pd.DataFrame,
    *,
    as_of_ts: datetime,
    period_kind: PeriodKind,
) -> DevelopingSD1:
    """Convenience: resolve the relevant period for `as_of_ts` then
    compute developing VWAP/SD.

    The `bars` DataFrame must cover at least [period_start, as_of_ts).
    The function does NOT do any IO; the caller loads bars however
    they like (BarReader, a static parquet, a buffer in the live
    trader, etc.).
    """
    as_of_ts = _ensure_utc(as_of_ts)
    period = _period_for(period_kind, as_of_ts)
    return compute_developing_vwap_sd1(
        bars,
        period_start_utc=period.start_utc,
        period_end_utc=period.end_utc,
        as_of_ts=as_of_ts,
        period_kind=period_kind,
    )


def developing_vwap_sd1_all_periods(
    bars: pd.DataFrame,
    *,
    as_of_ts: datetime,
    periods: tuple[PeriodKind, ...] = ALL_PERIODS,
) -> dict[PeriodKind, DevelopingSD1]:
    """Compute developing VWAP/SD for every requested period at a
    single `as_of_ts`. Returns a dict keyed by period kind.
    """
    return {
        kind: developing_vwap_sd1_at(bars, as_of_ts=as_of_ts, period_kind=kind)
        for kind in periods
    }


def _empty_result(
    period_kind: PeriodKind,
    period_start_utc: datetime,
    period_end_utc: datetime,
    as_of_ts: datetime,
) -> DevelopingSD1:
    return DevelopingSD1(
        period_kind=period_kind,
        period_start_utc=period_start_utc,
        period_end_utc=period_end_utc,
        as_of_ts=as_of_ts,
        n_bars=0,
        total_volume=0.0,
        vwap=0.0,
        sd=0.0,
        sd1_high=0.0,
        sd1_low=0.0,
    )
