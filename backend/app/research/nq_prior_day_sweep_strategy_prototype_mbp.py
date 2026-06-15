"""MBP-1 event sequencing for the NQ prior-day sweep prototype study."""

from __future__ import annotations

import datetime as dt
import math

import pandas as pd

from app.research.nq_liquidity_sweep_outcomes_sessions import ET
from app.research.nq_prior_day_sweep_strategy_prototype_setup import strategy_side
from app.research.nq_prior_day_sweep_strategy_prototype_types import (
    EntryMethod,
    PriorDaySweepPrototypeConfig,
    Side,
    StopMethod,
    TargetMethod,
)


def simulate_mbp_variant(
    event: pd.Series,
    mbp1: pd.DataFrame,
    *,
    entry_method: EntryMethod,
    stop_method: StopMethod,
    target_method: TargetMethod,
    config: PriorDaySweepPrototypeConfig,
) -> dict[str, object]:
    side = strategy_side(str(event["sweep_side"]))
    sweep_ts = _to_utc(event["sweep_ts"])
    level = float(event["level_price"])
    entry = _entry(event, mbp1, entry_method, config)
    if entry is None:
        return _skip(event, entry_method, stop_method, target_method, "no_entry")

    entry_ts, entry_price, entry_note = entry
    stop = _stop_price(side, level, entry_price, sweep_ts, entry_ts, mbp1, stop_method, config)
    if stop is None:
        return _skip(event, entry_method, stop_method, target_method, "invalid_stop")
    target = _target_price(side, entry_price, stop, target_method)
    exit_ts, exit_price, exit_reason, confidence = _exit(
        side,
        mbp1,
        entry_ts,
        stop,
        target,
        _forced_flat_ts(event, sweep_ts, config),
        config,
    )
    pnl = _pnl(side, entry_price, exit_price, config)
    risk_pts = abs(entry_price - stop)
    return {
        **_base(event, entry_method, stop_method, target_method),
        "status": "filled",
        "skip_reason": None,
        "entry_note": entry_note,
        "entry_ts": entry_ts,
        "entry_price": entry_price,
        "stop_price": stop,
        "target_price": target,
        "exit_ts": exit_ts,
        "exit_price": exit_price,
        "exit_reason": exit_reason,
        "fill_confidence": confidence,
        "risk_pts": risk_pts,
        "pnl": pnl,
        "r_multiple": pnl / (risk_pts * config.contract_value) if risk_pts > 0 else math.nan,
    }


def _entry(
    event: pd.Series,
    mbp1: pd.DataFrame,
    entry_method: EntryMethod,
    config: PriorDaySweepPrototypeConfig,
) -> tuple[dt.datetime, float, str] | None:
    side = strategy_side(str(event["sweep_side"]))
    sweep_ts = _to_utc(event["sweep_ts"])
    level = float(event["level_price"])
    if entry_method == "immediate_sweep":
        row = _first_valid_quote(mbp1, sweep_ts)
        if row is None:
            return None
        return _quote_entry(row, side, config, "first_quote_after_sweep")
    if entry_method == "delay_30s":
        row = _first_valid_quote(
            mbp1,
            sweep_ts + dt.timedelta(seconds=config.delayed_entry_seconds),
        )
        if row is None or not _still_beyond_level(_mid(row), side, level):
            return None
        return _quote_entry(row, side, config, "30s_delay")
    return _first_retest_entry(event, mbp1, config)


def _first_retest_entry(
    event: pd.Series,
    mbp1: pd.DataFrame,
    config: PriorDaySweepPrototypeConfig,
) -> tuple[dt.datetime, float, str] | None:
    side = strategy_side(str(event["sweep_side"]))
    sweep_ts = _to_utc(event["sweep_ts"])
    level = float(event["level_price"])
    end = sweep_ts + dt.timedelta(minutes=config.retest_deadline_minutes)
    trades = _trades_between(mbp1, sweep_ts, end)
    for row in trades.itertuples(index=False):
        price = float(row.price)
        if side == "long" and price <= level:
            return _row_ts(row), level + config.slippage_pts, "first_level_retest"
        if side == "short" and price >= level:
            return _row_ts(row), level - config.slippage_pts, "first_level_retest"
    return None


