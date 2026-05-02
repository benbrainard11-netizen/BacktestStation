"""Tests for the monthly historical MBP-1 puller.

Mocks the Databento Historical client so the suite has no live API
dependency.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

from app.ingest import historical


@pytest.fixture(autouse=True)
def _fast_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests need to exercise retry / backoff logic without spending real
    wall-clock time. Production constants stay generous (5/30/120/600s
    between retries, 1s throttle between symbols); tests run with both
    zeroed out."""
    monkeypatch.setattr(historical, "_RETRY_BACKOFFS_SEC", (0, 0, 0, 0))
    monkeypatch.setattr(historical, "_THROTTLE_BETWEEN_CALLS_SEC", 0.0)


@pytest.fixture
def data_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "data"
    monkeypatch.setenv("BS_DATA_ROOT", str(root))
    return root


def _fake_client(rows_per_day: int) -> MagicMock:
    """Build a Historical client whose get_range returns a DBNStore-like
    object with `rows_per_day` rows (or empty for 0)."""

    def _make_response(*_args, **_kwargs):
        store = MagicMock()
        if rows_per_day == 0:
            store.to_df.return_value = pd.DataFrame()
        else:
            ts = pd.Timestamp("2026-03-15 13:30:00", tz="UTC")
            df = pd.DataFrame(
                [
                    {"ts_event": ts + pd.Timedelta(seconds=i), "symbol": "NQ.c.0"}
                    for i in range(rows_per_day)
                ]
            ).set_index("ts_event")
            store.to_df.return_value = df

            # to_file writes some bytes — simulate a small DBN.
            def _to_file(path: str) -> None:
                Path(path).write_bytes(b"FAKE_DBN_PAYLOAD" * (rows_per_day or 1))

            store.to_file.side_effect = _to_file
        return store

    client = MagicMock()
    client.timeseries.get_range.side_effect = _make_response
    return client


# --- Date math -----------------------------------------------------------


def test_previous_month_handles_january_rollover() -> None:
    assert historical.previous_month(dt.date(2026, 1, 15)) == (2025, 12)


def test_previous_month_typical_case() -> None:
    assert historical.previous_month(dt.date(2026, 5, 1)) == (2026, 4)


def test_days_in_month() -> None:
    feb = historical.days_in_month(2026, 2)
    assert len(feb) == 28
    assert feb[0] == dt.date(2026, 2, 1)
    assert feb[-1] == dt.date(2026, 2, 28)
    leap = historical.days_in_month(2024, 2)
    assert len(leap) == 29


# --- Pull behavior -------------------------------------------------------


def test_pull_month_writes_per_symbol_files(data_root: Path) -> None:
    """Per-symbol-per-day layout: one DBN file per (date, symbol)."""
    client = _fake_client(rows_per_day=10)
    result = historical.pull_month(
        year=2026,
        month=3,
        client=client,
        data_root=data_root,
        max_days=5,
    )
    assert result.days_attempted == 5
    assert result.days_written == 5
    assert result.days_skipped_existing == 0
    assert result.days_skipped_empty == 0
    assert result.bytes_written > 0

    historical_dir = data_root / "raw" / "historical"
    files = sorted(historical_dir.glob("*.dbn"))
    # 5 days × 4 default symbols (NQ/ES/YM/RTY .c.0) = 20 files.
    assert len(files) == 5 * len(historical.SYMBOLS)
    # First and last file names follow the per-symbol pattern. SYMBOLS
    # are iterated in declared order; sort is alphanumeric so the first
    # alphabetically is ES.c.0 on day 03-01.
    names = {f.name for f in files}
    assert "GLBX.MDP3-mbp-1-2026-03-01-NQ.c.0.dbn" in names
    assert "GLBX.MDP3-mbp-1-2026-03-01-ES.c.0.dbn" in names
    assert "GLBX.MDP3-mbp-1-2026-03-05-RTY.c.0.dbn" in names


def test_pull_month_supports_custom_dataset_for_vx(data_root: Path) -> None:
    """VX futures live in Databento's CFE dataset, not the CME dataset."""
    client = _fake_client(rows_per_day=3)
    result = historical.pull_month(
        year=2026,
        month=3,
        client=client,
        data_root=data_root,
        max_days=1,
        schema="ohlcv-1m",
        dataset="XCBF.PITCH",
        symbols=["VX.n.0"],
    )
    assert result.days_attempted == 1
    assert result.days_written == 1

    path = data_root / "raw" / "historical" / "XCBF.PITCH-ohlcv-1m-2026-03-01-VX.n.0.dbn"
    assert path.exists()

    kwargs = client.timeseries.get_range.call_args.kwargs
    assert kwargs["dataset"] == "XCBF.PITCH"
    assert kwargs["schema"] == "ohlcv-1m"
    assert kwargs["symbols"] == ["VX.n.0"]
    assert kwargs["stype_in"] == "continuous"


