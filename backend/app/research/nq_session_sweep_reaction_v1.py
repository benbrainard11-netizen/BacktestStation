"""NQ Session Sweep Reaction V1 research/backtest harness.

This module implements the strategy candidate documented in:
docs/STRATEGY_CANDIDATE_NQ_SESSION_SWEEP_REACTION_V1.md

The public entry point is `run_backtest`. Helper modules keep detection,
execution, output shaping, and the per-session state machine separate.
"""

from __future__ import annotations

import datetime as dt

import pandas as pd

from app.research.final_15m_session_close import (
    close_position,
    globex_day_periods,
    next_globex_day,
    summarize_session,
)
from app.research.nq_session_sweep_reaction_v1_detection import (
    build_trade_plan,
    plan_skip_reason,
    prior_range_median,
)
from app.research.nq_session_sweep_reaction_v1_output import (
    equity_frame,
    replay_row,
    session_skip_row,
    summarize_results,
    trades_frame,
)
from app.research.nq_session_sweep_reaction_v1_session import process_session
from app.research.nq_session_sweep_reaction_v1_types import (
    SimulatedTrade,
    SweepEvent,
    SweepReactionConfig,
    TradePlan,
)
from app.research.nq_session_sweep_reaction_v1_utils import (
    ET,
    normalize_bars,
    normalize_mbp1,
)

__all__ = [
    "SimulatedTrade",
    "SweepEvent",
    "SweepReactionConfig",
    "TradePlan",
    "run_backtest",
    "summarize_results",
]


def run_backtest(
    *,
    bars: pd.DataFrame,
    mbp1: pd.DataFrame,
    start: dt.date,
    end: dt.date,
    warmup_start: dt.date | None = None,
    config: SweepReactionConfig | None = None,
) -> dict[str, pd.DataFrame | dict[str, object]]:
    """Run the V1 sweep-reaction backtest over anchor Globex label dates.

    `start` and `end` are anchor Globex label dates in ET, half-open.
    """

    cfg = config or SweepReactionConfig()
    bars_norm = normalize_bars(bars)
    mbp_norm = normalize_mbp1(mbp1)

    trades: list[SimulatedTrade] = []
    session_rows: list[dict[str, object]] = []
    replay_rows: list[dict[str, object]] = []
    prior_ranges: list[float] = []

    period_start = warmup_start or start
    for period in globex_day_periods(start=period_start, end=end):
        session = summarize_session(bars_norm, period)
        if session is None:
            if period.end_utc.astimezone(ET).date() >= start:
                row = session_skip_row(cfg, period, "missing_anchor_bars")
                session_rows.append(row)
            continue
        if session.label_date < start:
            prior_ranges.append(session.range_pts)
            continue

        prior_median = prior_range_median(prior_ranges, cfg)
        plan = build_trade_plan(session, prior_median, cfg)
        if plan is None:
            reason = plan_skip_reason(session, prior_median, cfg)
            row = session_skip_row(
                cfg,
                period,
                reason,
                session_date=session.label_date.isoformat(),
                anchor_high=session.high,
                anchor_low=session.low,
                anchor_range=session.range_pts,
                session_close_position=close_position(
                    session.close,
                    session.high,
                    session.low,
                ),
                prior20_median_range=prior_median,
            )
            session_rows.append(row)
            prior_ranges.append(session.range_pts)
            continue

        replay_rows.append(
            replay_row(
                event_type="session_armed",
                session_date=plan.session_date,
                next_session_date=plan.next_session_date,
                ts=period.end_utc,
                price=None,
                plan=plan,
                note=f"armed_{plan.armed_side}_sweep",
            )
        )

        trade, session_row, replay = process_session(
            plan=plan,
            next_period=next_globex_day(period),
            bars=bars_norm,
            mbp1=mbp_norm,
            config=cfg,
            trade_index=len(trades) + 1,
        )
        session_rows.append(session_row)
        replay_rows.extend(replay)
        if trade is not None:
            trades.append(trade)
        prior_ranges.append(session.range_pts)

    trades_df = trades_frame(trades)
    sessions_df = pd.DataFrame(session_rows)
    replay_df = pd.DataFrame(replay_rows)
    equity_df = equity_frame(trades, cfg.initial_equity)
    summary = summarize_results(
        trades_df=trades_df,
        sessions_df=sessions_df,
        equity_df=equity_df,
        config=cfg,
        start=start,
        end=end,
    )
    return {
        "trades": trades_df,
        "sessions": sessions_df,
        "replay_events": replay_df,
        "equity": equity_df,
        "summary": summary,
    }
