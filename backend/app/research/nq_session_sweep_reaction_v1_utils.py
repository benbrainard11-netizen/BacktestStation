"""Utility helpers for the NQ Session Sweep Reaction V1 backtest."""

from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

import pandas as pd

from app.research.nq_session_sweep_reaction_v1_types import SweepReactionConfig

ET = ZoneInfo("America/New_York")
UTC = dt.UTC


def session_times(
    next_session_date: str,
    config: SweepReactionConfig,
) -> dict[str, dt.datetime]:
    d = dt.date.fromisoformat(next_session_date)
    return {
        "entry_start": et_datetime(d, config.entry_start_et),
        "sweep_cutoff": et_datetime(d, config.sweep_cutoff_et),
        "entry_deadline": et_datetime(d, config.entry_deadline_et),
        "forced_flat": et_datetime(d, config.forced_flat_et),
    }


def et_datetime(date_value: dt.date, time_value: dt.time) -> dt.datetime:
    return dt.datetime.combine(date_value, time_value, tzinfo=ET).astimezone(UTC)


def normalize_bars(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "ts_event" in out.columns:
        out.index = pd.to_datetime(out["ts_event"], utc=True)
    elif not isinstance(out.index, pd.DatetimeIndex):
        raise ValueError("bars need ts_event column or DatetimeIndex")
    out.index = pd.to_datetime(out.index, utc=True)
    required = {"open", "high", "low", "close"}
    missing = required - set(out.columns)
    if missing:
        raise ValueError(f"bars missing required columns: {sorted(missing)}")
    out = out.sort_index()
    for col in required:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


def normalize_mbp1(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "ts_event" not in out.columns and not isinstance(out.index, pd.DatetimeIndex):
        raise ValueError("mbp1 needs ts_event column or DatetimeIndex")
    if "ts_event" in out.columns:
        out.index = pd.to_datetime(out["ts_event"], utc=True)
    else:
        out.index = pd.to_datetime(out.index, utc=True)
        out["ts_event"] = out.index
    out.index.name = None
    if "sequence" in out.columns:
        out = out.sort_values(["ts_event", "sequence"], na_position="last")
    else:
        out = out.sort_index()
    out.index = pd.to_datetime(out["ts_event"], utc=True)
    required = {"action", "price", "bid_px", "ask_px", "bid_sz", "ask_sz"}
    missing = required - set(out.columns)
    if missing:
        raise ValueError(f"mbp1 missing required columns: {sorted(missing)}")
    for col in ("price", "bid_px", "ask_px", "bid_sz", "ask_sz"):
        out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


def events_between(
    df: pd.DataFrame,
    start_utc: dt.datetime,
    end_utc: dt.datetime,
    *,
    inclusive_end: bool = False,
) -> pd.DataFrame:
    if inclusive_end:
        return df.loc[
            (df.index >= pd.Timestamp(start_utc)) & (df.index <= pd.Timestamp(end_utc))
        ]
    return df.loc[
        (df.index >= pd.Timestamp(start_utc)) & (df.index < pd.Timestamp(end_utc))
    ]


def trade_events_between(
    df: pd.DataFrame,
    start_utc: dt.datetime,
    end_utc: dt.datetime,
    *,
    inclusive_end: bool = False,
) -> pd.DataFrame:
    window = events_between(df, start_utc, end_utc, inclusive_end=inclusive_end)
    return window.loc[(window["action"] == "T") & window["price"].notna()]


def first_valid_event_after(
    df: pd.DataFrame,
    *,
    start_utc: dt.datetime,
    end_utc: dt.datetime,
):
    window = df.loc[
        (df.index > pd.Timestamp(start_utc))
        & (df.index <= pd.Timestamp(end_utc))
    ]
    window = window.loc[
        window["bid_px"].notna()
        & window["ask_px"].notna()
        & (window["ask_px"] >= window["bid_px"])
    ]
    if window.empty:
        return None
    return window.iloc[0]


def to_datetime(value) -> dt.datetime:
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    else:
        ts = ts.tz_convert("UTC")
    return ts.to_pydatetime(warn=False)


def row_ts(row) -> dt.datetime:
    if hasattr(row, "ts_event"):
        return to_datetime(row.ts_event)
    if isinstance(row, pd.Series) and "ts_event" in row:
        return to_datetime(row["ts_event"])
    if hasattr(row, "Index"):
        return to_datetime(row.Index)
    raise ValueError("row has no timestamp")
