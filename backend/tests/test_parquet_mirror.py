"""Tests for the parquet mirror daemon (Hive layout, manifests, 1m bars)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pyarrow.parquet as pq
import pytest

from app.ingest import parquet_mirror


def _write_old_dbn(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"FAKE_DBN_CONTENT")
    old = path.stat().st_mtime - 600
    os.utime(path, (old, old))


def _fake_dbn_store(symbols_to_rows: dict[str, int]) -> MagicMock:
    """DBNStore-like mock whose to_df() returns a TBBO-shaped multi-symbol frame."""
    rows = []
    base_ts = pd.Timestamp("2026-04-24 13:30:00", tz="UTC")
    for sym, n in symbols_to_rows.items():
        for i in range(n):
            rows.append(
                {
                    "ts_event": base_ts + pd.Timedelta(seconds=i),
                    "ts_recv": base_ts + pd.Timedelta(seconds=i),
                    "symbol": sym,
                    "action": "T",
                    "side": "A",
                    "price": 21000.0 + i,
                    "size": 1,
                    "bid_px_00": 20999.5,
                    "ask_px_00": 21000.5,
                    "bid_sz_00": 5,
                    "ask_sz_00": 7,
                    "publisher_id": 1,
                    "instrument_id": 12345,
                    "sequence": i,
                }
            )
    df = pd.DataFrame(rows).set_index("ts_event")

    store = MagicMock()
    store.to_df.return_value = df
    return store


@pytest.fixture
def data_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "data"
    (root / "raw" / "live").mkdir(parents=True)
    (root / "raw" / "historical").mkdir(parents=True)
    monkeypatch.setenv("BS_DATA_ROOT", str(root))
    return root


def _hive_raw_path(data_root: Path, schema: str, symbol: str, date: str) -> Path:
    return (
        data_root
        / "raw"
        / "databento"
        / schema
        / f"symbol={symbol}"
        / f"date={date}"
        / "part-000.parquet"
    )


def _hive_bars_path(data_root: Path, symbol: str, date: str) -> Path:
    return (
        data_root
        / "processed"
        / "bars"
        / "timeframe=1m"
        / f"symbol={symbol}"
        / f"date={date}"
        / "part-000.parquet"
    )


def _manifest_path(data_root: Path, date: str, schema: str) -> Path:
    return (
        data_root
        / "manifests"
        / "ingest_runs"
        / f"{date}_{schema}_manifest.json"
    )


# --- Core behavior ------------------------------------------------------


def test_mirror_creates_hive_partitions_for_each_symbol(data_root: Path) -> None:
    dbn = data_root / "raw" / "live" / "GLBX.MDP3-tbbo-2026-04-24.dbn"
    _write_old_dbn(dbn)
    fake_store = _fake_dbn_store({"NQ.c.0": 3, "ES.c.0": 5})

    with patch.object(
        parquet_mirror.db.DBNStore, "from_file", return_value=fake_store
    ):
        result = parquet_mirror.mirror_warehouse(data_root)

    # 2 symbols × 2 outputs (raw + bars) = 4 partitions
    assert result.converted_dbn == 1
    assert result.converted_partitions == 4
    assert result.errors == []

    assert _hive_raw_path(data_root, "tbbo", "NQ.c.0", "2026-04-24").exists()
    assert _hive_raw_path(data_root, "tbbo", "ES.c.0", "2026-04-24").exists()
    assert _hive_bars_path(data_root, "NQ.c.0", "2026-04-24").exists()
    assert _hive_bars_path(data_root, "ES.c.0", "2026-04-24").exists()


def test_mirror_writes_manifest(data_root: Path) -> None:
    dbn = data_root / "raw" / "live" / "GLBX.MDP3-tbbo-2026-04-24.dbn"
    _write_old_dbn(dbn)
    fake_store = _fake_dbn_store({"NQ.c.0": 5})
    with patch.object(
        parquet_mirror.db.DBNStore, "from_file", return_value=fake_store
    ):
        parquet_mirror.mirror_warehouse(data_root)

    mp = _manifest_path(data_root, "2026-04-24", "tbbo")
    assert mp.exists()
    payload = json.loads(mp.read_text(encoding="utf-8"))
    assert payload["date"] == "2026-04-24"
    assert payload["data_schema"] == "tbbo"
    assert payload["status"] == "complete"
    assert len(payload["outputs"]) == 2  # raw + bars
    assert payload["source"]["sha256"]
    assert payload["validation"]["row_count_ok"] is True


def test_mirror_embeds_parquet_metadata(data_root: Path) -> None:
    dbn = data_root / "raw" / "live" / "GLBX.MDP3-tbbo-2026-04-24.dbn"
    _write_old_dbn(dbn)
    fake_store = _fake_dbn_store({"NQ.c.0": 3})
    with patch.object(
        parquet_mirror.db.DBNStore, "from_file", return_value=fake_store
    ):
        parquet_mirror.mirror_warehouse(data_root)

    raw = _hive_raw_path(data_root, "tbbo", "NQ.c.0", "2026-04-24")
    metadata = pq.read_metadata(raw).metadata
    # pyarrow returns metadata as bytes-keyed dict.
    assert b"bs.source.kind" in metadata
    assert metadata[b"bs.source.kind"] == b"dbn"
    assert b"bs.generator.name" in metadata
    assert metadata[b"bs.generator.name"] == b"parquet_mirror"
    assert b"bs.schema.name" in metadata
    assert metadata[b"bs.schema.name"] == b"tbbo"
    assert b"bs.ts_event.min" in metadata


def test_bars_have_correct_ohlcv(data_root: Path) -> None:
    """1m bar should aggregate the 3-second window's trades."""
    dbn = data_root / "raw" / "live" / "GLBX.MDP3-tbbo-2026-04-24.dbn"
    _write_old_dbn(dbn)
    fake_store = _fake_dbn_store({"NQ.c.0": 3})  # 3 trades at 1-sec intervals
    with patch.object(
        parquet_mirror.db.DBNStore, "from_file", return_value=fake_store
    ):
        parquet_mirror.mirror_warehouse(data_root)

    bars = pq.ParquetFile(
        str(_hive_bars_path(data_root, "NQ.c.0", "2026-04-24"))
    ).read().to_pandas()
    assert len(bars) == 1  # all 3 trades within the same minute
    assert bars["open"].iloc[0] == 21000.0
    assert bars["high"].iloc[0] == 21002.0
    assert bars["low"].iloc[0] == 21000.0
    assert bars["close"].iloc[0] == 21002.0
    assert bars["volume"].iloc[0] == 3
    assert bars["trade_count"].iloc[0] == 3


