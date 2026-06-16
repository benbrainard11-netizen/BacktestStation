"""MBP/event sequencing for middle-third opening-range break studies."""

from __future__ import annotations

import datetime as dt
import math

import pandas as pd

from app.research.nq_opening_range_mbp_execution_types import BreakSide
from app.research.nq_opening_range_mbp_execution_utils import (
    row_ts,
    targets,
    trade_rows,
    trade_side,
)

OUTCOME_CONTINUATION = "continuation_breakout"
OUTCOME_REVERSAL = "failed_breakout_reversal"


def build_mbp_event(event: pd.Series, mbp1: pd.DataFrame) -> dict[str, object]:
    session_date = str(event["session_date"])
    first = first_break(mbp1, float(event["or_high"]), float(event["or_low"]))
    base = {
        "event_id": event_id(session_date),
        "symbol": event.get("symbol", "NQ.c.0"),
        "session_date": session_date,
        "month": event["month"],
        "is_holdout": bool(event["is_holdout"]),
        "opening_drive_close_bucket": event["opening_drive_close_bucket"],
        "or_open": float(event["or_open"]),
        "or_high": float(event["or_high"]),
        "or_low": float(event["or_low"]),
        "or_close": float(event["or_close"]),
        "or_range_pts": float(event["or_range_pts"]),
        "bar_first_break_side": event["first_break_side"],
        "bar_outcome_label": event["outcome_label"],
        "mbp_rows": int(len(mbp1)),
    }
    if first is None:
        return {
            **base,
            "first_break_side": "none",
            "trade_side": None,
            "first_break_ts": None,
            "first_break_price": math.nan,
            "continuation_target": math.nan,
            "reversal_target": math.nan,
            "outcome_label": "no_break",
            "outcome_hit_ts": None,
            "outcome_price": math.nan,
            "outcome_error": "no_mbp_break",
        }
    side, ts, price = first
    continuation, reversal = targets(side, event)
    outcome = mbp_outcome(mbp1, side, ts, continuation, reversal)
    return {
        **base,
        "first_break_side": side,
        "trade_side": trade_side(side),
        "first_break_ts": ts,
        "first_break_price": price,
        "continuation_target": continuation,
        "reversal_target": reversal,
        **outcome,
    }


def first_break(
    mbp1: pd.DataFrame,
    or_high: float,
    or_low: float,
) -> tuple[BreakSide, dt.datetime, float] | None:
    trades = trade_rows(mbp1)
    for row in trades.itertuples(index=False):
        price = float(row.price)
        if price > or_high:
            return "high", row_ts(row), price
        if price < or_low:
            return "low", row_ts(row), price
    return None


def mbp_outcome(
    mbp1: pd.DataFrame,
    side: str,
    break_ts: dt.datetime,
    continuation: float,
    reversal: float,
) -> dict[str, object]:
    for row in trade_rows(mbp1.loc[mbp1.index >= pd.Timestamp(break_ts)]).itertuples(index=False):
        price = float(row.price)
        ts = row_ts(row)
        if side == "high":
            if price >= continuation:
                return outcome_row(OUTCOME_CONTINUATION, ts, price, None)
            if price <= reversal:
                return outcome_row(OUTCOME_REVERSAL, ts, price, None)
        elif price <= continuation:
            return outcome_row(OUTCOME_CONTINUATION, ts, price, None)
        elif price >= reversal:
            return outcome_row(OUTCOME_REVERSAL, ts, price, None)
    return outcome_row("ambiguous", None, math.nan, "neither_target_hit")


def outcome_row(
    label: str,
    hit_ts: dt.datetime | None,
    price: float,
    error: str | None,
) -> dict[str, object]:
    return {
        "outcome_label": label,
        "outcome_hit_ts": hit_ts,
        "outcome_price": price,
        "outcome_error": error,
    }


def event_id(session_date: str) -> str:
    return f"or_middle_third:{session_date}"
