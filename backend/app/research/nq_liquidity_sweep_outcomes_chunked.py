"""Chunked R2/local runner for the NQ liquidity sweep outcome study."""

from __future__ import annotations

import gc
import logging
import time
from datetime import date, timedelta

import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc

from app.data.reader import read_bars, read_mbp1
from app.research.nq_liquidity_sweep_outcomes_features import (
    process_session_sweeps,
)
from app.research.nq_liquidity_sweep_outcomes_sessions import (
    normalize_bars,
    session_dates,
    session_time_bounds,
)
from app.research.nq_liquidity_sweep_outcomes_stats import analyze_sweep_features
from app.research.nq_liquidity_sweep_outcomes_types import LiquiditySweepStudyConfig

logger = logging.getLogger("nq_liquidity_sweep_outcomes")

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


def run_chunked_study(
    *,
    symbol: str,
    start: date,
    end: date,
    config: LiquiditySweepStudyConfig | None = None,
) -> dict[str, object]:
    cfg = config or LiquiditySweepStudyConfig(symbol=symbol)
    bars = _load_bars(symbol, start, end)
    events: list[pd.DataFrame] = []
    features: list[pd.DataFrame] = []
    sessions: list[dict[str, object]] = []
    daily_loads: list[dict[str, object]] = []

    for session_date in session_dates(start, end):
        loaded = _load_mbp_for_session(symbol, session_date, cfg)
        daily_loads.append(loaded["daily_load_row"])
        if loaded["error"]:
            sessions.append(_error_session_row(session_date, str(loaded["error"])))
            continue
        session_events, session_features, session_row = process_session_sweeps(
            bars=bars,
            mbp1=loaded["mbp1"],
            session_date=session_date,
            config=cfg,
        )
        events.append(session_events)
        features.append(session_features)
        sessions.append(session_row)
        del loaded, session_events, session_features
        gc.collect()

    events_df = _concat(events)
    features_df = _concat(features)
    analysis = analyze_sweep_features(events=events_df, features=features_df, config=cfg)
    return {
        "events": events_df,
        "features": features_df,
        "sessions": pd.DataFrame(sessions),
        "daily_loads": pd.DataFrame(daily_loads),
        **analysis,
    }


def _load_bars(symbol: str, start: date, end: date) -> pd.DataFrame:
    bars_start = start - timedelta(days=10)
    bars_end = end + timedelta(days=1)
    logger.info("loading 1m bars for %s from %s to %s", symbol, bars_start, bars_end)
    bars = read_bars(
        symbol=symbol,
        timeframe="1m",
        start=bars_start,
        end=bars_end,
    )
    out = normalize_bars(bars)
    logger.info("loaded %d 1m bars", len(out))
    return out


def _load_mbp_for_session(
    symbol: str,
    session_date: date,
    config: LiquiditySweepStudyConfig,
) -> dict[str, object]:
    times = session_time_bounds(session_date, config)
    window_start = times["sweep_start"] - timedelta(seconds=60)
    window_end = times["globex_close"]
    load_start = window_start.date()
    load_end = window_end.date() + timedelta(days=1)
    logger.info(
        "session %s -> loading MBP-1 %s to %s, filtering %s to %s",
        session_date,
        load_start,
        load_end,
        window_start,
        window_end,
    )
    try:
        table = _read_mbp1_with_retries(symbol=symbol, start=load_start, end=load_end)
    except OSError as exc:
        logger.exception("MBP-1 load failed for %s", session_date)
        return {
            "mbp1": pd.DataFrame(),
            "error": exc,
            "daily_load_row": _load_row(
                session_date,
                load_start,
                load_end,
                window_start,
                window_end,
                0,
                0,
                str(exc),
            ),
        }
    filtered = _filter_table_ts(table, window_start, window_end)
    mbp1 = filtered.to_pandas()
    return {
        "mbp1": mbp1,
        "error": None,
        "daily_load_row": _load_row(
            session_date,
            load_start,
            load_end,
            window_start,
            window_end,
            int(table.num_rows),
            int(len(mbp1)),
            None,
        ),
    }


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


def _filter_table_ts(table: pa.Table, start_ts: object, end_ts: object) -> pa.Table:
    if table.num_rows == 0:
        return table
    ts_type = table.schema.field("ts_event").type
    mask = pc.and_(
        pc.greater_equal(table["ts_event"], pa.scalar(start_ts, type=ts_type)),
        pc.less(table["ts_event"], pa.scalar(end_ts, type=ts_type)),
    )
    return table.filter(mask)


def _load_row(
    session_date: date,
    load_start: date,
    load_end: date,
    window_start,
    window_end,
    raw_rows: int,
    rows: int,
    error: str | None,
) -> dict[str, object]:
    return {
        "session_date": session_date.isoformat(),
        "mbp_start": load_start.isoformat(),
        "mbp_end": load_end.isoformat(),
        "mbp_window_start": window_start.isoformat(),
        "mbp_window_end": window_end.isoformat(),
        "mbp_raw_rows": raw_rows,
        "mbp_rows": rows,
        "error": error,
    }


def _error_session_row(session_date: date, error: str) -> dict[str, object]:
    return {
        "session_date": session_date.isoformat(),
        "levels_available": 0,
        "sweep_events": 0,
        "continuation_breakouts": 0,
        "failed_breakout_reversals": 0,
        "ambiguous": 0,
        "error": error,
    }


def _concat(frames: list[pd.DataFrame]) -> pd.DataFrame:
    frames = [frame for frame in frames if not frame.empty]
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True, sort=False)
