"""Chunked runner for larger NQ Session Sweep Reaction V1 studies."""

from __future__ import annotations

import gc
import logging
import time
from datetime import date, timedelta

import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc

from app.data.reader import read_bars, read_mbp1
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
    SweepReactionConfig,
)
from app.research.nq_session_sweep_reaction_v1_utils import (
    ET,
    normalize_bars,
    normalize_mbp1,
    session_times,
)

logger = logging.getLogger("nq_session_sweep_reaction_v1_chunked")

_MBP1_COLUMNS = [
    "ts_event",
    "symbol",
    "action",
    "side",
    "price",
    "size",
    "bid_px",
    "ask_px",
    "bid_sz",
    "ask_sz",
    "sequence",
]


def run_chunked_backtest(
    *,
    symbol: str,
    start: date,
    end: date,
    warmup_days: int,
    config: SweepReactionConfig,
) -> dict[str, pd.DataFrame | dict[str, object]]:
    warmup_start = start - timedelta(days=warmup_days)
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
                session_rows.append(row)
            continue
        if session.label_date < start:
            prior_ranges.append(session.range_pts)
            continue

        prior_median = prior_range_median(prior_ranges, config)
        plan = build_trade_plan(session, prior_median, config)
        if plan is None:
            reason = plan_skip_reason(session, prior_median, config)
            row = session_skip_row(
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
        next_period = next_globex_day(period)
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
            session_rows.append(_session_row_for_load_error(plan, str(exc)))
            daily_load_rows.append(
                _daily_load_error_row(
                    plan.session_date,
                    plan.next_session_date,
                    load_start,
                    load_end,
                    window_start,
                    window_end,
                    str(exc),
                )
            )
            prior_ranges.append(session.range_pts)
            continue

        mbp_filtered = _filter_table_ts(mbp_table, window_start, window_end)
        mbp1 = mbp_filtered.to_pandas()
        daily_load_rows.append(
            {
                "session_date": plan.session_date,
                "next_session_date": plan.next_session_date,
                "mbp_start": load_start.isoformat(),
                "mbp_end": load_end.isoformat(),
                "mbp_window_start": window_start.isoformat(),
                "mbp_window_end": window_end.isoformat(),
                "mbp_raw_rows": int(mbp_table.num_rows),
                "mbp_rows": int(len(mbp1)),
            }
        )
        mbp_norm = normalize_mbp1(mbp1)
        trade, session_row, replay = process_session(
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
        del mbp_table, mbp_filtered, mbp1, mbp_norm
        gc.collect()

    trades_df = trades_frame(trades)
    sessions_df = pd.DataFrame(session_rows)
    replay_df = pd.DataFrame(replay_rows)
    equity_df = equity_frame(trades, config.initial_equity)
    daily_loads_df = pd.DataFrame(daily_load_rows)
    summary = summarize_results(
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
        "replay_events": replay_df,
        "equity": equity_df,
        "daily_loads": daily_loads_df,
        "summary": summary,
    }


def _mbp_load_window(
    next_period,
    next_session_date: str,
    config: SweepReactionConfig,
) -> tuple[date, date, object, object]:
    times = session_times(next_session_date, config)
    window_start = next_period.start_utc
    window_end = times["forced_flat"] + timedelta(minutes=15)
    load_start = window_start.date()
    load_end = window_end.date() + timedelta(days=1)
    return load_start, load_end, window_start, window_end


def _filter_table_ts(table: pa.Table, start_ts: object, end_ts: object) -> pa.Table:
    if table.num_rows == 0:
        return table
    ts_type = table.schema.field("ts_event").type
    mask = pc.and_(
        pc.greater_equal(table["ts_event"], pa.scalar(start_ts, type=ts_type)),
        pc.less(table["ts_event"], pa.scalar(end_ts, type=ts_type)),
    )
    return table.filter(mask)


def _read_mbp1_with_retries(
    *,
    symbol: str,
    start: date,
    end: date,
    attempts: int = 3,
) -> pa.Table:
    last_error: OSError | None = None
    for attempt in range(1, attempts + 1):
        try:
            return read_mbp1(
                symbol=symbol,
                start=start,
                end=end,
                columns=_MBP1_COLUMNS,
                as_pandas=False,
            )
        except OSError as exc:
            last_error = exc
            if attempt == attempts:
                break
            wait_seconds = 2 * attempt
            logger.warning(
                "MBP-1 read failed for %s to %s; retrying in %ss (%s/%s): %s",
                start,
                end,
                wait_seconds,
                attempt,
                attempts,
                exc,
            )
            time.sleep(wait_seconds)
    assert last_error is not None
    raise last_error


def _daily_load_error_row(
    session_date: str,
    next_session_date: str,
    load_start: date,
    load_end: date,
    window_start,
    window_end,
    error: str,
) -> dict[str, object]:
    return {
        "session_date": session_date,
        "next_session_date": next_session_date,
        "mbp_start": load_start.isoformat(),
        "mbp_end": load_end.isoformat(),
        "mbp_window_start": window_start.isoformat(),
        "mbp_window_end": window_end.isoformat(),
        "mbp_raw_rows": 0,
        "mbp_rows": 0,
        "error": error,
    }


def _session_row_for_load_error(plan, error: str) -> dict[str, object]:
    return {
        "session_date": plan.session_date,
        "next_session_date": plan.next_session_date,
        "status": "skipped",
        "skip_reason": "mbp_load_error",
        "trade_id": None,
        "armed_side": plan.armed_side,
        "trade_side": plan.trade_side,
        "anchor_high": plan.anchor_high,
        "anchor_low": plan.anchor_low,
        "anchor_range": plan.anchor_range,
        "session_close_position": plan.session_close_position,
        "session_close_bias": plan.session_close_bias,
        "prior20_median_range": plan.prior20_median_range,
        "error": error,
    }
