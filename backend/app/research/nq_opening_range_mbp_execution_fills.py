"""Entry and exit simulation for opening-range MBP studies."""

from __future__ import annotations

import datetime as dt
import math

import pandas as pd

from app.research.nq_liquidity_sweep_outcomes_sessions import ET
from app.research.nq_opening_range_mbp_execution_types import (
    EntryStyle,
    OpeningRangeMbpExecutionConfig,
    TradeSide,
)
from app.research.nq_opening_range_mbp_execution_utils import (
    row_ts,
    to_utc,
    trade_rows,
    trade_side,
)


def simulate_entry_style(
    event: pd.Series,
    mbp1: pd.DataFrame,
    entry_style: EntryStyle,
    config: OpeningRangeMbpExecutionConfig,
) -> dict[str, object]:
    side = str(event["first_break_side"])
    if side not in {"high", "low"}:
        return skip_row(event, entry_style, "no_break")
    entry = entry_for_style(event, mbp1, entry_style, config)
    if entry is None:
        return skip_row(event, entry_style, "no_entry")
    entry_ts, entry_price, entry_note = entry
    trade = trade_side(side)
    stop = float(event["reversal_target"])
    target = float(event["continuation_target"])
    exit_ts, exit_price, reason, confidence = exit_after_entry(
        mbp1,
        trade,
        entry_ts,
        stop,
        target,
        forced_flat_ts(str(event["session_date"]), config),
        config,
    )
    pnl = pnl_dollars(trade, entry_price, exit_price, config)
    risk_pts = abs(entry_price - stop)
    return {
        **attempt_base(event, entry_style),
        "status": "filled",
        "skip_reason": None,
        "entry_note": entry_note,
        "entry_ts": entry_ts,
        "entry_price": entry_price,
        "stop_price": stop,
        "target_price": target,
        "exit_ts": exit_ts,
        "exit_price": exit_price,
        "exit_reason": reason,
        "fill_confidence": confidence,
        "risk_pts": risk_pts,
        "pnl": pnl,
        "r_multiple": pnl / (risk_pts * config.contract_value) if risk_pts else math.nan,
    }


def entry_for_style(
    event: pd.Series,
    mbp1: pd.DataFrame,
    entry_style: EntryStyle,
    config: OpeningRangeMbpExecutionConfig,
) -> tuple[dt.datetime, float, str] | None:
    break_ts = to_utc(event["first_break_ts"])
    trade = trade_side(str(event["first_break_side"]))
    level = float(event["or_high"] if trade == "long" else event["or_low"])
    if entry_style == "immediate_break":
        row = first_valid_quote(mbp1, break_ts)
        if row is None:
            return None
        return quote_entry(row, trade, config, "first_quote_after_break")
    if entry_style == "confirmation_30s":
        row = first_valid_quote(mbp1, break_ts + dt.timedelta(seconds=config.confirmation_seconds))
        if row is None or not still_beyond_level(mid(row), trade, level):
            return None
        return quote_entry(row, trade, config, "30s_confirmation")
    return first_retest_entry(event, mbp1, config)


def first_retest_entry(
    event: pd.Series,
    mbp1: pd.DataFrame,
    config: OpeningRangeMbpExecutionConfig,
) -> tuple[dt.datetime, float, str] | None:
    break_ts = to_utc(event["first_break_ts"])
    trade = trade_side(str(event["first_break_side"]))
    level = float(event["or_high"] if trade == "long" else event["or_low"])
    end = break_ts + dt.timedelta(minutes=config.retest_deadline_minutes)
    for row in trade_rows(mbp1.loc[(mbp1.index >= break_ts) & (mbp1.index <= end)]).itertuples(
        index=False
    ):
        price = float(row.price)
        if trade == "long" and price <= level:
            return row_ts(row), level + config.slippage_pts, "first_level_retest"
        if trade == "short" and price >= level:
            return row_ts(row), level - config.slippage_pts, "first_level_retest"
    return None


