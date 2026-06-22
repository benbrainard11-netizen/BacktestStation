"""Shadow paper monitor for the frozen OR-high middle-third prototype."""

from __future__ import annotations

import datetime as dt
import math

import pandas as pd

from app.data.reader import read_bars
from app.research.nq_liquidity_sweep_outcomes_sessions import ET, et_datetime, normalize_bars
from app.research.nq_opening_range_descriptive_build import OR_END_ET, OR_START_ET, window
from app.research.nq_opening_range_mbp_execution import MbpWindowLoader
from app.research.nq_opening_range_mbp_execution_sequence import first_break
from app.research.nq_opening_range_mbp_execution_types import ENTRY_STYLES, EntryStyle
from app.research.nq_or_high_middle_third_forward import FROZEN_COMMIT, PROTOTYPE_ID
from app.research.nq_or_high_middle_third_paper_execution import position_for_style
from app.research.nq_or_high_middle_third_paper_io import config_json, write_outputs
from app.research.nq_or_high_middle_third_paper_types import (
    DEFAULT_OUTPUT_DIR,
    PaperMonitorConfig,
)


def run_paper_monitor_once(
    *,
    config: PaperMonitorConfig | None = None,
    session_date: str | dt.date | None = None,
    now: dt.datetime | None = None,
) -> dict[str, object]:
    cfg = config or PaperMonitorConfig()
    now_utc = utc_now(now)
    session = date_value(session_date) if session_date is not None else now_utc.astimezone(ET).date()
    try:
        context = load_or_context(cfg, session, now_utc)
        mbp1 = load_live_mbp_window(cfg, session, now_utc) if context else pd.DataFrame()
        snapshot = evaluate_snapshot(
            cfg,
            session,
            now_utc,
            context,
            mbp1,
            missing_context_state=missing_context_state(session, now_utc),
        )
    except Exception as exc:
        snapshot = error_snapshot(cfg, session, now_utc, exc)
    write_outputs(snapshot, cfg)
    return snapshot


def load_or_context(
    cfg: PaperMonitorConfig,
    session_date: dt.date,
    now_utc: dt.datetime,
) -> dict[str, object] | None:
    bars = read_bars(
        symbol=cfg.symbol,
        timeframe="1m",
        start=session_date - dt.timedelta(days=10),
        end=session_date + dt.timedelta(days=1),
    )
    df = normalize_bars(bars)
    or_start = et_datetime(session_date, OR_START_ET)
    or_end = et_datetime(session_date, OR_END_ET)
    opening = window(df, or_start, min_dt(or_end, now_utc))
    if opening.empty or now_utc < or_end:
        return None
    or_open = float(opening["open"].iloc[0])
    or_high = float(opening["high"].max())
    or_low = float(opening["low"].min())
    or_close = float(opening["close"].iloc[-1])
    or_range = or_high - or_low
    close_position = (or_close - or_low) / or_range if or_range > 0 else math.nan
    return {
        "event_id": f"paper_or_high_middle_third:{session_date.isoformat()}",
        "prototype_id": PROTOTYPE_ID,
        "frozen_rules_commit": FROZEN_COMMIT,
        "symbol": cfg.symbol,
        "session_date": session_date.isoformat(),
        "or_open": or_open,
        "or_high": or_high,
        "or_low": or_low,
        "or_close": or_close,
        "or_range_pts": or_range,
        "opening_drive_close_position": close_position,
        "opening_drive_close_bucket": close_bucket(close_position),
        "opening_range_complete": True,
        "opening_range_bar_count": int(len(opening)),
    }


def load_live_mbp_window(
    cfg: PaperMonitorConfig,
    session_date: dt.date,
    now_utc: dt.datetime,
) -> pd.DataFrame:
    start = et_datetime(session_date, OR_END_ET)
    end = min_dt(et_datetime(session_date, cfg.execution.rth_close_et), now_utc)
    if end <= start:
        return pd.DataFrame()
    return MbpWindowLoader(cfg.symbol).load_window(session_date, start, end)


