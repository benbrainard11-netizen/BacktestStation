"""Shared helpers for opening-range MBP execution studies."""

from __future__ import annotations

import datetime as dt

import pandas as pd

from app.research.nq_opening_range_mbp_execution_types import TradeSide


def targets(side: str, event: pd.Series) -> tuple[float, float]:
    if side == "high":
        return float(event["or_high"]) + float(event["or_range_pts"]), float(event["or_low"])
    return float(event["or_low"]) - float(event["or_range_pts"]), float(event["or_high"])


def trade_side(side: str) -> TradeSide:
    if side == "high":
        return "long"
    if side == "low":
        return "short"
    raise ValueError(f"unknown break side: {side!r}")


def trade_rows(mbp1: pd.DataFrame) -> pd.DataFrame:
    return mbp1.loc[(mbp1["action"] == "T") & mbp1["price"].notna()]


def row_ts(row) -> dt.datetime:
    if hasattr(row, "ts_event"):
        return to_utc(row.ts_event)
    if isinstance(row, pd.Series) and "ts_event" in row:
        return to_utc(row["ts_event"])
    return to_utc(row.name)


def to_utc(value: object) -> dt.datetime:
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    else:
        ts = ts.tz_convert("UTC")
    return ts.to_pydatetime(warn=False)
