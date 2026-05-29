"""Post-sweep trade flow for NQ Session Sweep Reaction V1.1."""

from __future__ import annotations

import datetime as dt

import pandas as pd

from app.research.nq_session_sweep_reaction_v1_1_context import add_context
from app.research.nq_session_sweep_reaction_v1_1_simulation import (
    simulate_trade_after_entry,
)
from app.research.nq_session_sweep_reaction_v1_detection import (
    find_reclaim_bar,
    mean_imbalance,
)
from app.research.nq_session_sweep_reaction_v1_execution import (
    build_stop_target,
    entry_price,
)
from app.research.nq_session_sweep_reaction_v1_output import (
    session_row,
)
from app.research.nq_session_sweep_reaction_v1_replay import (
    confirmation_replay,
    reclaim_replay,
)
from app.research.nq_session_sweep_reaction_v1_types import (
    SimulatedTrade,
    SweepEvent,
    SweepReactionConfig,
    TradePlan,
)
from app.research.nq_session_sweep_reaction_v1_utils import (
    first_valid_event_after,
    row_ts,
)


def process_after_actionable_sweep(
    *,
    plan: TradePlan,
    actionable_sweep: SweepEvent,
    context: dict[str, object],
    replay: list[dict[str, object]],
    bars: pd.DataFrame,
    mbp1: pd.DataFrame,
    config: SweepReactionConfig,
    trade_index: int,
    times: dict[str, dt.datetime],
) -> tuple[SimulatedTrade | None, dict[str, object], list[dict[str, object]]]:
    confirmation_end = actionable_sweep.ts + dt.timedelta(
        seconds=config.mbp_confirmation_seconds
    )
    confirmation = mean_imbalance(mbp1, actionable_sweep.ts, confirmation_end)
    if confirmation is None:
        row = session_row(
            plan,
            "skipped",
            "mbp_confirmation_missing",
            actionable_sweep,
        )
        return None, add_context(row, context), replay

    confirmation_passed = (
        confirmation <= config.short_imbalance_threshold
        if plan.trade_side == "short"
        else confirmation >= config.long_imbalance_threshold
    )
    replay.append(
        confirmation_replay(
            plan=plan,
            sweep=actionable_sweep,
            confirmation_end=confirmation_end,
            confirmation=confirmation,
            confirmation_passed=confirmation_passed,
        )
    )
    if not confirmation_passed:
        row = session_row(
            plan,
            "skipped",
            "mbp_confirmation_failed",
            actionable_sweep,
            confirmation=confirmation,
        )
        return None, add_context(row, context), replay

    return _process_entry_and_exit(
        plan=plan,
        actionable_sweep=actionable_sweep,
        context=context,
        replay=replay,
        bars=bars,
        mbp1=mbp1,
        config=config,
        trade_index=trade_index,
        confirmation=confirmation,
        confirmation_end=confirmation_end,
        times=times,
    )


def _process_entry_and_exit(
    *,
    plan: TradePlan,
    actionable_sweep: SweepEvent,
    context: dict[str, object],
    replay: list[dict[str, object]],
    bars: pd.DataFrame,
    mbp1: pd.DataFrame,
    config: SweepReactionConfig,
    trade_index: int,
    confirmation: float,
    confirmation_end: dt.datetime,
    times: dict[str, dt.datetime],
) -> tuple[SimulatedTrade | None, dict[str, object], list[dict[str, object]]]:
    reclaim = find_reclaim_bar(
        bars,
        plan=plan,
        confirmation_end=confirmation_end,
        sweep_ts=actionable_sweep.ts,
        entry_deadline=times["entry_deadline"],
        config=config,
    )
    if reclaim is None:
        row = session_row(
            plan,
            "skipped",
            "no_reclaim_before_deadline",
            actionable_sweep,
            confirmation=confirmation,
        )
        return None, add_context(row, context), replay

    reclaim_start, reclaim_end, reclaim_close = reclaim
    replay.append(
        reclaim_replay(
            plan=plan,
            reclaim_start=reclaim_start,
            reclaim_end=reclaim_end,
            reclaim_close=reclaim_close,
        )
    )
    entry_event = first_valid_event_after(
        mbp1,
        start_utc=reclaim_end,
        end_utc=times["entry_deadline"],
    )
    if entry_event is None:
        row = session_row(
            plan,
            "skipped",
            "no_entry_event_before_deadline",
            actionable_sweep,
            confirmation=confirmation,
        )
        return None, add_context(row, context), replay

    fill_price = entry_price(entry_event, plan.trade_side, config)
    entry_ts = row_ts(entry_event)
    stop_plan = build_stop_target(
        trade_side=plan.trade_side,
        entry_price=fill_price,
        sweep_ts=actionable_sweep.ts,
        entry_ts=entry_ts,
        mbp1=mbp1,
        config=config,
    )
    if stop_plan is None:
        row = session_row(
            plan,
            "skipped",
            "missing_sweep_extreme",
            actionable_sweep,
            confirmation=confirmation,
        )
        return None, add_context(row, context), replay

    stop_price, target_price, risk_pts, sweep_extreme = stop_plan
    if risk_pts > config.max_stop_pts:
        row = session_row(
            plan,
            "skipped",
            "stop_distance_too_wide",
            actionable_sweep,
            confirmation=confirmation,
            risk_pts=risk_pts,
        )
        return None, add_context(row, context), replay

    return simulate_trade_after_entry(
        plan=plan,
        actionable_sweep=actionable_sweep,
        context=context,
        replay=replay,
        mbp1=mbp1,
        config=config,
        trade_index=trade_index,
        confirmation=confirmation,
        confirmation_end=confirmation_end,
        reclaim_start=reclaim_start,
        reclaim_end=reclaim_end,
        fill_price=fill_price,
        entry_ts=entry_ts,
        stop_price=stop_price,
        target_price=target_price,
        risk_pts=risk_pts,
        sweep_extreme=sweep_extreme,
        times=times,
    )
