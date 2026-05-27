"""Detection helpers for NQ Session Sweep Reaction V1."""

from __future__ import annotations

import datetime as dt
import math

import pandas as pd

from app.research.final_15m_session_close import (
    close_bias,
    close_position,
    next_globex_day,
)
from app.research.nq_session_sweep_reaction_v1_types import (
    SweepEvent,
    SweepReactionConfig,
    TradePlan,
)
from app.research.nq_session_sweep_reaction_v1_utils import (
    ET,
    events_between,
    row_ts,
    to_datetime,
    trade_events_between,
)


def build_trade_plan(
    session,
    prior_median: float | None,
    config: SweepReactionConfig,
) -> TradePlan | None:
    position = close_position(session.close, session.high, session.low)
    bias = close_bias(position)
    if position is None or bias not in {"bullish", "bearish"}:
        return None
    if not range_sanity_passes(session.range_pts, prior_median, config):
        return None
    next_period = next_globex_day(session.period)
    next_label = next_period.end_utc.astimezone(ET).date()
    armed_side = "high" if bias == "bullish" else "low"
    trade_side = "short" if armed_side == "high" else "long"
    return TradePlan(
        session_date=session.label_date.isoformat(),
        next_session_date=next_label.isoformat(),
        armed_side=armed_side,
        trade_side=trade_side,
        anchor_high=session.high,
        anchor_low=session.low,
        anchor_range=session.range_pts,
        session_close_position=float(position),
        session_close_bias=bias,
        prior20_median_range=prior_median,
    )


def plan_skip_reason(
    session,
    prior_median: float | None,
    config: SweepReactionConfig,
) -> str:
    position = close_position(session.close, session.high, session.low)
    bias = close_bias(position)
    if position is None:
        return "invalid_session_range"
    if bias == "neutral":
        return "neutral_session_bias"
    if bias == "undefined":
        return "undefined_session_bias"
    if not range_sanity_passes(session.range_pts, prior_median, config):
        if prior_median is None:
            return "prior_range_unavailable"
        return "range_sanity_failed"
    return "not_armed"


def range_sanity_passes(
    session_range: float,
    prior_median: float | None,
    config: SweepReactionConfig,
) -> bool:
    if not math.isfinite(session_range) or session_range <= 0:
        return False
    if config.prior_range_min_sessions <= 0:
        return True
    if prior_median is None or prior_median <= 0:
        return False
    return (
        session_range >= config.min_range_frac_of_prior_median * prior_median
        and session_range <= config.max_range_frac_of_prior_median * prior_median
    )


def prior_range_median(
    prior_ranges: list[float],
    config: SweepReactionConfig,
) -> float | None:
    if config.prior_range_min_sessions <= 0:
        return None
    lookback = prior_ranges[-config.prior_range_lookback :]
    if len(lookback) < config.prior_range_min_sessions:
        return None
    return float(pd.Series(lookback).median())


def first_sweep(
    trade_events: pd.DataFrame,
    *,
    anchor_high: float,
    anchor_low: float,
    buffer_pts: float,
) -> SweepEvent | None:
    if trade_events.empty:
        return None
    high_trigger = anchor_high + buffer_pts
    low_trigger = anchor_low - buffer_pts
    for row in trade_events.itertuples(index=False):
        price = float(row.price)
        if price >= high_trigger:
            return SweepEvent(
                "high",
                row_ts(row),
                price,
                float(row.bid_px),
                float(row.ask_px),
            )
        if price <= low_trigger:
            return SweepEvent(
                "low",
                row_ts(row),
                price,
                float(row.bid_px),
                float(row.ask_px),
            )
    return None


def mean_imbalance(
    mbp1: pd.DataFrame,
    start_utc: dt.datetime,
    end_utc: dt.datetime,
) -> float | None:
    window = events_between(mbp1, start_utc, end_utc, inclusive_end=True)
    if window.empty:
        return None
    bid = pd.to_numeric(window["bid_sz"], errors="coerce").astype("float64")
    ask = pd.to_numeric(window["ask_sz"], errors="coerce").astype("float64")
    total = bid + ask
    values = ((bid - ask) / total.where(total > 0)).dropna()
    if values.empty:
        return None
    return float(values.mean())


def find_reclaim_bar(
    bars: pd.DataFrame,
    *,
    plan: TradePlan,
    confirmation_end: dt.datetime,
    sweep_ts: dt.datetime,
    entry_deadline: dt.datetime,
    config: SweepReactionConfig,
) -> tuple[dt.datetime, dt.datetime, float] | None:
    deadline = min(
        sweep_ts + dt.timedelta(minutes=config.reclaim_deadline_minutes),
        entry_deadline,
    )
    window = bars.loc[
        (bars.index + pd.Timedelta(minutes=1) > pd.Timestamp(confirmation_end))
        & (bars.index + pd.Timedelta(minutes=1) <= pd.Timestamp(deadline))
    ]
    for ts, bar in window.iterrows():
        close = float(bar["close"])
        bar_start = to_datetime(ts)
        bar_end = bar_start + dt.timedelta(minutes=1)
        if plan.trade_side == "short" and close <= plan.anchor_high:
            return bar_start, bar_end, close
        if plan.trade_side == "long" and close >= plan.anchor_low:
            return bar_start, bar_end, close
    return None


def trade_events_for_sweeps(
    mbp1: pd.DataFrame,
    start_utc: dt.datetime,
    cutoff_utc: dt.datetime,
) -> pd.DataFrame:
    return trade_events_between(mbp1, start_utc, cutoff_utc)
