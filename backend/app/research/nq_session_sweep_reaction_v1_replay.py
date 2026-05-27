"""Replay event helpers for NQ Session Sweep Reaction V1."""

from __future__ import annotations

import datetime as dt

from app.research.nq_session_sweep_reaction_v1_output import replay_row
from app.research.nq_session_sweep_reaction_v1_types import SweepEvent, TradePlan


def first_sweep_replay(plan: TradePlan, sweep: SweepEvent) -> dict[str, object]:
    return replay_row(
        event_type="first_sweep",
        session_date=plan.session_date,
        next_session_date=plan.next_session_date,
        ts=sweep.ts,
        price=sweep.price,
        plan=plan,
        note=f"{sweep.side}_sweep",
    )


def confirmation_replay(
    *,
    plan: TradePlan,
    sweep: SweepEvent,
    confirmation_end: dt.datetime,
    confirmation: float,
    confirmation_passed: bool,
) -> dict[str, object]:
    event_type = "confirmation_passed" if confirmation_passed else "confirmation_failed"
    return replay_row(
        event_type=event_type,
        session_date=plan.session_date,
        next_session_date=plan.next_session_date,
        ts=confirmation_end,
        price=sweep.price,
        plan=plan,
        note=f"mean_imbalance={confirmation:.4f}",
        extra={"post_sweep_30s_mean_imbalance": confirmation},
    )


def reclaim_replay(
    *,
    plan: TradePlan,
    reclaim_start: dt.datetime,
    reclaim_end: dt.datetime,
    reclaim_close: float,
) -> dict[str, object]:
    return replay_row(
        event_type="reclaim",
        session_date=plan.session_date,
        next_session_date=plan.next_session_date,
        ts=reclaim_end,
        price=reclaim_close,
        plan=plan,
        note="completed_1m_bar_closed_back_inside",
        extra={"reclaim_bar_start": reclaim_start},
    )


def entry_replay(
    *,
    plan: TradePlan,
    trade_id: str,
    entry_ts: dt.datetime,
    fill_price: float,
    stop_price: float,
    target_price: float,
    risk_pts: float,
) -> dict[str, object]:
    return replay_row(
        event_type="entry",
        session_date=plan.session_date,
        next_session_date=plan.next_session_date,
        ts=entry_ts,
        price=fill_price,
        plan=plan,
        trade_id=trade_id,
        note=plan.trade_side,
        extra={
            "stop_price": stop_price,
            "target_price": target_price,
            "risk_pts": risk_pts,
        },
    )


def exit_replay(
    *,
    plan: TradePlan,
    trade_id: str,
    exit_ts: dt.datetime,
    exit_price: float,
    exit_reason: str,
    stop_price: float,
    target_price: float,
    pnl: float,
    r_multiple: float,
) -> dict[str, object]:
    return replay_row(
        event_type="exit",
        session_date=plan.session_date,
        next_session_date=plan.next_session_date,
        ts=exit_ts,
        price=exit_price,
        plan=plan,
        trade_id=trade_id,
        note=exit_reason,
        extra={
            "stop_price": stop_price,
            "target_price": target_price,
            "pnl": pnl,
            "r_multiple": r_multiple,
        },
    )
