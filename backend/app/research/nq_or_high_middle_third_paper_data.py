"""Live data loading/status for the OR-high shadow paper monitor."""

from __future__ import annotations

import datetime as dt
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd

from app.data.reader import read_bars, read_mbp1, read_tbbo
from app.research.nq_liquidity_sweep_outcomes_sessions import normalize_mbp1

LIVE_COLUMNS = ["ts_event", "action", "price", "bid_px", "ask_px", "sequence"]


def load_live_event_window(
    *,
    symbol: str,
    session_date: dt.date,
    start: dt.datetime,
    end: dt.datetime,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Load today event data for live paper monitoring.

    MBP-1 is preferred because it matches the research study. TBBO is a
    live-data fallback in this repo and shares the columns this monitor
    needs: timestamp, trade action/price, bid, ask, and sequence.
    """

    status: dict[str, object] = {
        "preferred_schema": "mbp-1",
        "fallback_schema": "tbbo",
        "event_schema_used": None,
        "event_rows": 0,
        "event_latest_ts": None,
        "event_data_available": False,
        "errors": [],
    }
    for schema, reader in (("mbp-1", read_mbp1), ("tbbo", read_tbbo)):
        try:
            raw = reader(
                symbol=symbol,
                start=session_date,
                end=session_date + dt.timedelta(days=1),
                columns=LIVE_COLUMNS,
            )
        except Exception as exc:
            status["errors"].append(f"{schema}: {type(exc).__name__}: {exc}")
            continue
        frame = normalize_live_events(raw, start, end)
        if frame.empty:
            continue
        status.update(
            {
                "event_schema_used": schema,
                "event_rows": int(len(frame)),
                "event_latest_ts": frame.index.max().isoformat(),
                "event_data_available": True,
            }
        )
        return frame, status
    return pd.DataFrame(), status


def bars_status(symbol: str, session_date: dt.date) -> dict[str, object]:
    try:
        bars = read_bars(
            symbol=symbol,
            timeframe="1m",
            start=session_date,
            end=session_date + dt.timedelta(days=1),
        )
    except Exception as exc:
        return {
            "bars_available": False,
            "bars_rows": 0,
            "bars_latest_ts": None,
            "bars_error": f"{type(exc).__name__}: {exc}",
        }
    if bars.empty:
        return {
            "bars_available": False,
            "bars_rows": 0,
            "bars_latest_ts": None,
            "bars_error": None,
        }
    ts = pd.to_datetime(bars["ts_event"], utc=True, errors="coerce")
    return {
        "bars_available": True,
        "bars_rows": int(len(bars)),
        "bars_latest_ts": ts.max().isoformat() if not ts.dropna().empty else None,
        "bars_error": None,
    }


def run_parquet_mirror_once(
    *,
    backend_dir: Path,
    timeout_seconds: int,
) -> dict[str, object]:
    if os.environ.get("BS_DATA_BACKEND", "local").lower() == "r2":
        return {"status": "skipped_r2_backend", "returncode": None}
    command = [sys.executable, "-m", "app.ingest.parquet_mirror"]
    try:
        completed = subprocess.run(
            command,
            cwd=backend_dir,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except Exception as exc:
        return {
            "status": "error",
            "returncode": None,
            "error": f"{type(exc).__name__}: {exc}",
        }
    return {
        "status": "ok" if completed.returncode == 0 else "failed",
        "returncode": completed.returncode,
        "stdout_tail": tail_text(completed.stdout),
        "stderr_tail": tail_text(completed.stderr),
    }


def normalize_live_events(
    raw: pd.DataFrame,
    start: dt.datetime,
    end: dt.datetime,
) -> pd.DataFrame:
    if raw.empty:
        return pd.DataFrame()
    frame = normalize_mbp1(raw)
    return frame.loc[(frame.index >= pd.Timestamp(start)) & (frame.index <= pd.Timestamp(end))]


def tail_text(value: str, max_chars: int = 1000) -> str:
    return value[-max_chars:] if len(value) > max_chars else value
