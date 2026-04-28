"""Tests for the weekly gap-filler.

The module's public surface (scanning, gap detection, cost-gating, dry-run)
is exercised against a tmpdir warehouse. Live Databento calls are mocked
via the `client` injection point.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.ingest import gap_filler, historical


# --- iter_target_partitions ---------------------------------------------


def test_iter_target_partitions_excludes_weekends() -> None:
    today = dt.date(2026, 4, 30)  # Thursday
    targets = gap_filler.iter_target_partitions(1, ["NQ.c.0"], today=today)
    # April 2026 has 30 days. Weekdays in April 2026: 22 days.
    # But targets are capped at <= today (Apr 30), so all 22 weekdays count.
    assert len(targets) == 22
    # Confirm no weekend dates snuck in.
    for day, _ in targets:
        assert day.weekday() < 5


def test_iter_target_partitions_caps_at_today() -> None:
    """If today is mid-month, future days in the same month aren't
    targeted (the data hasn't happened yet)."""
    today = dt.date(2026, 4, 10)
    targets = gap_filler.iter_target_partitions(1, ["NQ.c.0"], today=today)
    days = {day for day, _ in targets}
    # No days after Apr 10.
    assert all(d <= today for d in days)


def test_iter_target_partitions_walks_n_months() -> None:
    today = dt.date(2026, 4, 30)
    targets_1 = gap_filler.iter_target_partitions(1, ["NQ.c.0"], today=today)
    targets_3 = gap_filler.iter_target_partitions(3, ["NQ.c.0"], today=today)
    # 3 months ≥ 1 month always.
    assert len(targets_3) > len(targets_1)
    # Earliest target should be in February for n=3 (Feb/Mar/Apr).
    earliest = min(day for day, _ in targets_3)
    assert earliest.month == 2 and earliest.year == 2026


def test_iter_target_partitions_multiplies_by_symbols() -> None:
    today = dt.date(2026, 4, 30)
    one_sym = gap_filler.iter_target_partitions(1, ["NQ.c.0"], today=today)
    four_sym = gap_filler.iter_target_partitions(
        1, ["NQ.c.0", "ES.c.0", "YM.c.0", "RTY.c.0"], today=today
    )
    assert len(four_sym) == len(one_sym) * 4


# --- existing_partitions ------------------------------------------------


def test_existing_partitions_recognizes_per_symbol_files(tmp_path: Path) -> None:
    historical_dir = tmp_path / "raw" / "historical"
    historical_dir.mkdir(parents=True)
    (historical_dir / "GLBX.MDP3-mbp-1-2026-03-15-NQ.c.0.dbn").write_bytes(b"X")
    (historical_dir / "GLBX.MDP3-mbp-1-2026-03-15-ES.c.0.dbn").write_bytes(b"Y")
    found = gap_filler.existing_partitions(tmp_path)
    assert (dt.date(2026, 3, 15), "NQ.c.0") in found
    assert (dt.date(2026, 3, 15), "ES.c.0") in found


def test_existing_partitions_treats_legacy_as_all_symbols(tmp_path: Path) -> None:
    """Legacy multi-symbol files have no symbol in the filename. We
    over-count (mark all configured symbols as present) rather than
    risk a re-pull."""
    historical_dir = tmp_path / "raw" / "historical"
    historical_dir.mkdir(parents=True)
    (historical_dir / "GLBX.MDP3-mbp-1-2026-03-01.dbn").write_bytes(b"X")
    found = gap_filler.existing_partitions(tmp_path)
    for sym in historical.SYMBOLS:
        assert (dt.date(2026, 3, 1), sym) in found


def test_existing_partitions_skips_empty_files(tmp_path: Path) -> None:
    historical_dir = tmp_path / "raw" / "historical"
    historical_dir.mkdir(parents=True)
    (historical_dir / "GLBX.MDP3-mbp-1-2026-03-15-NQ.c.0.dbn").touch()  # 0 bytes
    found = gap_filler.existing_partitions(tmp_path)
    assert (dt.date(2026, 3, 15), "NQ.c.0") not in found


def test_existing_partitions_returns_empty_when_dir_missing(tmp_path: Path) -> None:
    found = gap_filler.existing_partitions(tmp_path)
    assert found == set()


# --- compute_gaps -------------------------------------------------------


def test_compute_gaps_returns_only_missing() -> None:
    targets = [
        (dt.date(2026, 4, 27), "NQ.c.0"),
        (dt.date(2026, 4, 27), "ES.c.0"),
        (dt.date(2026, 4, 28), "NQ.c.0"),
    ]
    existing = {(dt.date(2026, 4, 27), "NQ.c.0")}
    gaps = gap_filler.compute_gaps(targets, existing)
    assert gaps == [
        (dt.date(2026, 4, 27), "ES.c.0"),
        (dt.date(2026, 4, 28), "NQ.c.0"),
    ]


# --- fill_gaps end-to-end -----------------------------------------------


def _fake_client(cost_map: dict[tuple[str, str], float]) -> MagicMock:
    """Build a Historical client whose metadata.get_cost looks up a map.
    Keys: (symbol, start_iso). Default cost: 0.0."""
    client = MagicMock()

    def _cost(*args, **kwargs):
        symbols = kwargs.get("symbols", [])
        start = kwargs.get("start", "")
        if symbols and start:
            return cost_map.get((symbols[0], start), 0.0)
        return 0.0

    client.metadata.get_cost.side_effect = _cost

    # Pulls return a store with a small DataFrame and a to_file that writes bytes.
    def _make_response(*_args, **_kwargs):
        store = MagicMock()
        import pandas as pd

        ts = pd.Timestamp("2026-03-15 13:30:00", tz="UTC")
        df = pd.DataFrame(
            [{"ts_event": ts, "symbol": "NQ.c.0"}]
        ).set_index("ts_event")
        store.to_df.return_value = df
        store.to_file.side_effect = lambda path: Path(path).write_bytes(b"FAKE")
        return store

    client.timeseries.get_range.side_effect = _make_response
    return client


def test_fill_gaps_dry_run_writes_nothing(tmp_path: Path) -> None:
    today = dt.date(2026, 4, 30)
    result = gap_filler.fill_gaps(
        last_n_months=1,
        symbols=["NQ.c.0"],
        data_root=tmp_path,
        dry_run=True,
        today=today,
    )
    assert result.gaps_found > 0
    assert result.pulled == 0
    assert result.skipped_paid == 0
    assert not (tmp_path / "raw" / "historical").exists() or not list(
        (tmp_path / "raw" / "historical").iterdir()
    )


def test_fill_gaps_pulls_zero_cost_partitions(tmp_path: Path) -> None:
    today = dt.date(2026, 4, 6)  # Mon — gives us last week to fill
    client = _fake_client(cost_map={})  # all $0
    result = gap_filler.fill_gaps(
        last_n_months=1,
        symbols=["NQ.c.0"],
        data_root=tmp_path,
        dry_run=False,
        today=today,
        client=client,
    )
    assert result.pulled > 0
    files = list((tmp_path / "raw" / "historical").glob("*.dbn"))
    assert len(files) == result.pulled
    # All filenames should follow the per-symbol pattern.
    for f in files:
        assert f.name.endswith("-NQ.c.0.dbn")


def test_fill_gaps_skip_warns_on_paid_partitions(tmp_path: Path) -> None:
    today = dt.date(2026, 4, 6)
    paid_day = "2026-04-01"
    client = _fake_client(cost_map={("NQ.c.0", paid_day): 12.50})
    result = gap_filler.fill_gaps(
        last_n_months=1,
        symbols=["NQ.c.0"],
        data_root=tmp_path,
        dry_run=False,
        today=today,
        client=client,
    )
    assert result.skipped_paid >= 1
    assert any(paid_day in msg and "$12.50" in msg for msg in result.skip_warn_log)
    # The paid day should NOT have a file on disk.
    paid_path = (
        tmp_path
        / "raw"
        / "historical"
        / f"GLBX.MDP3-mbp-1-{paid_day}-NQ.c.0.dbn"
    )
    assert not paid_path.exists()


def test_fill_gaps_idempotent_when_warehouse_full(tmp_path: Path) -> None:
    """A second run after a successful first should find 0 gaps."""
    today = dt.date(2026, 4, 6)
    client = _fake_client(cost_map={})
    first = gap_filler.fill_gaps(
        last_n_months=1,
        symbols=["NQ.c.0"],
        data_root=tmp_path,
        dry_run=False,
        today=today,
        client=client,
    )
    assert first.pulled > 0

    second = gap_filler.fill_gaps(
        last_n_months=1,
        symbols=["NQ.c.0"],
        data_root=tmp_path,
        dry_run=False,
        today=today,
        client=client,
    )
    assert second.gaps_found == 0
    assert second.pulled == 0
