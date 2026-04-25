"""Tests for the parquet mirror daemon.

Mocks Databento's DBNStore so the test suite has no live-data dependency.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pyarrow.parquet as pq
import pytest

from app.ingest import parquet_mirror


def _write_old_dbn(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Real DBN content doesn't matter — we mock the loader. Bytes just
    # need to exist so the file appears on disk and gets walked.
    path.write_bytes(b"FAKE_DBN_CONTENT")
    old = path.stat().st_mtime - 600  # 10 min ago — past SKIP_RECENT_SEC
    os.utime(path, (old, old))


def _fake_dbn_store(symbols_to_rows: dict[str, int]) -> MagicMock:
    """Build a fake DBNStore whose to_df() returns a multi-symbol frame."""
    rows = []
    ts = pd.Timestamp("2026-04-24 13:30:00", tz="UTC")
    for sym, n in symbols_to_rows.items():
        for i in range(n):
            rows.append({
                "ts_event": ts + pd.Timedelta(seconds=i),
                "symbol": sym,
                "price": 21000.0 + i,
                "size": 1,
            })
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


def test_mirror_creates_per_symbol_parquet(data_root: Path) -> None:
    dbn = data_root / "raw" / "live" / "GLBX.MDP3-tbbo-2026-04-24.dbn"
    _write_old_dbn(dbn)

    fake_store = _fake_dbn_store({"NQ.c.0": 3, "ES.c.0": 5})
    with patch.object(
        parquet_mirror.db.DBNStore, "from_file", return_value=fake_store
    ):
        result = parquet_mirror.mirror_warehouse(data_root)

    assert result.scanned == 1
    assert result.converted == 2  # one parquet per symbol
    assert result.errors == []

    nq_parquet = data_root / "parquet" / "NQ.c.0" / "tbbo" / "2026-04-24.parquet"
    es_parquet = data_root / "parquet" / "ES.c.0" / "tbbo" / "2026-04-24.parquet"
    assert nq_parquet.exists()
    assert es_parquet.exists()

    nq_table = pq.read_table(nq_parquet)
    es_table = pq.read_table(es_parquet)
    assert nq_table.num_rows == 3
    assert es_table.num_rows == 5


def test_mirror_idempotent(data_root: Path) -> None:
    dbn = data_root / "raw" / "live" / "GLBX.MDP3-tbbo-2026-04-24.dbn"
    _write_old_dbn(dbn)
    fake_store = _fake_dbn_store({"NQ.c.0": 1})

    with patch.object(
        parquet_mirror.db.DBNStore, "from_file", return_value=fake_store
    ):
        first = parquet_mirror.mirror_warehouse(data_root)
        second = parquet_mirror.mirror_warehouse(data_root)

    assert first.converted == 1
    assert second.converted == 0
    assert second.skipped_unchanged == 1


def test_mirror_skips_recent_files(data_root: Path) -> None:
    """File modified in the last minute is in-progress; don't read it."""
    dbn = data_root / "raw" / "live" / "GLBX.MDP3-tbbo-2026-04-24.dbn"
    dbn.parent.mkdir(parents=True, exist_ok=True)
    dbn.write_bytes(b"in-progress")
    # mtime is now -> within SKIP_RECENT_SEC

    with patch.object(parquet_mirror.db.DBNStore, "from_file") as mock:
        result = parquet_mirror.mirror_warehouse(data_root)
        mock.assert_not_called()  # wasn't even loaded

    assert result.skipped_recent == 1
    assert result.converted == 0


def test_mirror_skips_unrecognized_filenames(data_root: Path) -> None:
    junk = data_root / "raw" / "live" / "weird-name.dbn"
    _write_old_dbn(junk)

    with patch.object(parquet_mirror.db.DBNStore, "from_file") as mock:
        result = parquet_mirror.mirror_warehouse(data_root)
        mock.assert_not_called()

    assert result.skipped_unrecognized == 1
    assert result.converted == 0


def test_mirror_handles_empty_dbn(data_root: Path) -> None:
    """DBN with no records (e.g. ingester started, market closed, no ticks)."""
    dbn = data_root / "raw" / "live" / "GLBX.MDP3-tbbo-2026-04-24.dbn"
    _write_old_dbn(dbn)
    fake_store = MagicMock()
    fake_store.to_df.return_value = pd.DataFrame()  # empty

    with patch.object(
        parquet_mirror.db.DBNStore, "from_file", return_value=fake_store
    ):
        result = parquet_mirror.mirror_warehouse(data_root)

    assert result.scanned == 1
    assert result.converted == 0
    assert result.errors == []


def test_mirror_walks_both_live_and_historical(data_root: Path) -> None:
    live_dbn = data_root / "raw" / "live" / "GLBX.MDP3-tbbo-2026-04-24.dbn"
    hist_dbn = (
        data_root / "raw" / "historical" / "GLBX.MDP3-mbp-1-2026-03-15.dbn"
    )
    _write_old_dbn(live_dbn)
    _write_old_dbn(hist_dbn)

    fake_store = _fake_dbn_store({"NQ.c.0": 1})
    with patch.object(
        parquet_mirror.db.DBNStore, "from_file", return_value=fake_store
    ):
        result = parquet_mirror.mirror_warehouse(data_root)

    assert result.scanned == 2
    assert result.converted == 2
    assert (
        data_root / "parquet" / "NQ.c.0" / "tbbo" / "2026-04-24.parquet"
    ).exists()
    assert (
        data_root / "parquet" / "NQ.c.0" / "mbp-1" / "2026-03-15.parquet"
    ).exists()


def test_mirror_returns_503_when_root_missing(tmp_path: Path) -> None:
    nonexistent = tmp_path / "nope"
    result = parquet_mirror.mirror_warehouse(nonexistent)
    assert len(result.errors) == 1
    assert "does not exist" in result.errors[0]
