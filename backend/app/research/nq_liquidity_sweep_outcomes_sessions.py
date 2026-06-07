"""Session and level helpers for the NQ liquidity sweep outcome study."""

from __future__ import annotations

import datetime as dt
import math
from zoneinfo import ZoneInfo

import pandas as pd

from app.research.nq_liquidity_sweep_outcomes_types import (
    LiquiditySweepStudyConfig,
    SweepLevel,
)
from app.research.sessions import globex_day_for

ET = ZoneInfo("America/New_York")
UTC = dt.UTC


def normalize_bars(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "ts_event" in out.columns:
        out.index = pd.to_datetime(out["ts_event"], utc=True)
    elif not isinstance(out.index, pd.DatetimeIndex):
        raise ValueError("bars need ts_event column or DatetimeIndex")
    out.index = pd.to_datetime(out.index, utc=True)
    out = out.sort_index()
    for col in ("open", "high", "low", "close"):
        if col not in out.columns:
            raise ValueError(f"bars missing required column: {col}")
        out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


def normalize_mbp1(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "ts_event" in out.columns:
        out.index = pd.to_datetime(out["ts_event"], utc=True)
    elif isinstance(out.index, pd.DatetimeIndex):
        out.index = pd.to_datetime(out.index, utc=True)
        out["ts_event"] = out.index
    else:
        raise ValueError("mbp1 needs ts_event column or DatetimeIndex")
    out.index.name = None
    if not out.index.is_monotonic_increasing:
        if "sequence" in out.columns:
            out = out.sort_values(["ts_event", "sequence"], na_position="last")
        else:
            out = out.sort_index()
    out.index = pd.to_datetime(out["ts_event"], utc=True)
    for col in ("price", "bid_px", "ask_px", "bid_sz", "ask_sz", "size"):
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


def session_dates(start: dt.date, end: dt.date) -> list[dt.date]:
    if start >= end:
        raise ValueError("start must be before end")
    dates: list[dt.date] = []
    cur = start
    while cur < end:
        if cur.weekday() < 5:
            dates.append(cur)
        cur += dt.timedelta(days=1)
    return dates


def et_datetime(date_value: dt.date, time_value: dt.time) -> dt.datetime:
    return dt.datetime.combine(date_value, time_value, tzinfo=ET).astimezone(UTC)


def session_time_bounds(
    session_date: dt.date,
    config: LiquiditySweepStudyConfig,
) -> dict[str, dt.datetime]:
    return {
        "rth_open": et_datetime(session_date, config.rth_open_et),
        "sweep_start": et_datetime(session_date, config.sweep_start_et),
        "rth_close": et_datetime(session_date, config.rth_close_et),
        "globex_close": et_datetime(session_date, config.globex_close_et),
        "overnight_freeze": et_datetime(session_date, config.overnight_freeze_et),
    }


def session_levels(
    bars: pd.DataFrame,
    session_date: dt.date,
    config: LiquiditySweepStudyConfig,
) -> tuple[list[SweepLevel], dict[str, object]]:
    df = normalize_bars(bars)
    prior = _previous_rth_summary(df, session_date, config)
    overnight = _overnight_summary(df, session_date, config)
    levels: list[SweepLevel] = []
    if prior is not None:
        levels.extend(
            [
                SweepLevel(
                    session_date,
                    "prior_day_high",
                    prior["high"],
                    "high",
                    prior["start"],
                    prior["end"],
                ),
                SweepLevel(
                    session_date,
                    "prior_day_low",
                    prior["low"],
                    "low",
                    prior["start"],
                    prior["end"],
                ),
            ]
        )
    if overnight is not None:
        levels.extend(
            [
                SweepLevel(
                    session_date,
                    "overnight_high",
                    overnight["high"],
                    "high",
                    overnight["start"],
                    overnight["end"],
                ),
                SweepLevel(
                    session_date,
                    "overnight_low",
                    overnight["low"],
                    "low",
                    overnight["start"],
                    overnight["end"],
                ),
            ]
        )
    return levels, _session_level_context(session_date, prior, overnight)


def _previous_rth_summary(
    bars: pd.DataFrame,
    session_date: dt.date,
    config: LiquiditySweepStudyConfig,
) -> dict[str, object] | None:
    cur = session_date - dt.timedelta(days=1)
    for _ in range(7):
        if cur.weekday() < 5:
            start = et_datetime(cur, config.rth_open_et)
            end = et_datetime(cur, config.rth_close_et)
            window = _window(bars, start, end)
            if not window.empty:
                return {
                    "date": cur,
                    "start": start,
                    "end": end,
                    "high": float(window["high"].max()),
                    "low": float(window["low"].min()),
                }
        cur -= dt.timedelta(days=1)
    return None


def _overnight_summary(
    bars: pd.DataFrame,
    session_date: dt.date,
    config: LiquiditySweepStudyConfig,
) -> dict[str, object] | None:
    ref = dt.datetime.combine(session_date, dt.time(12), tzinfo=ET)
    period = globex_day_for(ref)
    end = et_datetime(session_date, config.overnight_freeze_et)
    window = _window(bars, period.start_utc, end)
    if window.empty:
        return None
    return {
        "start": period.start_utc,
        "end": end,
        "high": float(window["high"].max()),
        "low": float(window["low"].min()),
    }


def _window(
    df: pd.DataFrame,
    start_utc: dt.datetime,
    end_utc: dt.datetime,
) -> pd.DataFrame:
    return df.loc[
        (df.index >= pd.Timestamp(start_utc)) & (df.index < pd.Timestamp(end_utc))
    ]


def _session_level_context(
    session_date: dt.date,
    prior: dict[str, object] | None,
    overnight: dict[str, object] | None,
) -> dict[str, object]:
    return {
        "session_date": session_date.isoformat(),
        "prior_rth_date": prior["date"].isoformat() if prior else None,
        "prior_day_high": _finite_or_none(prior["high"] if prior else None),
        "prior_day_low": _finite_or_none(prior["low"] if prior else None),
        "overnight_high": _finite_or_none(overnight["high"] if overnight else None),
        "overnight_low": _finite_or_none(overnight["low"] if overnight else None),
        "levels_available": int((2 if prior else 0) + (2 if overnight else 0)),
    }


def _finite_or_none(value: object) -> float | None:
    if value is None:
        return None
    out = float(value)
    return out if math.isfinite(out) else None
