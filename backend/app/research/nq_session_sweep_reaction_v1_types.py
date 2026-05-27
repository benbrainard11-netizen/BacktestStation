"""Types for the NQ Session Sweep Reaction V1 backtest."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Literal

Side = Literal["long", "short"]
SweepSide = Literal["high", "low"]


@dataclass(frozen=True)
class SweepReactionConfig:
    """Locked V1 parameters and execution assumptions."""

    symbol: str = "NQ.c.0"
    tick_size: float = 0.25
    contract_value: float = 20.0
    qty: int = 1
    initial_equity: float = 25_000.0
    commission_per_contract: float = 2.0
    slippage_ticks: int = 1
    sweep_buffer_pts: float = 0.25
    entry_start_et: dt.time = dt.time(9, 35)
    sweep_cutoff_et: dt.time = dt.time(10, 30)
    entry_deadline_et: dt.time = dt.time(10, 45)
    forced_flat_et: dt.time = dt.time(12, 0)
    mbp_confirmation_seconds: int = 30
    short_imbalance_threshold: float = -0.20
    long_imbalance_threshold: float = 0.20
    reclaim_deadline_minutes: int = 10
    stop_buffer_pts: float = 0.50
    min_stop_pts: float = 6.0
    max_stop_pts: float = 30.0
    target_r: float = 1.50
    prior_range_lookback: int = 20
    prior_range_min_sessions: int = 10
    min_range_frac_of_prior_median: float = 0.50
    max_range_frac_of_prior_median: float = 1.75


@dataclass(frozen=True)
class SweepEvent:
    side: SweepSide
    ts: dt.datetime
    price: float
    bid_px: float
    ask_px: float


@dataclass(frozen=True)
class TradePlan:
    session_date: str
    next_session_date: str
    armed_side: SweepSide
    trade_side: Side
    anchor_high: float
    anchor_low: float
    anchor_range: float
    session_close_position: float
    session_close_bias: str
    prior20_median_range: float | None


@dataclass(frozen=True)
class SimulatedTrade:
    trade_id: str
    session_date: str
    next_session_date: str
    side: Side
    qty: int
    entry_ts: dt.datetime
    exit_ts: dt.datetime
    entry_price: float
    exit_price: float
    stop_price: float
    target_price: float
    risk_pts: float
    pnl: float
    r_multiple: float
    exit_reason: str
    fill_confidence: str
    sweep_side: SweepSide
    sweep_ts: dt.datetime
    sweep_price: float
    sweep_extreme: float
    reclaim_bar_start: dt.datetime
    reclaim_bar_end: dt.datetime
    confirmation_end: dt.datetime
    post_sweep_30s_mean_imbalance: float
    anchor_high: float
    anchor_low: float
    anchor_range: float
    session_close_position: float
    session_close_bias: str
    prior20_median_range: float | None
