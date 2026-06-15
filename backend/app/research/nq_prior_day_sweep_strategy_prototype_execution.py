"""Execution simulation for the NQ prior-day sweep prototype study."""

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


def simulate_bar_variant(
    event: pd.Series,
    bars: pd.DataFrame,
    *,
    entry_method: EntryMethod,
    stop_method: StopMethod,
    target_method: TargetMethod,
    config: PriorDaySweepPrototypeConfig,
) -> dict[str, object]:
    side = strategy_side(str(event["sweep_side"]))
    sweep_ts = _to_utc(event["sweep_ts"])
    level = float(event["level_price"])
    entry = _bar_entry(event, bars, entry_method, config)
    if entry is None:
        return _skip(event, entry_method, stop_method, target_method, "no_entry")

    entry_ts, entry_price, entry_note = entry
    stop = _stop_price(
        side,
        level,
        entry_price,
        sweep_ts,
        entry_ts,
        bars,
        stop_method,
        config,
    )
    if stop is None:
        return _skip(event, entry_method, stop_method, target_method, "invalid_stop")
    target = _target_price(side, entry_price, stop, target_method)
    exit_ts, exit_price, exit_reason, confidence = _bar_exit(
        side,
        bars,
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


def _bar_entry(
    event: pd.Series,
    bars: pd.DataFrame,
    entry_method: EntryMethod,
    config: PriorDaySweepPrototypeConfig,
) -> tuple[dt.datetime, float, str] | None:
    side = strategy_side(str(event["sweep_side"]))
    sweep_ts = _to_utc(event["sweep_ts"])
    level = float(event["level_price"])
    if entry_method == "immediate_sweep":
        ts = _next_complete_minute(sweep_ts)
        row = _first_bar_at_or_after(bars, ts)
        if row is None:
            return None
        return _timestamp(row.name), _market_entry_price(row["open"], side, config), "next_bar_open"
    if entry_method == "delay_30s":
        ts = _next_complete_minute(sweep_ts + dt.timedelta(seconds=config.delayed_entry_seconds))
        row = _first_bar_at_or_after(bars, ts)
        if row is None or not _still_beyond_level(float(row["open"]), side, level):
            return None
        return _timestamp(row.name), _market_entry_price(row["open"], side, config), "30s_delay"
    return _first_retest_entry(event, bars, config)


def _first_retest_entry(
    event: pd.Series,
    bars: pd.DataFrame,
    config: PriorDaySweepPrototypeConfig,
) -> tuple[dt.datetime, float, str] | None:
    side = strategy_side(str(event["sweep_side"]))
    sweep_ts = _to_utc(event["sweep_ts"])
    level = float(event["level_price"])
    start = _next_complete_minute(sweep_ts)
    end = sweep_ts + dt.timedelta(minutes=config.retest_deadline_minutes)
    window = bars.loc[(bars.index >= pd.Timestamp(start)) & (bars.index <= pd.Timestamp(end))]
    for ts, row in window.iterrows():
        if side == "long" and float(row["low"]) <= level:
            return _timestamp(ts), level + config.slippage_pts, "first_level_retest"
        if side == "short" and float(row["high"]) >= level:
            return _timestamp(ts), level - config.slippage_pts, "first_level_retest"
    return None


def _stop_price(
    side: Side,
    level: float,
    entry: float,
    sweep_ts: dt.datetime,
    entry_ts: dt.datetime,
    bars: pd.DataFrame,
    method: StopMethod,
    config: PriorDaySweepPrototypeConfig,
) -> float | None:
    if method == "fixed_8":
        return entry - 8.0 if side == "long" else entry + 8.0
    if method == "level_reversal_8":
        stop = level - 8.0 if side == "long" else level + 8.0
        return stop if abs(entry - stop) > 0 else None
    return _sweep_extreme_stop(side, entry, sweep_ts, entry_ts, bars, config)


def _sweep_extreme_stop(
    side: Side,
    entry: float,
    sweep_ts: dt.datetime,
    entry_ts: dt.datetime,
    bars: pd.DataFrame,
    config: PriorDaySweepPrototypeConfig,
) -> float | None:
    window = bars.loc[
        (bars.index >= pd.Timestamp(sweep_ts)) & (bars.index <= pd.Timestamp(entry_ts))
    ]
    if window.empty:
        raw = entry - 8.0 if side == "long" else entry + 8.0
    elif side == "long":
        raw = float(window["low"].min()) - config.stop_buffer_pts
    else:
        raw = float(window["high"].max()) + config.stop_buffer_pts
    risk = abs(entry - raw)
    if risk < config.min_sweep_extreme_stop_pts:
        raw = (
            entry - config.min_sweep_extreme_stop_pts
            if side == "long"
            else entry + config.min_sweep_extreme_stop_pts
        )
    if abs(entry - raw) > config.max_sweep_extreme_stop_pts:
        return None
    return raw


def _target_price(
    side: Side,
    entry: float,
    stop: float,
    method: TargetMethod,
) -> float:
    if method == "fixed_8":
        return entry + 8.0 if side == "long" else entry - 8.0
    if method == "fixed_12":
        return entry + 12.0 if side == "long" else entry - 12.0
    risk = abs(entry - stop)
    return entry + 1.5 * risk if side == "long" else entry - 1.5 * risk


def _bar_exit(
    side: Side,
    bars: pd.DataFrame,
    entry_ts: dt.datetime,
    stop: float,
    target: float,
    forced_flat: dt.datetime,
    config: PriorDaySweepPrototypeConfig,
) -> tuple[dt.datetime, float, str, str]:
    window = bars.loc[
        (bars.index >= pd.Timestamp(entry_ts)) & (bars.index <= pd.Timestamp(forced_flat))
    ]
    last_ts, last_close = entry_ts, math.nan
    for ts, row in window.iterrows():
        last_ts, last_close = _timestamp(ts), float(row["close"])
        stop_hit, target_hit = _bar_hits(side, row, stop, target)
        if stop_hit and target_hit:
            return last_ts, _stop_fill(side, stop, config), "stop", "same_bar_stop_first"
        if stop_hit:
            return last_ts, _stop_fill(side, stop, config), "stop", "bar_sequence"
        if target_hit:
            return last_ts, target, "target", "bar_sequence"
    if not math.isfinite(last_close):
        row = bars.iloc[-1]
        last_ts, last_close = _timestamp(row.name), float(row["close"])
    return last_ts, _market_exit_price(last_close, side, config), "forced_flat", "bar_close"


def _bar_hits(side: Side, row: pd.Series, stop: float, target: float) -> tuple[bool, bool]:
    if side == "long":
        return float(row["low"]) <= stop, float(row["high"]) >= target
    return float(row["high"]) >= stop, float(row["low"]) <= target


def _market_entry_price(price: float, side: Side, config: PriorDaySweepPrototypeConfig) -> float:
    if side == "long":
        return float(price) + config.slippage_pts
    return float(price) - config.slippage_pts


def _market_exit_price(price: float, side: Side, config: PriorDaySweepPrototypeConfig) -> float:
    if side == "long":
        return float(price) - config.slippage_pts
    return float(price) + config.slippage_pts


def _stop_fill(side: Side, stop: float, config: PriorDaySweepPrototypeConfig) -> float:
    return stop - config.slippage_pts if side == "long" else stop + config.slippage_pts


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


def _first_bar_at_or_after(bars: pd.DataFrame, ts: dt.datetime) -> pd.Series | None:
    window = bars.loc[bars.index >= pd.Timestamp(ts)]
    return None if window.empty else window.iloc[0]


def _next_complete_minute(value: dt.datetime) -> dt.datetime:
    ts = pd.Timestamp(value)
    floored = ts.floor("min")
    if ts == floored:
        return ts.to_pydatetime(warn=False)
    return (floored + pd.Timedelta(minutes=1)).to_pydatetime(warn=False)


def _timestamp(value: object) -> dt.datetime:
    return _to_utc(value)


def _to_utc(value: object) -> dt.datetime:
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    else:
        ts = ts.tz_convert("UTC")
    return ts.to_pydatetime(warn=False)
