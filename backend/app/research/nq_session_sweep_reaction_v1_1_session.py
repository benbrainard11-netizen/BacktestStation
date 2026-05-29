"""One-session state machine for NQ Session Sweep Reaction V1.1."""

from __future__ import annotations

import datetime as dt

import pandas as pd

from app.research.nq_session_sweep_reaction_v1_1_context import (
    add_context,
    sweep_context,
)
from app.research.nq_session_sweep_reaction_v1_1_trade_flow import (
    process_after_actionable_sweep,
)
from app.research.nq_session_sweep_reaction_v1_detection import (
    first_sweep,
    trade_events_for_sweeps,
)
from app.research.nq_session_sweep_reaction_v1_output import (
    replay_row,
    session_row,
)
from app.research.nq_session_sweep_reaction_v1_types import (
    SimulatedTrade,
    SweepEvent,
    SweepReactionConfig,
    TradePlan,
)
from app.research.nq_session_sweep_reaction_v1_utils import (
    session_times,
)


def process_session_v1_1(
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
    overnight_sweep = _first_sweep_between(
        mbp1,
        next_period.start_utc,
        times["entry_start"],
        plan=plan,
        config=config,
    )
    rth_sweep = _first_sweep_between(
        mbp1,
        times["entry_start"],
        times["sweep_cutoff"],
        plan=plan,
        config=config,
    )
    context = sweep_context(
        plan=plan,
        overnight_sweep=overnight_sweep,
        rth_sweep=rth_sweep,
    )
    if overnight_sweep is not None:
        replay.append(_context_sweep_replay(plan, overnight_sweep, context))
    if rth_sweep is None:
        row = session_row(plan, "skipped", "no_actionable_sweep_before_cutoff")
        return None, add_context(row, context), replay

    replay.append(_rth_sweep_replay(plan, rth_sweep, context))
    if rth_sweep.side != plan.armed_side:
        row = session_row(plan, "skipped", "opposite_side_first", rth_sweep)
        return None, add_context(row, context), replay

    return process_after_actionable_sweep(
        plan=plan,
        actionable_sweep=rth_sweep,
        context=context,
        replay=replay,
        bars=bars,
        mbp1=mbp1,
        config=config,
        trade_index=trade_index,
        times=times,
    )


def _first_sweep_between(
    mbp1: pd.DataFrame,
    start_utc: dt.datetime,
    end_utc: dt.datetime,
    *,
    plan: TradePlan,
    config: SweepReactionConfig,
) -> SweepEvent | None:
    events = trade_events_for_sweeps(mbp1, start_utc, end_utc)
    return first_sweep(
        events,
        anchor_high=plan.anchor_high,
        anchor_low=plan.anchor_low,
        buffer_pts=config.sweep_buffer_pts,
    )


def _context_sweep_replay(
    plan: TradePlan,
    sweep: SweepEvent,
    context: dict[str, object],
) -> dict[str, object]:
    return replay_row(
        event_type="overnight_context_sweep",
        session_date=plan.session_date,
        next_session_date=plan.next_session_date,
        ts=sweep.ts,
        price=sweep.price,
        plan=plan,
        note=f"{sweep.side}_sweep_before_0935",
        extra=context,
    )


def _rth_sweep_replay(
    plan: TradePlan,
    sweep: SweepEvent,
    context: dict[str, object],
) -> dict[str, object]:
    return replay_row(
        event_type="rth_first_sweep",
        session_date=plan.session_date,
        next_session_date=plan.next_session_date,
        ts=sweep.ts,
        price=sweep.price,
        plan=plan,
        note=f"{sweep.side}_sweep_after_0935",
        extra=context,
    )