# --- Idempotency --------------------------------------------------------


def test_mirror_idempotent(data_root: Path) -> None:
    dbn = data_root / "raw" / "live" / "GLBX.MDP3-tbbo-2026-04-24.dbn"
    _write_old_dbn(dbn)
    fake_store = _fake_dbn_store({"NQ.c.0": 2})

    with patch.object(
        parquet_mirror.db.DBNStore, "from_file", return_value=fake_store
    ):
        first = parquet_mirror.mirror_warehouse(data_root)
        second = parquet_mirror.mirror_warehouse(data_root)

    assert first.converted_partitions == 2
    assert second.converted_partitions == 0
    assert second.skipped_unchanged == 1


def test_rebuild_flag_forces_re_emit(data_root: Path) -> None:
    dbn = data_root / "raw" / "live" / "GLBX.MDP3-tbbo-2026-04-24.dbn"
    _write_old_dbn(dbn)
    fake_store = _fake_dbn_store({"NQ.c.0": 2})

    with patch.object(
        parquet_mirror.db.DBNStore, "from_file", return_value=fake_store
    ):
        parquet_mirror.mirror_warehouse(data_root)
        rebuild = parquet_mirror.mirror_warehouse(data_root, rebuild=True)

    assert rebuild.converted_partitions == 2  # forced re-emit


# --- Skip / error cases -------------------------------------------------


def test_mirror_skips_recent_files(data_root: Path) -> None:
    dbn = data_root / "raw" / "live" / "GLBX.MDP3-tbbo-2026-04-24.dbn"
    dbn.parent.mkdir(parents=True, exist_ok=True)
    dbn.write_bytes(b"in-progress")  # mtime = now

    with patch.object(parquet_mirror.db.DBNStore, "from_file") as mock:
        result = parquet_mirror.mirror_warehouse(data_root)
        mock.assert_not_called()

    assert result.skipped_recent == 1
    assert result.converted_partitions == 0


def test_mirror_skips_unrecognized_filenames(data_root: Path) -> None:
    junk = data_root / "raw" / "live" / "weird-name.dbn"
    _write_old_dbn(junk)

    with patch.object(parquet_mirror.db.DBNStore, "from_file") as mock:
        result = parquet_mirror.mirror_warehouse(data_root)
        mock.assert_not_called()

    assert result.skipped_unrecognized == 1
    assert result.converted_partitions == 0


def test_mirror_handles_empty_dbn(data_root: Path) -> None:
    dbn = data_root / "raw" / "live" / "GLBX.MDP3-tbbo-2026-04-24.dbn"
    _write_old_dbn(dbn)
    fake_store = MagicMock()
    fake_store.to_df.return_value = pd.DataFrame()

    with patch.object(
        parquet_mirror.db.DBNStore, "from_file", return_value=fake_store
    ):
        result = parquet_mirror.mirror_warehouse(data_root)

    assert result.converted_partitions == 0
    assert result.errors == []
    # No manifest written for empty days.
    assert not _manifest_path(data_root, "2026-04-24", "tbbo").exists()


def test_mirror_walks_both_live_and_historical(data_root: Path) -> None:
    live = data_root / "raw" / "live" / "GLBX.MDP3-tbbo-2026-04-24.dbn"
    hist = data_root / "raw" / "historical" / "GLBX.MDP3-mbp-1-2026-03-15.dbn"
    _write_old_dbn(live)
    _write_old_dbn(hist)

    fake_store = _fake_dbn_store({"NQ.c.0": 1})
    with patch.object(
        parquet_mirror.db.DBNStore, "from_file", return_value=fake_store
    ):
        result = parquet_mirror.mirror_warehouse(data_root)

    assert result.scanned == 2
    # Two DBN, one symbol each, two outputs each = 4
    assert result.converted_partitions == 4
    assert _hive_raw_path(data_root, "tbbo", "NQ.c.0", "2026-04-24").exists()
    assert _hive_raw_path(data_root, "mbp-1", "NQ.c.0", "2026-03-15").exists()


def test_mirror_returns_error_when_root_missing(tmp_path: Path) -> None:
    nonexistent = tmp_path / "nope"
    result = parquet_mirror.mirror_warehouse(nonexistent)
    assert len(result.errors) == 1
    assert "does not exist" in result.errors[0]
