"""One-session state machine for NQ Session Sweep Reaction V1."""

from __future__ import annotations

import datetime as dt

import pandas as pd

from app.research.nq_session_sweep_reaction_v1_detection import (
    find_reclaim_bar,
    first_sweep,
    mean_imbalance,
    trade_events_for_sweeps,
)
from app.research.nq_session_sweep_reaction_v1_execution import (
    build_stop_target,
    entry_price,
    pnl,
    simulate_exit,
)
from app.research.nq_session_sweep_reaction_v1_output import (
    session_row,
    simulated_trade,
)
from app.research.nq_session_sweep_reaction_v1_replay import (
    confirmation_replay,
    entry_replay,
    exit_replay,
    first_sweep_replay,
    reclaim_replay,
)
from app.research.nq_session_sweep_reaction_v1_types import (
    SimulatedTrade,
    SweepReactionConfig,
    TradePlan,
)
from app.research.nq_session_sweep_reaction_v1_utils import (
    first_valid_event_after,
    row_ts,
    session_times,
)


def process_session(
    *,
    plan: TradePlan,
    next_period,
    bars: pd.DataFrame,
    mbp1: pd.DataFrame,
    config: SweepReactionConfig,
    trade_index: int,
) -> tuple[SimulatedTrade | None, dict[str, object], list[dict[str, object]]]:
    replay: list[dict[str, object]] = []
    times = session_times(plan.next_session_date, config)
    sweep_events = trade_events_for_sweeps(
        mbp1,
        next_period.start_utc,
        times["sweep_cutoff"],
    )
    sweep = first_sweep(
        sweep_events,
        anchor_high=plan.anchor_high,
        anchor_low=plan.anchor_low,
        buffer_pts=config.sweep_buffer_pts,
    )
    if sweep is None:
        return None, session_row(plan, "skipped", "no_sweep_before_cutoff"), replay
    replay.append(first_sweep_replay(plan, sweep))

    if sweep.ts < times["entry_start"]:
        reason = (
            "armed_side_swept_before_entry_start"
            if sweep.side == plan.armed_side
            else "opposite_side_first"
        )
        return None, session_row(plan, "skipped", reason, sweep), replay
    if sweep.side != plan.armed_side:
        return (
            None,
            session_row(plan, "skipped", "opposite_side_first", sweep),
            replay,
        )

    confirmation_end = sweep.ts + dt.timedelta(seconds=config.mbp_confirmation_seconds)
    confirmation = mean_imbalance(mbp1, sweep.ts, confirmation_end)
    if confirmation is None:
        return (
            None,
            session_row(plan, "skipped", "mbp_confirmation_missing", sweep),
            replay,
        )

    confirmation_passed = (
        confirmation <= config.short_imbalance_threshold
        if plan.trade_side == "short"
        else confirmation >= config.long_imbalance_threshold
    )
    replay.append(
        confirmation_replay(
            plan=plan,
            sweep=sweep,
            confirmation_end=confirmation_end,
            confirmation=confirmation,
            confirmation_passed=confirmation_passed,
        )
    )
    if not confirmation_passed:
        return (
            None,
            session_row(
                plan,
                "skipped",
                "mbp_confirmation_failed",
                sweep,
                confirmation=confirmation,
            ),
            replay,
        )

    reclaim = find_reclaim_bar(
        bars,
        plan=plan,
        confirmation_end=confirmation_end,
        sweep_ts=sweep.ts,
        entry_deadline=times["entry_deadline"],
        config=config,
    )
    if reclaim is None:
        return (
            None,
            session_row(
                plan,
                "skipped",
                "no_reclaim_before_deadline",
                sweep,
                confirmation=confirmation,
            ),
            replay,
        )

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
        return (
            None,
            session_row(
                plan,
                "skipped",
                "no_entry_event_before_deadline",
                sweep,
                confirmation=confirmation,
            ),
            replay,
        )

    fill_price = entry_price(entry_event, plan.trade_side, config)
    entry_ts = row_ts(entry_event)
    stop_plan = build_stop_target(
        trade_side=plan.trade_side,
        entry_price=fill_price,
        sweep_ts=sweep.ts,
        entry_ts=entry_ts,
        mbp1=mbp1,
        config=config,
    )
    if stop_plan is None:
        return (
            None,
            session_row(
                plan,
                "skipped",
                "missing_sweep_extreme",
                sweep,
                confirmation=confirmation,
            ),
            replay,
        )

    stop_price, target_price, risk_pts, sweep_extreme = stop_plan
    if risk_pts > config.max_stop_pts:
        return (
            None,
            session_row(
                plan,
                "skipped",
                "stop_distance_too_wide",
                sweep,
                confirmation=confirmation,
                risk_pts=risk_pts,
            ),
            replay,
        )

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
        return (
            None,
            session_row(
                plan,
                "skipped",
                "no_exit_event",
                sweep,
                confirmation=confirmation,
            ),
            replay,
        )

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
        sweep=sweep,
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
    return (
        trade,
        session_row(
            plan,
            "traded",
            "",
            sweep,
            confirmation=confirmation,
            risk_pts=risk_pts,
            trade_id=trade_id,
        ),
        replay,
    )
