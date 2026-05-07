"""Tests for the daily Databento puller.

Mocks the Databento Historical client so the suite has no live API
dependency. Mirrors the pattern in test_historical_puller.py.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

from app.ingest import daily


# --- Fixtures ------------------------------------------------------------


@pytest.fixture
def data_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "data"
    monkeypatch.setenv("BS_DATA_ROOT", str(root))
    monkeypatch.setenv("DATABENTO_API_KEY", "fake-key-for-tests")
    return root


def _fake_client(rows_per_call: int, cost_per_quote: float = 0.0) -> MagicMock:
    """Historical client that returns a small DBN response per get_range
    call and a fixed cost per get_cost call."""

    def _make_response(*_args, **_kwargs):
        store = MagicMock()
        if rows_per_call == 0:
            store.to_df.return_value = pd.DataFrame()
        else:
            ts = pd.Timestamp("2026-04-30 13:30:00", tz="UTC")
            df = pd.DataFrame(
                [
                    {"ts_event": ts + pd.Timedelta(seconds=i), "symbol": "X"}
                    for i in range(rows_per_call)
                ]
            ).set_index("ts_event")
            store.to_df.return_value = df

            def _to_file(path: str) -> None:
                Path(path).write_bytes(b"FAKE_DBN" * (rows_per_call or 1))

            store.to_file.side_effect = _to_file
        return store

    client = MagicMock()
    client.timeseries.get_range.side_effect = _make_response
    client.metadata.get_cost.return_value = cost_per_quote
    return client


# --- Date helpers --------------------------------------------------------


def test_yesterday_utc_typical() -> None:
    assert daily.yesterday_utc(dt.date(2026, 5, 4)) == dt.date(2026, 5, 3)


def test_yesterday_utc_handles_month_rollover() -> None:
    assert daily.yesterday_utc(dt.date(2026, 5, 1)) == dt.date(2026, 4, 30)


def test_date_range_inclusive_start_exclusive_end() -> None:
    days = daily.date_range(dt.date(2026, 4, 28), dt.date(2026, 5, 1))
    assert days == [
        dt.date(2026, 4, 28),
        dt.date(2026, 4, 29),
        dt.date(2026, 4, 30),
    ]


def test_date_range_empty_when_end_le_start() -> None:
    assert daily.date_range(dt.date(2026, 5, 1), dt.date(2026, 5, 1)) == []
    assert daily.date_range(dt.date(2026, 5, 2), dt.date(2026, 5, 1)) == []


# --- Cost pre-flight -----------------------------------------------------


def test_cost_quote_sums_both_schemas(data_root: Path) -> None:
    """Each schema gets one get_cost call. Result is the sum."""
    client = _fake_client(rows_per_call=0, cost_per_quote=0.0)
    # Override per-call so we can verify the sum
    client.metadata.get_cost.side_effect = [1.50, 2.25]

    days = [dt.date(2026, 4, 30)]
    import logging
    logger = logging.getLogger("test")
    total = daily.quote_total_cost(client, days, logger)
    assert total == pytest.approx(3.75)
    assert client.metadata.get_cost.call_count == 2


def test_pull_days_aborts_when_quote_exceeds_threshold(data_root: Path) -> None:
    """Cost > threshold => no pulls happen, error recorded."""
    client = _fake_client(rows_per_call=10, cost_per_quote=5.0)
    days = [dt.date(2026, 4, 30)]
    result = daily.pull_days(
        days, client=client, cost_threshold_usd=1.0, data_root=data_root
    )
    assert result.cost_quote_usd == pytest.approx(10.0)  # 5 per schema * 2
    assert result.errors  # abort recorded
    assert "ABORT" in result.errors[0]
    # Crucially: get_range was NOT called
    assert client.timeseries.get_range.call_count == 0


def test_pull_days_proceeds_at_zero_cost(data_root: Path) -> None:
    """The hot path: trial returns $0 -> pulls go through."""
    client = _fake_client(rows_per_call=10, cost_per_quote=0.0)
    days = [dt.date(2026, 4, 30)]
    result = daily.pull_days(days, client=client, data_root=data_root)
    assert result.cost_quote_usd == 0.0
    assert not result.errors
    # 3 INDEX symbols + 10 OTHER symbols = 13 get_range calls per day
    assert client.timeseries.get_range.call_count == 13


def test_pull_days_dry_run_skips_pulls(data_root: Path) -> None:
    client = _fake_client(rows_per_call=10, cost_per_quote=0.0)
    days = [dt.date(2026, 4, 30)]
    result = daily.pull_days(
        days, client=client, dry_run=True, data_root=data_root
    )
    assert not result.errors
    assert client.timeseries.get_range.call_count == 0


def test_pull_days_writes_per_symbol_files(data_root: Path) -> None:
    """End-to-end happy path: per-symbol DBN files land in the right place."""
    client = _fake_client(rows_per_call=10, cost_per_quote=0.0)
    days = [dt.date(2026, 4, 30)]
    daily.pull_days(days, client=client, data_root=data_root)

    hist_dir = data_root / "raw" / "historical"
    assert hist_dir.exists()
    files = sorted(p.name for p in hist_dir.glob("*.dbn"))
    # 3 MBP-1 + 10 TBBO files for one day
    assert len(files) == 13
    # Spot-check naming convention from historical.file_for_date_symbol
    assert any("mbp-1" in f and "NQ.c.0" in f for f in files)
    assert any("tbbo" in f and "CL.c.0" in f for f in files)


def test_pull_days_idempotent_on_existing_files(data_root: Path) -> None:
    """A second pull over the same day re-quotes cost but doesn't re-download."""
    client = _fake_client(rows_per_call=10, cost_per_quote=0.0)
    days = [dt.date(2026, 4, 30)]
    daily.pull_days(days, client=client, data_root=data_root)
    first_call_count = client.timeseries.get_range.call_count

    # Second run with a fresh client mock
    client2 = _fake_client(rows_per_call=10, cost_per_quote=0.0)
    daily.pull_days(days, client=client2, data_root=data_root)
    # All 13 files exist => zero get_range calls on second run
    assert client2.timeseries.get_range.call_count == 0
    assert first_call_count == 13


def test_pull_days_empty_range_no_op(data_root: Path) -> None:
    """Empty day list: no errors, no cost calls, no pulls."""
    client = _fake_client(rows_per_call=10, cost_per_quote=0.0)
    result = daily.pull_days([], client=client, data_root=data_root)
    assert not result.errors
    assert result.days_attempted == 0
    assert client.metadata.get_cost.call_count == 0
    assert client.timeseries.get_range.call_count == 0


# --- CLI argument parsing ------------------------------------------------


def test_resolve_days_default_yesterday(monkeypatch: pytest.MonkeyPatch) -> None:
    """No flags -> [yesterday UTC]."""
    args = daily._parse_args([])
    days = daily._resolve_days(args)
    assert len(days) == 1
    assert days[0] == daily.yesterday_utc()


def test_resolve_days_explicit_date() -> None:
    args = daily._parse_args(["--date", "2026-04-30"])
    assert daily._resolve_days(args) == [dt.date(2026, 4, 30)]


def test_resolve_days_range() -> None:
    args = daily._parse_args(
        ["--start", "2026-04-28", "--end", "2026-05-01"]
    )
    days = daily._resolve_days(args)
    assert days == [
        dt.date(2026, 4, 28),
        dt.date(2026, 4, 29),
        dt.date(2026, 4, 30),
    ]
