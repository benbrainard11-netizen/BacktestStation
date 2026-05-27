"""Execution simulation helpers for NQ Session Sweep Reaction V1."""

from __future__ import annotations

import datetime as dt

import pandas as pd

from app.research.nq_session_sweep_reaction_v1_types import (
    Side,
    SweepReactionConfig,
)
from app.research.nq_session_sweep_reaction_v1_utils import (
    row_ts,
    to_datetime,
    trade_events_between,
)


def build_stop_target(
    *,
    trade_side: Side,
    entry_price: float,
    sweep_ts: dt.datetime,
    entry_ts: dt.datetime,
    mbp1: pd.DataFrame,
    config: SweepReactionConfig,
) -> tuple[float, float, float, float] | None:
    trades = trade_events_between(mbp1, sweep_ts, entry_ts, inclusive_end=True)
    if trades.empty:
        return None
    prices = pd.to_numeric(trades["price"], errors="coerce").dropna()
    if prices.empty:
        return None
    if trade_side == "short":
        extreme = float(prices.max())
        stop = extreme + config.stop_buffer_pts
        if stop - entry_price < config.min_stop_pts:
            stop = entry_price + config.min_stop_pts
        risk = stop - entry_price
        target = entry_price - config.target_r * risk
    else:
        extreme = float(prices.min())
        stop = extreme - config.stop_buffer_pts
        if entry_price - stop < config.min_stop_pts:
            stop = entry_price - config.min_stop_pts
        risk = entry_price - stop
        target = entry_price + config.target_r * risk
    return float(stop), float(target), float(risk), extreme


def simulate_exit(
    mbp1: pd.DataFrame,
    *,
    trade_side: Side,
    entry_ts: dt.datetime,
    stop_price: float,
    target_price: float,
    forced_flat: dt.datetime,
    config: SweepReactionConfig,
) -> tuple[dt.datetime, float, str, str] | None:
    events = mbp1.loc[mbp1.index > pd.Timestamp(entry_ts)].copy()
    if events.empty:
        return None
    for row in events.itertuples(index=False):
        ts = row_ts(row)
        if ts >= forced_flat:
            price = exit_market_price(row, trade_side, config)
            return ts, price, "forced_flat", "exact"
        if str(row.action) != "T" or pd.isna(row.price):
            continue
        trade_price = float(row.price)
        if trade_side == "long":
            if trade_price <= stop_price:
                price = exit_market_price(row, trade_side, config)
                return ts, price, "stop", "exact"
            if trade_price >= target_price:
                return ts, target_price, "target", "exact"
        else:
            if trade_price >= stop_price:
                price = exit_market_price(row, trade_side, config)
                return ts, price, "stop", "exact"
            if trade_price <= target_price:
                return ts, target_price, "target", "exact"
    last = events.iloc[-1]
    return (
        to_datetime(last.name),
        exit_market_price(last, trade_side, config),
        "forced_flat",
        "ambiguous",
    )


def entry_price(row, side: Side, config: SweepReactionConfig) -> float:
    slippage = config.slippage_ticks * config.tick_size
    if side == "long":
        return float(row.ask_px) + slippage
    return float(row.bid_px) - slippage


def exit_market_price(row, trade_side: Side, config: SweepReactionConfig) -> float:
    slippage = config.slippage_ticks * config.tick_size
    if trade_side == "long":
        return float(row.bid_px) - slippage
    return float(row.ask_px) + slippage


def pnl(
    *,
    side: Side,
    entry_price: float,
    exit_price: float,
    qty: int,
    contract_value: float,
    commission_per_contract: float,
) -> float:
    sign = 1 if side == "long" else -1
    gross = (exit_price - entry_price) * sign * qty * contract_value
    commissions = 2 * qty * commission_per_contract
    return float(gross - commissions)
