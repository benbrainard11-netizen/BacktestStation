"""Chunked runner for larger NQ Session Sweep Reaction V1.1 studies."""

from __future__ import annotations

import gc
import logging
from datetime import date, timedelta

import pandas as pd

from app.data.reader import read_bars
from app.research.final_15m_session_close import (
    close_position,
    globex_day_periods,
    next_globex_day,
    summarize_session,
)
from app.research.nq_session_sweep_reaction_v1_1 import (
    _add_trade_context,
    _summary,
    _with_empty_context,
)
from app.research.nq_session_sweep_reaction_v1_1_session import (
    process_session_v1_1,
)
from app.research.nq_session_sweep_reaction_v1_chunked import (
    _daily_load_error_row,
    _filter_table_ts,
    _mbp_load_window,
    _read_mbp1_with_retries,
    _session_row_for_load_error,
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
    trades_frame,
)
from app.research.nq_session_sweep_reaction_v1_types import (
    SimulatedTrade,
    SweepReactionConfig,
)
from app.research.nq_session_sweep_reaction_v1_utils import (
    ET,
    normalize_bars,
    normalize_mbp1,
)

logger = logging.getLogger("nq_session_sweep_reaction_v1_1_chunked")


def run_chunked_backtest_v1_1(
    *,
    symbol: str,
    start: date,
    end: date,
    warmup_days: int,
    config: SweepReactionConfig,
) -> dict[str, pd.DataFrame | dict[str, object]]:
    warmup_start = start - timedelta(days=warmup_days)
    bars_norm = _load_bars(symbol, warmup_start, end)
    trades: list[SimulatedTrade] = []
    session_rows: list[dict[str, object]] = []
    replay_rows: list[dict[str, object]] = []
    daily_load_rows: list[dict[str, object]] = []
    prior_ranges: list[float] = []

    for period in globex_day_periods(start=warmup_start, end=end):
        session = summarize_session(bars_norm, period)
        if session is None:
            if period.end_utc.astimezone(ET).date() >= start:
                row = session_skip_row(config, period, "missing_anchor_bars")
                session_rows.append(_with_empty_context(row))
            continue
        if session.label_date < start:
            prior_ranges.append(session.range_pts)
            continue

        prior_median = prior_range_median(prior_ranges, config)
        plan = build_trade_plan(session, prior_median, config)
        if plan is None:
            reason = plan_skip_reason(session, prior_median, config)
            row = _plan_skip_row(config, period, session, reason, prior_median)
            session_rows.append(_with_empty_context(row))
            prior_ranges.append(session.range_pts)
            continue

        next_period = next_globex_day(period)
        replay_rows.append(_armed_replay(period, plan))
        loaded = _load_mbp(symbol, next_period, plan, config)
        daily_load_rows.append(loaded["daily_load_row"])
        if loaded["error"]:
            row = _session_row_for_load_error(plan, str(loaded["error"]))
            session_rows.append(_with_empty_context(row))
            prior_ranges.append(session.range_pts)
            continue

        mbp_norm = normalize_mbp1(loaded["mbp1"])
        trade, session_row, replay = process_session_v1_1(
            plan=plan,
            next_period=next_period,
            bars=bars_norm,
            mbp1=mbp_norm,
            config=config,
            trade_index=len(trades) + 1,
        )
        session_rows.append(session_row)
        replay_rows.extend(replay)
        if trade is not None:
            trades.append(trade)
        prior_ranges.append(session.range_pts)
        del loaded, mbp_norm
        gc.collect()

    return _result(
        trades=trades,
        session_rows=session_rows,
        replay_rows=replay_rows,
        daily_load_rows=daily_load_rows,
        config=config,
        start=start,
        end=end,
    )


def _load_bars(symbol: str, warmup_start: date, end: date) -> pd.DataFrame:
    bars_load_start = warmup_start - timedelta(days=3)
    bars_load_end = end + timedelta(days=4)
    logger.info(
        "loading 1m bars for %s from %s to %s",
        symbol,
        bars_load_start,
        bars_load_end,
    )
    bars = read_bars(
        symbol=symbol,
        timeframe="1m",
        start=bars_load_start,
        end=bars_load_end,
    )
    bars_norm = normalize_bars(bars)
    logger.info("loaded %d 1m bars", len(bars_norm))
    return bars_norm


def _load_mbp(
    symbol: str,
    next_period,
    plan,
    config: SweepReactionConfig,
) -> dict[str, object]:
    load_start, load_end, window_start, window_end = _mbp_load_window(
        next_period,
        plan.next_session_date,
        config,
    )
    logger.info(
        "session %s -> loading MBP-1 %s to %s, filtering %s to %s",
        plan.session_date,
        load_start,
        load_end,
        window_start,
        window_end,
    )
    try:
        mbp_table = _read_mbp1_with_retries(
            symbol=symbol,
            start=load_start,
            end=load_end,
        )
    except OSError as exc:
        logger.exception("MBP-1 load failed for session %s", plan.session_date)
        return {
            "mbp1": pd.DataFrame(),
            "error": exc,
            "daily_load_row": _daily_load_error_row(
                plan.session_date,
                plan.next_session_date,
                load_start,
                load_end,
                window_start,
                window_end,
                str(exc),
            ),
        }
    mbp_filtered = _filter_table_ts(mbp_table, window_start, window_end)
    mbp1 = mbp_filtered.to_pandas()
    return {
        "mbp1": mbp1,
        "error": None,
        "daily_load_row": {
            "session_date": plan.session_date,
            "next_session_date": plan.next_session_date,
            "mbp_start": load_start.isoformat(),
            "mbp_end": load_end.isoformat(),
            "mbp_window_start": window_start.isoformat(),
            "mbp_window_end": window_end.isoformat(),
            "mbp_raw_rows": int(mbp_table.num_rows),
            "mbp_rows": int(len(mbp1)),
        },
    }


def _plan_skip_row(config, period, session, reason, prior_median):
    return session_skip_row(
        config,
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


def _armed_replay(period, plan) -> dict[str, object]:
    return replay_row(
        event_type="session_armed",
        session_date=plan.session_date,
        next_session_date=plan.next_session_date,
        ts=period.end_utc,
        price=None,
        plan=plan,
        note=f"armed_{plan.armed_side}_sweep_v1_1",
    )


def _result(
    *,
    trades: list[SimulatedTrade],
    session_rows: list[dict[str, object]],
    replay_rows: list[dict[str, object]],
    daily_load_rows: list[dict[str, object]],
    config: SweepReactionConfig,
    start: date,
    end: date,
) -> dict[str, pd.DataFrame | dict[str, object]]:
    sessions_df = pd.DataFrame(session_rows)
    trades_df = _add_trade_context(trades_frame(trades), sessions_df)
    equity_df = equity_frame(trades, config.initial_equity)
    daily_loads_df = pd.DataFrame(daily_load_rows)
    summary = _summary(
        trades_df=trades_df,
        sessions_df=sessions_df,
        equity_df=equity_df,
        config=config,
        start=start,
        end=end,
    )
    summary["mbp_loads"] = {
        "planned_sessions_loaded": int(len(daily_loads_df)),
        "total_mbp_rows_loaded": int(daily_loads_df["mbp_rows"].sum())
        if not daily_loads_df.empty
        else 0,
    }
    return {
        "trades": trades_df,
        "sessions": sessions_df,
        "replay_events": pd.DataFrame(replay_rows),
        "equity": equity_df,
        "daily_loads": daily_loads_df,
        "summary": summary,
    }
