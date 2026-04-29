"""Tests for app.data.reader — partition globbing, projection, resampling."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from app.data import read_bars, read_tbbo
from app.data.reader import _date_range, _parse_date, add_mid_and_spread
from app.data.schema import BARS_1M_SCHEMA, TBBO_SCHEMA


# --- Path helpers --------------------------------------------------------


def _write_tbbo_partition(
    data_root: Path,
    *,
    symbol: str,
    date: dt.date,
    rows: int = 5,
) -> Path:
    """Drop a small TBBO parquet at the Hive-partitioned path."""
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
    table = pa.Table.from_pandas(df, schema=TBBO_SCHEMA.pa_schema, preserve_index=False)
    pq.write_table(table, out)
    return out


def _write_bars_1m_partition(
    data_root: Path,
    *,
    symbol: str,
    date: dt.date,
    minutes: int = 60,
) -> Path:
    out = (
        data_root
        / "processed"
        / "bars"
        / "timeframe=1m"
        / f"symbol={symbol}"
        / f"date={date.isoformat()}"
        / "part-000.parquet"
    )
    out.parent.mkdir(parents=True, exist_ok=True)

    start = pd.Timestamp(date, tz="UTC") + pd.Timedelta("13:30:00")
    rows = []
    for i in range(minutes):
        ts = start + pd.Timedelta(minutes=i)
        base = 21000.0 + i * 0.25
        rows.append(
            {
                "ts_event": ts,
                "symbol": symbol,
                "open": base,
                "high": base + 0.5,
                "low": base - 0.5,
                "close": base + 0.25,
                "volume": 100,
                "trade_count": 10,
                "vwap": base + 0.1,
            }
        )
    df = pd.DataFrame(rows)
    table = pa.Table.from_pandas(df, schema=BARS_1M_SCHEMA.pa_schema, preserve_index=False)
    pq.write_table(table, out)
    return out


@pytest.fixture
def data_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "data"
    root.mkdir()
    monkeypatch.setenv("BS_DATA_ROOT", str(root))
    return root


# --- Date helpers -------------------------------------------------------


def test_parse_date_iso_string() -> None:
    assert _parse_date("2026-04-24") == dt.date(2026, 4, 24)


def test_parse_date_passthrough() -> None:
    assert _parse_date(dt.date(2026, 4, 24)) == dt.date(2026, 4, 24)


def test_date_range_half_open() -> None:
    out = _date_range(dt.date(2026, 4, 24), dt.date(2026, 4, 27))
    assert out == [
        dt.date(2026, 4, 24),
        dt.date(2026, 4, 25),
        dt.date(2026, 4, 26),
    ]


def test_date_range_empty_when_end_le_start() -> None:
    assert _date_range(dt.date(2026, 4, 24), dt.date(2026, 4, 24)) == []


# --- TBBO read ----------------------------------------------------------


def test_read_tbbo_single_day(data_root: Path) -> None:
    _write_tbbo_partition(data_root, symbol="NQ.c.0", date=dt.date(2026, 4, 24), rows=10)

    df = read_tbbo(symbol="NQ.c.0", start="2026-04-24", end="2026-04-25")
    assert len(df) == 10
    assert set(df.columns).issuperset({"ts_event", "symbol", "price", "bid_px", "ask_px"})
    assert (df["symbol"] == "NQ.c.0").all()


def test_read_tbbo_multi_day(data_root: Path) -> None:
    _write_tbbo_partition(data_root, symbol="NQ.c.0", date=dt.date(2026, 4, 24), rows=3)
    _write_tbbo_partition(data_root, symbol="NQ.c.0", date=dt.date(2026, 4, 25), rows=4)
    _write_tbbo_partition(data_root, symbol="NQ.c.0", date=dt.date(2026, 4, 26), rows=2)

    df = read_tbbo(symbol="NQ.c.0", start="2026-04-24", end="2026-04-27")
    assert len(df) == 9


def test_read_tbbo_skips_missing_days_silently(data_root: Path) -> None:
    _write_tbbo_partition(data_root, symbol="NQ.c.0", date=dt.date(2026, 4, 24), rows=5)
    # No file for 4-25.
    _write_tbbo_partition(data_root, symbol="NQ.c.0", date=dt.date(2026, 4, 26), rows=5)

    df = read_tbbo(symbol="NQ.c.0", start="2026-04-24", end="2026-04-27")
    assert len(df) == 10


def test_read_tbbo_empty_range_returns_empty(data_root: Path) -> None:
    df = read_tbbo(symbol="NQ.c.0", start="2026-04-24", end="2026-04-25")
    assert len(df) == 0


def test_read_tbbo_column_projection(data_root: Path) -> None:
    _write_tbbo_partition(data_root, symbol="NQ.c.0", date=dt.date(2026, 4, 24), rows=3)
    df = read_tbbo(
        symbol="NQ.c.0",
        start="2026-04-24",
        end="2026-04-25",
        columns=["price", "size"],
    )
    # Sort key gets prepended automatically.
    assert "ts_event" in df.columns
    assert "price" in df.columns
    assert "size" in df.columns
    assert "bid_px" not in df.columns


def test_read_tbbo_returns_pyarrow_table_when_requested(data_root: Path) -> None:
    _write_tbbo_partition(data_root, symbol="NQ.c.0", date=dt.date(2026, 4, 24), rows=3)
    table = read_tbbo(
        symbol="NQ.c.0",
        start="2026-04-24",
        end="2026-04-25",
        as_pandas=False,
    )
    assert isinstance(table, pa.Table)
    assert table.num_rows == 3


def test_symbol_isolation_no_leak(data_root: Path) -> None:
    """Writing NQ.c.0 partition should not surface in ES.c.0 reads."""
    _write_tbbo_partition(data_root, symbol="NQ.c.0", date=dt.date(2026, 4, 24), rows=3)
    df = read_tbbo(symbol="ES.c.0", start="2026-04-24", end="2026-04-25")
    assert len(df) == 0


# --- Bar read + resample -----------------------------------------------


def test_read_bars_1m_passthrough(data_root: Path) -> None:
    _write_bars_1m_partition(data_root, symbol="NQ.c.0", date=dt.date(2026, 4, 24), minutes=60)
    df = read_bars(
        symbol="NQ.c.0", timeframe="1m", start="2026-04-24", end="2026-04-25"
    )
    assert len(df) == 60


def test_read_bars_5m_aggregates_correctly(data_root: Path) -> None:
    _write_bars_1m_partition(data_root, symbol="NQ.c.0", date=dt.date(2026, 4, 24), minutes=60)
    df_5m = read_bars(
        symbol="NQ.c.0", timeframe="5m", start="2026-04-24", end="2026-04-25"
    )
    # 60 1m bars at 5m = 12 bars
    assert len(df_5m) == 12

    # Each 5m bar should have volume = sum of 5 underlying 1m bars (5 * 100 = 500)
    assert (df_5m["volume"] == 500).all()
    # trade_count likewise (5 * 10 = 50)
    assert (df_5m["trade_count"] == 50).all()


def test_read_bars_1h_aggregates(data_root: Path) -> None:
    _write_bars_1m_partition(data_root, symbol="NQ.c.0", date=dt.date(2026, 4, 24), minutes=60)
    df_1h = read_bars(
        symbol="NQ.c.0", timeframe="1h", start="2026-04-24", end="2026-04-25"
    )
    # Bars start at 13:30 UTC. Floored to hours, that's two buckets:
    # 13:00 (gets the 13:30-13:59 bars, 30 of them) and 14:00 (the 14:00-14:29
    # bars, 30 of them). Real session data would span more hours.
    assert len(df_1h) == 2
    # Both hour-buckets together = full 60 1m bars × 100 volume each = 6000
    assert df_1h["volume"].sum() == 6000


def test_read_bars_unknown_timeframe_raises(data_root: Path) -> None:
    with pytest.raises(ValueError, match="unknown timeframe"):
        read_bars(symbol="NQ.c.0", timeframe="7m", start="2026-04-24", end="2026-04-25")


def test_read_bars_empty_returns_empty(data_root: Path) -> None:
    df = read_bars(
        symbol="NQ.c.0", timeframe="5m", start="2026-04-24", end="2026-04-25"
    )
    assert len(df) == 0


def _write_bars_with_custom_vwaps(
    data_root: Path,
    *,
    symbol: str,
    date: dt.date,
    rows: list[dict],
) -> Path:
    """Write a 1m partition with caller-supplied VWAP/volume rows.

    Used by the resample-VWAP regression test so we can pin specific
    sub-bar values and verify the pool VWAP comes back volume-weighted.
    """
    out = (
        data_root
        / "processed"
        / "bars"
        / "timeframe=1m"
        / f"symbol={symbol}"
        / f"date={date.isoformat()}"
        / "part-000.parquet"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    table = pa.Table.from_pandas(
        df, schema=BARS_1M_SCHEMA.pa_schema, preserve_index=False
    )
    pq.write_table(table, out)
    return out


def test_read_bars_resampled_vwap_is_volume_weighted(data_root: Path) -> None:
    """Codex review 2026-04-29: the higher-timeframe VWAP was being
    computed as a plain mean of sub-bar VWAPs, which silently re-weights
    every sub-bar equally regardless of how much volume traded inside it.
    Lock the volume-weighted formula in.

    Setup: five 1m bars within a single 5m bucket, all on a single day.
    Three bars traded at vwap=100 with volume=1, two bars traded at
    vwap=200 with volume=99. Plain mean = 140; volume-weighted mean =
    sum(vwap*volume)/sum(volume) = (3*100 + 198*200)/(3 + 198) ≈ 198.5.
    """
    base_ts = pd.Timestamp(dt.date(2026, 4, 24), tz="UTC") + pd.Timedelta("13:30:00")
    rows = []
    for i in range(5):
        # First three bars: vwap=100 vol=1; last two: vwap=200 vol=99.
        is_heavy = i >= 3
        vwap = 200.0 if is_heavy else 100.0
        volume = 99 if is_heavy else 1
        rows.append(
            {
                "ts_event": base_ts + pd.Timedelta(minutes=i),
                "symbol": "NQ.c.0",
                "open": vwap,
                "high": vwap,
                "low": vwap,
                "close": vwap,
                "volume": volume,
                "trade_count": volume,
                "vwap": vwap,
            }
        )
    _write_bars_with_custom_vwaps(
        data_root,
        symbol="NQ.c.0",
        date=dt.date(2026, 4, 24),
        rows=rows,
    )

    df_5m = read_bars(
        symbol="NQ.c.0",
        timeframe="5m",
        start="2026-04-24",
        end="2026-04-25",
    )
    assert len(df_5m) == 1
    bar = df_5m.iloc[0]
    expected_weighted = (3 * 100 * 1 + 2 * 200 * 99) / (3 * 1 + 2 * 99)
    plain_mean = (3 * 100 + 2 * 200) / 5  # = 140 — what the bug returned
    assert bar["volume"] == 3 + 2 * 99
    assert abs(bar["vwap"] - expected_weighted) < 0.01, (
        f"expected weighted {expected_weighted}, got {bar['vwap']}"
    )
    assert abs(bar["vwap"] - plain_mean) > 50, (
        "vwap is suspiciously close to the plain mean — bug may have regressed"
    )


def test_read_bars_resampled_vwap_handles_nan_source(data_root: Path) -> None:
    """Codex re-review 2026-04-29: parquet_mirror and legacy_ohlcv_import
    both write source bars with vwap=NaN and positive volume (OHLCV-only
    DBN files). The resample must NOT silently turn those into resampled
    vwap=0 — substitute close before weighting."""
    import math

    base_ts = pd.Timestamp(dt.date(2026, 4, 24), tz="UTC") + pd.Timedelta("13:30:00")
    rows = [
        {
            "ts_event": base_ts + pd.Timedelta(minutes=i),
            "symbol": "NQ.c.0",
            "open": 21000.0 + i,
            "high": 21000.0 + i,
            "low": 21000.0 + i,
            "close": 21000.0 + i,
            "volume": 100,
            "trade_count": 0,
            "vwap": float("nan"),
        }
        for i in range(5)
    ]
    _write_bars_with_custom_vwaps(
        data_root,
        symbol="NQ.c.0",
        date=dt.date(2026, 4, 24),
        rows=rows,
    )
    df_5m = read_bars(
        symbol="NQ.c.0",
        timeframe="5m",
        start="2026-04-24",
        end="2026-04-25",
    )
    assert len(df_5m) == 1
    bar = df_5m.iloc[0]
    # Volume-weighted close: each sub-bar weighs equal (vol=100) so
    # result = mean(closes) = (21000 + 21001 + ... + 21004) / 5 = 21002
    expected = sum(21000 + i for i in range(5)) / 5
    assert abs(bar["vwap"] - expected) < 0.01, (
        f"expected {expected}, got {bar['vwap']}; pre-fix bug returned 0"
    )
    assert bar["vwap"] > 20000, "vwap collapsed to 0 — NaN substitution regressed"
    assert not math.isnan(bar["vwap"])


def test_read_bars_resampled_vwap_mixed_nan_and_real(data_root: Path) -> None:
    """Mixed bucket: some sub-bars have real vwap, others NaN. The
    weighted formula should use the real vwap where present and the
    close where NaN. Volume-weighting still applies."""
    base_ts = pd.Timestamp(dt.date(2026, 4, 24), tz="UTC") + pd.Timedelta("13:30:00")
    rows = []
    # Two bars with real vwap=100, vol=10 each → weight 20 toward vwap=100
    for i in range(2):
        rows.append(
            {
                "ts_event": base_ts + pd.Timedelta(minutes=i),
                "symbol": "NQ.c.0",
                "open": 100.0,
                "high": 100.0,
                "low": 100.0,
                "close": 999.0,  # will not be used because vwap is real
                "volume": 10,
                "trade_count": 1,
                "vwap": 100.0,
            }
        )
    # Three bars with vwap=NaN and close=200, vol=10 each → weight 30 toward 200
    for i in range(3):
        rows.append(
            {
                "ts_event": base_ts + pd.Timedelta(minutes=i + 2),
                "symbol": "NQ.c.0",
                "open": 200.0,
                "high": 200.0,
                "low": 200.0,
                "close": 200.0,
                "volume": 10,
                "trade_count": 0,
                "vwap": float("nan"),
            }
        )
    _write_bars_with_custom_vwaps(
        data_root,
        symbol="NQ.c.0",
        date=dt.date(2026, 4, 24),
        rows=rows,
    )
    df_5m = read_bars(
        symbol="NQ.c.0",
        timeframe="5m",
        start="2026-04-24",
        end="2026-04-25",
    )
    assert len(df_5m) == 1
    # Expected: (2 * 100 * 10 + 3 * 200 * 10) / (5 * 10) = 8000 / 50 = 160
    expected = (2 * 100 * 10 + 3 * 200 * 10) / (5 * 10)
    bar = df_5m.iloc[0]
    assert abs(bar["vwap"] - expected) < 0.01


def test_read_bars_resampled_vwap_handles_zero_volume(data_root: Path) -> None:
    """A bucket with all-zero-volume sub-bars (rare but happens during
    halts / outages) should return a sane VWAP — fall back to close
    rather than NaN/Inf."""
    base_ts = pd.Timestamp(dt.date(2026, 4, 24), tz="UTC") + pd.Timedelta("13:30:00")
    rows = [
        {
            "ts_event": base_ts + pd.Timedelta(minutes=i),
            "symbol": "NQ.c.0",
            "open": 21000.0,
            "high": 21000.0,
            "low": 21000.0,
            "close": 21000.0 + i * 0.25,
            "volume": 0,
            "trade_count": 0,
            "vwap": 21000.0,
        }
        for i in range(5)
    ]
    _write_bars_with_custom_vwaps(
        data_root,
        symbol="NQ.c.0",
        date=dt.date(2026, 4, 24),
        rows=rows,
    )
    df_5m = read_bars(
        symbol="NQ.c.0",
        timeframe="5m",
        start="2026-04-24",
        end="2026-04-25",
    )
    assert len(df_5m) == 1
    bar = df_5m.iloc[0]
    assert bar["volume"] == 0
    # Falls back to close (last sub-bar) when no volume to weight by.
    assert bar["vwap"] == bar["close"]
    import math
    assert not math.isnan(bar["vwap"]) and not math.isinf(bar["vwap"])


# --- Derived columns ---------------------------------------------------


def test_add_mid_and_spread_computes_correctly() -> None:
    table = pa.table(
        {
            "bid_px": [100.0, 101.0],
            "ask_px": [101.0, 102.0],
            "ts_event": pa.array(
                [pa.scalar(0, type=pa.timestamp("ns", tz="UTC"))] * 2
            ),
        }
    )
    out = add_mid_and_spread(table)
    assert out.column("mid_px").to_pylist() == [100.5, 101.5]
    assert out.column("spread").to_pylist() == [1.0, 1.0]


def test_add_mid_and_spread_requires_columns() -> None:
    table = pa.table({"x": [1, 2]})
    with pytest.raises(ValueError, match="missing bid_px"):
        add_mid_and_spread(table)
