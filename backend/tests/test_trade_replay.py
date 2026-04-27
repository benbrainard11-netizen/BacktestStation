"""Tests for the /trade-replay service + API."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from app.data.schema import TBBO_SCHEMA
from app.services.trade_replay import (
    LEAD_MAX_SECONDS,
    TRAIL_MAX_SECONDS,
    clamp_lead,
    clamp_trail,
    compute_window,
    load_trade_window,
    tbbo_partition_exists,
)


# --- Helpers --------------------------------------------------------------


def _write_tbbo_partition(
    data_root: Path,
    *,
    symbol: str,
    date: dt.date,
    rows: int = 60,
) -> Path:
    """Drop a synthetic TBBO partition with one tick per second from 13:30Z."""
    out = (
        data_root
        / "raw"
        / "databento"
        / "tbbo"
        / f"symbol={symbol}"
        / f"date={date.isoformat()}"
        / "part-000.parquet"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    base_ts = pd.Timestamp(date, tz="UTC") + pd.Timedelta("13:30:00")
    df = pd.DataFrame(
        {
            "ts_event": pd.to_datetime(
                [base_ts + pd.Timedelta(seconds=i) for i in range(rows)]
            ),
            "ts_recv": pd.to_datetime(
                [base_ts + pd.Timedelta(seconds=i) for i in range(rows)]
            ),
            "symbol": [symbol] * rows,
            "action": ["T"] * rows,
            "side": ["A"] * rows,
            "price": [21000.0 + i for i in range(rows)],
            "size": [1] * rows,
            "bid_px": [20999.5 + i for i in range(rows)],
            "ask_px": [21000.5 + i for i in range(rows)],
            "bid_sz": [5] * rows,
            "ask_sz": [7] * rows,
            "publisher_id": [1] * rows,
            "instrument_id": [12345] * rows,
            "sequence": list(range(rows)),
        }
    )
    table = pa.Table.from_pandas(
        df, schema=TBBO_SCHEMA.pa_schema, preserve_index=False
    )
    pq.write_table(table, out)
    return out


# --- tbbo_partition_exists ------------------------------------------------


def test_tbbo_partition_exists_true_when_parquet_present(tmp_path):
    _write_tbbo_partition(tmp_path, symbol="NQ.c.0", date=dt.date(2026, 4, 27))
    assert (
        tbbo_partition_exists(
            symbol="NQ.c.0", date=dt.date(2026, 4, 27), data_root=tmp_path
        )
        is True
    )


def test_tbbo_partition_exists_false_when_dir_missing(tmp_path):
    assert (
        tbbo_partition_exists(
            symbol="NQ.c.0", date=dt.date(2026, 4, 27), data_root=tmp_path
        )
        is False
    )


def test_tbbo_partition_exists_false_when_dir_empty(tmp_path):
    # Empty partition dir — no parquet files
    part_dir = (
        tmp_path
        / "raw"
        / "databento"
        / "tbbo"
        / "symbol=NQ.c.0"
        / "date=2026-04-27"
    )
    part_dir.mkdir(parents=True)
    assert (
        tbbo_partition_exists(
            symbol="NQ.c.0", date=dt.date(2026, 4, 27), data_root=tmp_path
        )
        is False
    )


# --- compute_window + clamps ----------------------------------------------


def test_compute_window_basic():
    entry = dt.datetime(2026, 4, 27, 13, 30, 0)
    exit_ = dt.datetime(2026, 4, 27, 13, 35, 0)
    start, end = compute_window(entry, exit_, lead_seconds=60, trail_seconds=120)
    assert start == dt.datetime(2026, 4, 27, 13, 29, 0)
    assert end == dt.datetime(2026, 4, 27, 13, 37, 0)


def test_compute_window_open_trade_uses_entry_for_trail():
    entry = dt.datetime(2026, 4, 27, 13, 30, 0)
    start, end = compute_window(entry, None, lead_seconds=60, trail_seconds=300)
    assert start == dt.datetime(2026, 4, 27, 13, 29, 0)
    assert end == dt.datetime(2026, 4, 27, 13, 35, 0)


def test_clamp_lead_caps_at_max():
    assert clamp_lead(LEAD_MAX_SECONDS + 1) == LEAD_MAX_SECONDS
    assert clamp_lead(0) == 0
    assert clamp_lead(-5) == 0


def test_clamp_trail_caps_at_max():
    assert clamp_trail(TRAIL_MAX_SECONDS + 100) == TRAIL_MAX_SECONDS
    assert clamp_trail(0) == 0
    assert clamp_trail(-1) == 0


# --- load_trade_window ----------------------------------------------------


def test_load_trade_window_slices_correctly(tmp_path):
    """Synthetic 60 ticks at 1s spacing from 13:30:00. Window 13:30:30 ± 5s
    should return ticks 25-35 (11 rows)."""
    _write_tbbo_partition(
        tmp_path, symbol="NQ.c.0", date=dt.date(2026, 4, 27), rows=60
    )
    entry = dt.datetime(2026, 4, 27, 13, 30, 30)
    exit_ = dt.datetime(2026, 4, 27, 13, 30, 30)
    window_start, window_end, df = load_trade_window(
        symbol="NQ.c.0",
        entry_ts=entry,
        exit_ts=exit_,
        lead_seconds=5,
        trail_seconds=5,
        data_root=tmp_path,
    )
    assert window_start == dt.datetime(2026, 4, 27, 13, 30, 25)
    assert window_end == dt.datetime(2026, 4, 27, 13, 30, 35)
    assert len(df) == 11


def test_load_trade_window_returns_empty_df_when_no_partition(tmp_path):
    entry = dt.datetime(2026, 4, 27, 13, 30, 30)
    _, _, df = load_trade_window(
        symbol="NQ.c.0",
        entry_ts=entry,
        exit_ts=None,
        lead_seconds=60,
        trail_seconds=60,
        data_root=tmp_path,
    )
    assert len(df) == 0


def test_load_trade_window_caps_lead_trail_to_max(tmp_path):
    _write_tbbo_partition(
        tmp_path, symbol="NQ.c.0", date=dt.date(2026, 4, 27), rows=60
    )
    entry = dt.datetime(2026, 4, 27, 13, 30, 30)
    window_start, window_end, _ = load_trade_window(
        symbol="NQ.c.0",
        entry_ts=entry,
        exit_ts=entry,
        lead_seconds=99999,  # way over cap
        trail_seconds=99999,
        data_root=tmp_path,
    )
    assert (entry - window_start).total_seconds() == LEAD_MAX_SECONDS
    assert (window_end - entry).total_seconds() == TRAIL_MAX_SECONDS