def _stop_price(
    side: Side,
    level: float,
    entry: float,
    sweep_ts: dt.datetime,
    entry_ts: dt.datetime,
    mbp1: pd.DataFrame,
    method: StopMethod,
    config: PriorDaySweepPrototypeConfig,
) -> float | None:
    if method == "fixed_8":
        return entry - 8.0 if side == "long" else entry + 8.0
    if method == "level_reversal_8":
        stop = level - 8.0 if side == "long" else level + 8.0
        return stop if abs(entry - stop) > 0 else None
    return _sweep_extreme_stop(side, entry, sweep_ts, entry_ts, mbp1, config)


def _sweep_extreme_stop(
    side: Side,
    entry: float,
    sweep_ts: dt.datetime,
    entry_ts: dt.datetime,
    mbp1: pd.DataFrame,
    config: PriorDaySweepPrototypeConfig,
) -> float | None:
    prices = _trades_between(mbp1, sweep_ts, entry_ts)["price"].dropna().astype(float)
    if prices.empty:
        raw = entry - 8.0 if side == "long" else entry + 8.0
    elif side == "long":
        raw = float(prices.min()) - config.stop_buffer_pts
    else:
        raw = float(prices.max()) + config.stop_buffer_pts
    if abs(entry - raw) < config.min_sweep_extreme_stop_pts:
        raw = (
            entry - config.min_sweep_extreme_stop_pts
            if side == "long"
            else entry + config.min_sweep_extreme_stop_pts
        )
    return None if abs(entry - raw) > config.max_sweep_extreme_stop_pts else raw


def _target_price(side: Side, entry: float, stop: float, method: TargetMethod) -> float:
    if method == "fixed_8":
        return entry + 8.0 if side == "long" else entry - 8.0
    if method == "fixed_12":
        return entry + 12.0 if side == "long" else entry - 12.0
    risk = abs(entry - stop)
    return entry + 1.5 * risk if side == "long" else entry - 1.5 * risk


def _exit(
    side: Side,
    mbp1: pd.DataFrame,
    entry_ts: dt.datetime,
    stop: float,
    target: float,
    forced_flat: dt.datetime,
    config: PriorDaySweepPrototypeConfig,
) -> tuple[dt.datetime, float, str, str]:
    events = mbp1.loc[mbp1.index > pd.Timestamp(entry_ts)]
    last = None
    for row in events.itertuples(index=False):
        last = row
        ts = _row_ts(row)
        if ts >= forced_flat:
            return ts, _market_exit(row, side, config), "forced_flat", "event_sequence"
        if str(row.action) != "T" or pd.isna(row.price):
            continue
        price = float(row.price)
        if side == "long":
            if price <= stop:
                return ts, _stop_fill(side, stop, config), "stop", "event_sequence"
            if price >= target:
                return ts, target, "target", "event_sequence"
        elif price >= stop:
            return ts, _stop_fill(side, stop, config), "stop", "event_sequence"
        elif price <= target:
            return ts, target, "target", "event_sequence"
    if last is not None:
        return _row_ts(last), _market_exit(last, side, config), "forced_flat", "last_event"
    return entry_ts, _fallback_exit(side, stop, target), "forced_flat", "no_events"


def _quote_entry(
    row: pd.Series,
    side: Side,
    config: PriorDaySweepPrototypeConfig,
    note: str,
) -> tuple[dt.datetime, float, str]:
    if side == "long":
        return _row_ts(row), float(row.ask_px) + config.slippage_pts, note
    return _row_ts(row), float(row.bid_px) - config.slippage_pts, note