def exit_after_entry(
    mbp1: pd.DataFrame,
    trade: TradeSide,
    entry_ts: dt.datetime,
    stop: float,
    target: float,
    forced_flat: dt.datetime,
    config: OpeningRangeMbpExecutionConfig,
) -> tuple[dt.datetime, float, str, str]:
    events = mbp1.loc[mbp1.index > pd.Timestamp(entry_ts)]
    last = None
    for row in events.itertuples(index=False):
        last = row
        ts = row_ts(row)
        if ts >= forced_flat:
            return ts, market_exit(row, trade, config), "forced_flat", "event_sequence"
        if str(row.action) != "T" or pd.isna(row.price):
            continue
        price = float(row.price)
        if trade == "long":
            if price <= stop:
                return ts, stop - config.slippage_pts, "stop", "event_sequence"
            if price >= target:
                return ts, target, "target", "event_sequence"
        elif price >= stop:
            return ts, stop + config.slippage_pts, "stop", "event_sequence"
        elif price <= target:
            return ts, target, "target", "event_sequence"
    if last is not None:
        return row_ts(last), market_exit(last, trade, config), "forced_flat", "last_event"
    return entry_ts, stop if trade == "long" else target, "forced_flat", "no_events"


def first_valid_quote(mbp1: pd.DataFrame, start: dt.datetime) -> pd.Series | None:
    window = mbp1.loc[mbp1.index >= pd.Timestamp(start)]
    window = window.loc[
        window["bid_px"].notna()
        & window["ask_px"].notna()
        & (window["ask_px"] >= window["bid_px"])
    ]
    return None if window.empty else window.iloc[0]


def quote_entry(
    row: pd.Series,
    trade: TradeSide,
    config: OpeningRangeMbpExecutionConfig,
    note: str,
) -> tuple[dt.datetime, float, str]:
    if trade == "long":
        return row_ts(row), float(row.ask_px) + config.slippage_pts, note
    return row_ts(row), float(row.bid_px) - config.slippage_pts, note


def market_exit(row, trade: TradeSide, config: OpeningRangeMbpExecutionConfig) -> float:
    if trade == "long":
        return float(row.bid_px) - config.slippage_pts
    return float(row.ask_px) + config.slippage_pts


def pnl_dollars(
    trade: TradeSide,
    entry: float,
    exit_price: float,
    config: OpeningRangeMbpExecutionConfig,
) -> float:
    sign = 1 if trade == "long" else -1
    gross = (exit_price - entry) * sign * config.qty * config.contract_value
    return float(gross - 2 * config.qty * config.commission_per_contract)


def mid(row: pd.Series) -> float:
    return (float(row.bid_px) + float(row.ask_px)) / 2.0


def still_beyond_level(price: float, trade: TradeSide, level: float) -> bool:
    return price >= level if trade == "long" else price <= level


def forced_flat_ts(session_date: str, config: OpeningRangeMbpExecutionConfig) -> dt.datetime:
    date_value = dt.date.fromisoformat(session_date)
    return dt.datetime.combine(date_value, config.rth_close_et, tzinfo=ET).astimezone(dt.UTC)


def attempt_base(event: pd.Series, entry_style: EntryStyle) -> dict[str, object]:
    return {
        "event_id": event["event_id"],
        "session_date": event["session_date"],
        "month": event["month"],
        "is_holdout": bool(event["is_holdout"]),
        "first_break_side": event["first_break_side"],
        "trade_side": event["trade_side"],
        "first_break_ts": event["first_break_ts"],
        "or_high": event["or_high"],
        "or_low": event["or_low"],
        "or_range_pts": event["or_range_pts"],
        "entry_style": entry_style,
        "variant_id": entry_style,
    }


def skip_row(event: pd.Series, entry_style: EntryStyle, reason: str) -> dict[str, object]:
    return {
        **attempt_base(event, entry_style),
        "status": "skipped",
        "skip_reason": reason,
    }
