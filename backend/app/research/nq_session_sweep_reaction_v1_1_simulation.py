"""Trade simulation step for NQ Session Sweep Reaction V1.1."""

from __future__ import annotations

import datetime as dt

import pandas as pd

from app.research.nq_session_sweep_reaction_v1_1_context import add_context
from app.research.nq_session_sweep_reaction_v1_execution import (
    pnl,
    simulate_exit,
)
from app.research.nq_session_sweep_reaction_v1_output import (
    session_row,
    simulated_trade,
)
from app.research.nq_session_sweep_reaction_v1_replay import (
    entry_replay,
    exit_replay,
)
from app.research.nq_session_sweep_reaction_v1_types import (
    SimulatedTrade,
    SweepEvent,
    SweepReactionConfig,
    TradePlan,
)


def simulate_trade_after_entry(
    *,
    plan: TradePlan,
    actionable_sweep: SweepEvent,
    context: dict[str, object],
    replay: list[dict[str, object]],
    mbp1: pd.DataFrame,
    config: SweepReactionConfig,
    trade_index: int,
    confirmation: float,
    confirmation_end: dt.datetime,
    reclaim_start: dt.datetime,
    reclaim_end: dt.datetime,
    fill_price: float,
    entry_ts: dt.datetime,
    stop_price: float,
    target_price: float,
    risk_pts: float,
    sweep_extreme: float,
    times: dict[str, dt.datetime],
) -> tuple[SimulatedTrade | None, dict[str, object], list[dict[str, object]]]:
    trade_id = f"{plan.session_date}_{trade_index:04d}"
    replay.append(
        entry_replay(
            plan=plan,
            trade_id=trade_id,
            entry_ts=entry_ts,
            fill_price=fill_price,
            stop_price=stop_price,
            target_price=target_price,
            risk_pts=risk_pts,
        )
    )
    exit_fill = simulate_exit(
        mbp1,
        trade_side=plan.trade_side,
        entry_ts=entry_ts,
        stop_price=stop_price,
        target_price=target_price,
        forced_flat=times["forced_flat"],
        config=config,
    )
    if exit_fill is None:
        row = session_row(
            plan,
            "skipped",
            "no_exit_event",
            actionable_sweep,
            confirmation=confirmation,
        )
        return None, add_context(row, context), replay

    exit_ts, exit_price, exit_reason, fill_confidence = exit_fill
    trade_pnl = pnl(
        side=plan.trade_side,
        entry_price=fill_price,
        exit_price=exit_price,
        qty=config.qty,
        contract_value=config.contract_value,
        commission_per_contract=config.commission_per_contract,
    )
    risk_dollars = risk_pts * config.contract_value * config.qty
    r_multiple = trade_pnl / risk_dollars if risk_dollars > 0 else 0.0
    trade = simulated_trade(
        trade_id=trade_id,
        plan=plan,
        sweep=actionable_sweep,
        qty=config.qty,
        entry_ts=entry_ts,
        exit_ts=exit_ts,
        entry_price=fill_price,
        exit_price=exit_price,
        stop_price=stop_price,
        target_price=target_price,
        risk_pts=risk_pts,
        pnl=trade_pnl,
        r_multiple=r_multiple,
        exit_reason=exit_reason,
        fill_confidence=fill_confidence,
        sweep_extreme=sweep_extreme,
        reclaim_bar_start=reclaim_start,
        reclaim_bar_end=reclaim_end,
        confirmation_end=confirmation_end,
        confirmation=confirmation,
    )
    replay.append(
        exit_replay(
            plan=plan,
            trade_id=trade_id,
            exit_ts=exit_ts,
            exit_price=exit_price,
            exit_reason=exit_reason,
            stop_price=stop_price,
            target_price=target_price,
            pnl=trade_pnl,
            r_multiple=r_multiple,
        )
    )
    row = session_row(
        plan,
        "traded",
        "",
        actionable_sweep,
        confirmation=confirmation,
        risk_pts=risk_pts,
        trade_id=trade_id,
    )
    return trade, add_context(row, context), replay