def test_pull_month_skips_existing_files(data_root: Path) -> None:
    """Idempotent: existing files are not re-pulled."""
    # Pre-create one file as if a previous run got that day.
    existing = data_root / "raw" / "historical" / "GLBX.MDP3-mbp-1-2026-03-01.dbn"
    existing.parent.mkdir(parents=True, exist_ok=True)
    existing.write_bytes(b"existing")

    client = _fake_client(rows_per_day=5)
    result = historical.pull_month(
        year=2026,
        month=3,
        client=client,
        data_root=data_root,
        max_days=3,
    )
    assert result.days_attempted == 3
    assert result.days_skipped_existing == 1
    assert result.days_written == 2
    # Existing file untouched
    assert existing.read_bytes() == b"existing"


def test_pull_month_skips_empty_days(data_root: Path) -> None:
    """Days where Databento returns no data don't produce a file."""
    client = _fake_client(rows_per_day=0)  # always empty
    result = historical.pull_month(
        year=2026,
        month=3,
        client=client,
        data_root=data_root,
        max_days=4,
    )
    assert result.days_attempted == 4
    assert result.days_written == 0
    assert result.days_skipped_empty == 4
    assert list((data_root / "raw" / "historical").glob("*.dbn")) == []


def test_pull_month_continues_on_per_symbol_error(data_root: Path) -> None:
    """A permanent error on ONE symbol does not stop the day's other
    symbols from being pulled. Per-symbol errors are logged but do not
    propagate to `result.errors` (those are reserved for day-level
    failures inside `pull_month`)."""
    fail_once = {"done": False}

    def _flaky(*args, **kwargs):
        if not fail_once["done"]:
            fail_once["done"] = True
            # "Permission denied" is NOT in _TRANSIENT_ERROR_PATTERNS,
            # so the retry logic propagates it unchanged.
            raise RuntimeError("Permission denied: invalid API key")
        store = MagicMock()
        ts = pd.Timestamp("2026-03-15 13:30:00", tz="UTC")
        df = pd.DataFrame([{"ts_event": ts, "symbol": "NQ.c.0"}]).set_index("ts_event")
        store.to_df.return_value = df
        store.to_file.side_effect = lambda path: Path(path).write_bytes(b"X")
        return store

    client = MagicMock()
    client.timeseries.get_range.side_effect = _flaky

    result = historical.pull_month(
        year=2026,
        month=3,
        client=client,
        data_root=data_root,
        max_days=1,
    )
    # Day still counts as written because some symbols succeeded.
    assert result.days_attempted == 1
    assert result.days_written == 1
    assert result.days_skipped_empty == 0
    # Per-symbol failures stay log-only — `result.errors` is for
    # day-level pull_day exceptions, which didn't happen here.
    assert result.errors == []
    # Verify only 3 of 4 symbols produced a file on that day.
    files = list((data_root / "raw" / "historical").glob("GLBX.MDP3-mbp-1-2026-03-01-*.dbn"))
    assert len(files) == len(historical.SYMBOLS) - 1


def test_get_range_retries_on_transient_error(data_root: Path) -> None:
    """Transient Databento errors (503, timeout, etc.) are retried up
    to len(_RETRY_BACKOFFS_SEC) times before giving up."""
    call_count = {"n": 0}

    def _flaky(*args, **kwargs):
        call_count["n"] += 1
        # First call transient-fails, second succeeds.
        if call_count["n"] == 1:
            raise RuntimeError("503 Service Unavailable")
        store = MagicMock()
        ts = pd.Timestamp("2026-03-15 13:30:00", tz="UTC")
        df = pd.DataFrame([{"ts_event": ts, "symbol": "NQ.c.0"}]).set_index("ts_event")
        store.to_df.return_value = df
        store.to_file.side_effect = lambda path: Path(path).write_bytes(b"X")
        return store

    client = MagicMock()
    client.timeseries.get_range.side_effect = _flaky

    result = historical.pull_month(
        year=2026,
        month=3,
        client=client,
        data_root=data_root,
        max_days=1,
    )
    # All 4 symbols ultimately succeed (first symbol's call retries once
    # and succeeds; remaining 3 symbols succeed first try).
    assert result.days_written == 1
    assert result.errors == []
    files = list((data_root / "raw" / "historical").glob("GLBX.MDP3-mbp-1-2026-03-01-*.dbn"))
    assert len(files) == len(historical.SYMBOLS)
    # Total calls = 5 (4 symbols + 1 retry).
    assert call_count["n"] == len(historical.SYMBOLS) + 1


def test_pull_month_rejects_invalid_month() -> None:
    client = MagicMock()
    with pytest.raises(ValueError):
        historical.pull_month(year=2026, month=13, client=client)
    with pytest.raises(ValueError):
        historical.pull_month(year=2026, month=0, client=client)


# --- CLI -----------------------------------------------------------------


def test_parse_args_defaults_to_none() -> None:
    args = historical._parse_args([])
    assert args.month is None
    assert args.max_days is None
    assert args.dataset == historical.DATASET
    assert args.stype_in == historical.STYPE_IN


def test_parse_args_with_month() -> None:
    args = historical._parse_args(
        [
            "--month",
            "2026-03",
            "--max-days",
            "5",
            "--dataset",
            "XCBF.PITCH",
            "--stype-in",
            "continuous",
        ]
    )
    assert args.month == "2026-03"
    assert args.max_days == 5
    assert args.dataset == "XCBF.PITCH"
    assert args.stype_in == "continuous"
