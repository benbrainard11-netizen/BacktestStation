"""Paper execution helpers for the frozen OR-high monitor."""

from __future__ import annotations

import datetime as dt

import pandas as pd

from app.research.nq_liquidity_sweep_outcomes_sessions import et_datetime
from app.research.nq_opening_range_mbp_execution_fills import (
    first_valid_quote,
    mid,
    pnl_dollars,
    quote_entry,
)
from app.research.nq_opening_range_mbp_execution_types import (
    EntryStyle,
    OpeningRangeMbpExecutionConfig,
    TradeSide,
)
from app.research.nq_opening_range_mbp_execution_utils import row_ts, trade_rows
from app.research.nq_or_high_middle_third_paper_types import PaperMonitorConfig


def position_for_style(
    context: dict[str, object],
    mbp1: pd.DataFrame,
    entry_style: EntryStyle,
    cfg: PaperMonitorConfig,
    now_utc: dt.datetime,
) -> dict[str, object]:
    break_ts = to_utc(context["first_break_ts"])
    entry = entry_for_style_live(context, mbp1, entry_style, cfg.execution, now_utc)
    base = {
        "paper_trade_id": f"{context['event_id']}:{entry_style}",
        "event_id": context["event_id"],
        "session_date": context["session_date"],
        "symbol": context["symbol"],
        "entry_style": entry_style,
        "variant_id": entry_style,
        "trade_side": "long",
        "first_break_ts": break_ts,
        "first_break_price": context["first_break_price"],
        "or_high": context["or_high"],
        "or_low": context["or_low"],
        "or_range_pts": context["or_range_pts"],
        "target_price": float(context["or_high"]) + float(context["or_range_pts"]),
        "stop_price": float(context["or_low"]),
    }
    if entry is None:
        return base | {"status": pending_status(entry_style, break_ts, cfg.execution, now_utc)}
    entry_ts, entry_price, note = entry
    exit_state = exit_or_open(mbp1, "long", entry_ts, entry_price, base, cfg.execution, now_utc)
    return base | {
        "status": exit_state["status"],
        "entry_note": note,
        "entry_ts": entry_ts,
        "entry_price": entry_price,
        "risk_pts": abs(entry_price - float(base["stop_price"])),
        **exit_state,
    }


def entry_for_style_live(
    context: dict[str, object],
    mbp1: pd.DataFrame,
    entry_style: EntryStyle,
    config: OpeningRangeMbpExecutionConfig,
    now_utc: dt.datetime,
) -> tuple[dt.datetime, float, str] | None:
    break_ts = to_utc(context["first_break_ts"])
    level = float(context["or_high"])
    if entry_style == "immediate_break":
        row = first_valid_quote(mbp1, break_ts)
        return quote_entry(row, "long", config, "first_quote_after_break") if row is not None else None
    if entry_style == "confirmation_30s":
        confirm_ts = break_ts + dt.timedelta(seconds=config.confirmation_seconds)
        if now_utc < confirm_ts:
            return None
        row = first_valid_quote(mbp1, confirm_ts)
        if row is None or mid(row) < level:
            return None
        return quote_entry(row, "long", config, "30s_confirmation")
    return first_retest_entry(context, mbp1, config, break_ts, level)


def first_retest_entry(
    context: dict[str, object],
    mbp1: pd.DataFrame,
    config: OpeningRangeMbpExecutionConfig,
    break_ts: dt.datetime,
    level: float,
) -> tuple[dt.datetime, float, str] | None:
    end = break_ts + dt.timedelta(minutes=config.retest_deadline_minutes)
    retest_window = mbp1.loc[(mbp1.index >= break_ts) & (mbp1.index <= end)]
    for row in trade_rows(retest_window).itertuples(index=False):
        if float(row.price) <= level:
            return row_ts(row), level + config.slippage_pts, "first_level_retest"
    return None


def pending_status(
    entry_style: EntryStyle,
    break_ts: dt.datetime,
    config: OpeningRangeMbpExecutionConfig,
    now_utc: dt.datetime,
) -> str:
    if entry_style == "confirmation_30s":
        confirm_ts = break_ts + dt.timedelta(seconds=config.confirmation_seconds)
        return "pending_entry" if now_utc < confirm_ts else "skipped_no_entry"
    if entry_style == "first_retest":
        deadline = break_ts + dt.timedelta(minutes=config.retest_deadline_minutes)
        return "pending_entry" if now_utc <= deadline else "skipped_no_entry"
    return "skipped_no_entry"


def exit_or_open(
    mbp1: pd.DataFrame,
    trade: TradeSide,
    entry_ts: dt.datetime,
    entry_price: float,
    position: dict[str, object],
    config: OpeningRangeMbpExecutionConfig,
    now_utc: dt.datetime,
) -> dict[str, object]:
    stop = float(position["stop_price"])
    target = float(position["target_price"])
    session = dt.date.fromisoformat(str(position["session_date"]))
    forced_flat = et_datetime(session, config.rth_close_et)
    last_quote = None
    for row in mbp1.loc[mbp1.index > pd.Timestamp(entry_ts)].itertuples(index=False):
        ts = row_ts(row)
        if pd.notna(row.bid_px) and pd.notna(row.ask_px):
            last_quote = row
        if ts >= forced_flat:
            return closed_state(trade, entry_price, row, "forced_flat", config)
        if str(row.action) == "T" and pd.notna(row.price):
            price = float(row.price)
            if price <= stop:
                return priced_close(trade, entry_price, ts, stop - config.slippage_pts, "stop", config)
            if price >= target:
                return priced_close(trade, entry_price, ts, target, "target", config)
    if now_utc >= forced_flat and last_quote is not None:
        return closed_state(trade, entry_price, last_quote, "forced_flat", config)
    return open_state(trade, entry_price, last_quote, config)


def open_state(
    trade: TradeSide,
    entry_price: float,
    quote_row: object | None,
    config: OpeningRangeMbpExecutionConfig,
) -> dict[str, object]:
    mark = entry_price if quote_row is None else mark_exit_price(quote_row, trade, config)
    pnl = pnl_dollars(trade, entry_price, mark, config)
    return {
        "status": "open",
        "mark_price": mark,
        "unrealized_pnl": pnl,
        "realized_pnl": 0.0,
        "pnl": pnl,
        "exit_reason": None,
    }


def closed_state(
    trade: TradeSide,
    entry_price: float,
    row: object,
    reason: str,
    config: OpeningRangeMbpExecutionConfig,
) -> dict[str, object]:
    return priced_close(trade, entry_price, row_ts(row), mark_exit_price(row, trade, config), reason, config)


def priced_close(
    trade: TradeSide,
    entry_price: float,
    ts: dt.datetime,
    price: float,
    reason: str,
    config: OpeningRangeMbpExecutionConfig,
) -> dict[str, object]:
    pnl = pnl_dollars(trade, entry_price, price, config)
    return {
        "status": "closed",
        "exit_ts": ts,
        "exit_price": price,
        "exit_reason": reason,
        "realized_pnl": pnl,
        "unrealized_pnl": 0.0,
        "pnl": pnl,
    }


def mark_exit_price(
    row: object,
    trade: TradeSide,
    config: OpeningRangeMbpExecutionConfig,
) -> float:
    if trade == "long":
        return float(row.bid_px) - config.slippage_pts
    return float(row.ask_px) + config.slippage_pts


def to_utc(value: object) -> dt.datetime:
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        return ts.tz_localize("UTC").to_pydatetime()
    return ts.tz_convert("UTC").to_pydatetime()
