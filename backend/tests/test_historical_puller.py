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


def test_pull_month_writes_per_day_files(data_root: Path) -> None:
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
    assert len(files) == 5
    assert files[0].name == "GLBX.MDP3-mbp-1-2026-03-01.dbn"
    assert files[4].name == "GLBX.MDP3-mbp-1-2026-03-05.dbn"


def test_pull_month_skips_existing_files(data_root: Path) -> None:
    """Idempotent: existing files are not re-pulled."""
    # Pre-create one file as if a previous run got that day.
    existing = (
        data_root / "raw" / "historical" / "GLBX.MDP3-mbp-1-2026-03-01.dbn"
    )
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


def test_pull_month_continues_on_per_day_error(
    data_root: Path,
) -> None:
    """If one day's API call fails, the others still complete."""
    call_count = {"n": 0}

    def _flaky(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 2:
            raise RuntimeError("API timeout")
        store = MagicMock()
        ts = pd.Timestamp("2026-03-15 13:30:00", tz="UTC")
        df = pd.DataFrame([{"ts_event": ts, "symbol": "NQ.c.0"}]).set_index(
            "ts_event"
        )
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
        max_days=4,
    )
    assert result.days_attempted == 4
    assert result.days_written == 3
    assert len(result.errors) == 1
    assert "API timeout" in result.errors[0]


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


def test_parse_args_with_month() -> None:
    args = historical._parse_args(["--month", "2026-03", "--max-days", "5"])
    assert args.month == "2026-03"
    assert args.max_days == 5