def _first_valid_quote(mbp1: pd.DataFrame, start: dt.datetime) -> pd.Series | None:
    window = mbp1.loc[mbp1.index >= pd.Timestamp(start)]
    window = window.loc[
        window["bid_px"].notna()
        & window["ask_px"].notna()
        & (window["ask_px"] >= window["bid_px"])
    ]
    return None if window.empty else window.iloc[0]


def _trades_between(mbp1: pd.DataFrame, start: dt.datetime, end: dt.datetime) -> pd.DataFrame:
    window = mbp1.loc[(mbp1.index >= pd.Timestamp(start)) & (mbp1.index <= pd.Timestamp(end))]
    return window.loc[(window["action"] == "T") & window["price"].notna()]


def _market_exit(row, side: Side, config: PriorDaySweepPrototypeConfig) -> float:
    if side == "long":
        return float(row.bid_px) - config.slippage_pts
    return float(row.ask_px) + config.slippage_pts


def _stop_fill(side: Side, stop: float, config: PriorDaySweepPrototypeConfig) -> float:
    return stop - config.slippage_pts if side == "long" else stop + config.slippage_pts


def _fallback_exit(side: Side, stop: float, target: float) -> float:
    return stop if side == "long" else target


def _mid(row) -> float:
    return (float(row.bid_px) + float(row.ask_px)) / 2.0


def _still_beyond_level(price: float, side: Side, level: float) -> bool:
    return price >= level if side == "long" else price <= level


def _forced_flat_ts(
    event: pd.Series,
    sweep_ts: dt.datetime,
    config: PriorDaySweepPrototypeConfig,
) -> dt.datetime:
    session_date = dt.date.fromisoformat(str(event["session_date"]))
    noon = dt.datetime.combine(session_date, config.forced_flat_et, tzinfo=ET).astimezone(dt.UTC)
    return min(noon, sweep_ts + dt.timedelta(minutes=config.max_hold_minutes))


def _pnl(
    side: Side,
    entry: float,
    exit_price: float,
    config: PriorDaySweepPrototypeConfig,
) -> float:
    sign = 1 if side == "long" else -1
    gross = (exit_price - entry) * sign * config.qty * config.contract_value
    return float(gross - 2 * config.qty * config.commission_per_contract)


def _skip(
    event: pd.Series,
    entry_method: EntryMethod,
    stop_method: StopMethod,
    target_method: TargetMethod,
    reason: str,
) -> dict[str, object]:
    return {
        **_base(event, entry_method, stop_method, target_method),
        "status": "skipped",
        "skip_reason": reason,
    }


def _base(
    event: pd.Series,
    entry_method: EntryMethod,
    stop_method: StopMethod,
    target_method: TargetMethod,
) -> dict[str, object]:
    return {
        "event_id": event["event_id"],
        "session_date": event["session_date"],
        "month": event["month"],
        "level_type": event["level_type"],
        "sweep_side": event["sweep_side"],
        "trade_side": event["trade_side"],
        "sweep_ts": event["sweep_ts"],
        "level_price": event["level_price"],
        "sweep_price": event["sweep_price"],
        "context_score": event["context_score"],
        "overnight_location_aligned": event["overnight_location_aligned"],
        "rth_gap_aligned": event["rth_gap_aligned"],
        "opening_drive_aligned": event["opening_drive_aligned"],
        "entry_method": entry_method,
        "stop_method": stop_method,
        "target_method": target_method,
        "variant_id": f"{entry_method}__{stop_method}__{target_method}",
    }


def _row_ts(row) -> dt.datetime:
    if hasattr(row, "ts_event"):
        return _to_utc(row.ts_event)
    if isinstance(row, pd.Series) and "ts_event" in row:
        return _to_utc(row["ts_event"])
    return _to_utc(row.name)


def _to_utc(value: object) -> dt.datetime:
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    else:
        ts = ts.tz_convert("UTC")
    return ts.to_pydatetime(warn=False)