def evaluate_snapshot(
    cfg: PaperMonitorConfig,
    session_date: dt.date,
    now_utc: dt.datetime,
    context: dict[str, object] | None,
    mbp1: pd.DataFrame,
    missing_context_state: str = "waiting_for_opening_range",
) -> dict[str, object]:
    if context is None:
        return base_snapshot(cfg, session_date, now_utc, missing_context_state, [], [])
    if context["opening_drive_close_bucket"] != "middle_third":
        return base_snapshot(cfg, session_date, now_utc, "stand_down_not_middle_third", [], [context])
    if mbp1.empty:
        return base_snapshot(cfg, session_date, now_utc, "waiting_for_mbp_data", [], [context])

    first = first_break(mbp1, float(context["or_high"]), float(context["or_low"]))
    if first is None:
        return base_snapshot(cfg, session_date, now_utc, "waiting_for_or_high_break", [], [context])
    side, break_ts, break_price = first
    context = context | {
        "first_break_side": side,
        "first_break_ts": break_ts,
        "first_break_price": break_price,
    }
    if side != "high":
        return base_snapshot(cfg, session_date, now_utc, "stand_down_first_break_low", [], [context])

    positions = [position_for_style(context, mbp1, style, cfg, now_utc) for style in ENTRY_STYLES]
    primary = primary_position(positions, cfg.primary_entry_style)
    status = str(primary["status"]) if primary else "or_high_break_detected"
    snapshot = base_snapshot(cfg, session_date, now_utc, f"paper_{status}", positions, [context])
    snapshot["signals"] = signal_rows(context, positions)
    snapshot["last_signal"] = primary_signal(primary, context) if primary else signal_from_context(context)
    return snapshot


def base_snapshot(
    cfg: PaperMonitorConfig,
    session_date: dt.date,
    now_utc: dt.datetime,
    state: str,
    positions: list[dict[str, object]],
    contexts: list[dict[str, object]],
) -> dict[str, object]:
    primary = primary_position(positions, cfg.primary_entry_style)
    pnl = float(primary.get("pnl", 0.0)) if primary else 0.0
    risk_pts = float(primary.get("risk_pts", 0.0) or 0.0) if primary else 0.0
    risk = risk_pts * cfg.execution.contract_value
    return {
        "prototype_id": PROTOTYPE_ID,
        "frozen_rules_commit": FROZEN_COMMIT,
        "mode": "shadow_paper_no_broker_orders",
        "state": state,
        "last_heartbeat": now_utc,
        "symbol": cfg.symbol,
        "session_date": session_date.isoformat(),
        "primary_entry_style": cfg.primary_entry_style,
        "positions": positions,
        "contexts": contexts,
        "signals": [],
        "paper_account": {
            "today_pnl": pnl,
            "today_r": pnl / risk if risk else 0.0,
            "trades_today": int(primary is not None and primary.get("status") in {"open", "closed"}),
        },
        "config": config_json(cfg),
    }


def signal_rows(context: dict[str, object], positions: list[dict[str, object]]) -> list[dict[str, object]]:
    rows = [signal_from_context(context)]
    for pos in positions:
        if pos.get("entry_ts") is not None:
            rows.append(primary_signal(pos, context))
    return rows


def signal_from_context(context: dict[str, object]) -> dict[str, object]:
    return {
        "signal_id": f"{context['event_id']}:or_high_break",
        "ts": context.get("first_break_ts"),
        "side": "long",
        "price": context.get("first_break_price"),
        "reason": "OR-high middle-third first break detected",
        "executed": False,
    }


def primary_signal(position: dict[str, object], context: dict[str, object]) -> dict[str, object]:
    return {
        "signal_id": f"{position['paper_trade_id']}:entry",
        "ts": position.get("entry_ts") or context.get("first_break_ts"),
        "side": "long",
        "price": position.get("entry_price") or context.get("first_break_price"),
        "reason": f"Shadow paper {position['entry_style']} entry for frozen OR-high middle-third",
        "executed": position.get("status") in {"open", "closed"},
    }


def error_snapshot(
    cfg: PaperMonitorConfig,
    session_date: dt.date,
    now_utc: dt.datetime,
    exc: Exception,
) -> dict[str, object]:
    snap = base_snapshot(cfg, session_date, now_utc, "error", [], [])
    return snap | {"last_error": f"{type(exc).__name__}: {exc}"}


def primary_position(
    positions: list[dict[str, object]],
    style: EntryStyle,
) -> dict[str, object] | None:
    return next((row for row in positions if row.get("entry_style") == style), None)


def close_bucket(value: float) -> str:
    if not math.isfinite(value):
        return "unknown"
    if value <= 1 / 3:
        return "lower_third"
    if value <= 2 / 3:
        return "middle_third"
    return "upper_third"


def min_dt(a: dt.datetime, b: dt.datetime) -> dt.datetime:
    return a if a <= b else b


def missing_context_state(session_date: dt.date, now_utc: dt.datetime) -> str:
    if now_utc < et_datetime(session_date, OR_END_ET):
        return "waiting_for_opening_range"
    return "waiting_for_opening_range_data"


def utc_now(value: dt.datetime | None) -> dt.datetime:
    out = value or dt.datetime.now(dt.UTC)
    return out.replace(tzinfo=dt.UTC) if out.tzinfo is None else out.astimezone(dt.UTC)


def date_value(value: str | dt.date) -> dt.date:
    return value if isinstance(value, dt.date) else dt.date.fromisoformat(value)
