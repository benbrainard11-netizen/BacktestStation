"""Smoke tests for the warehouse_sync helper.

The script copies Hive-partitioned parquet from a remote root (e.g.
Tailscale-mounted SMB share) into a local subset. These tests build
a fake remote tree under tmp_path and exercise the partition-path
math + idempotency check, with no network access.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from app.ingest.warehouse_sync import (
    SCHEMA_TO_PATH,
    _date_range,
    _partition_path,
    main,
    sync_partition,
)


def _seed_partition_files(
    root: Path, schema: str, symbol: str, date: dt.date, sizes: list[int]
) -> Path:
    """Write `sizes` worth of placeholder parquet files into a partition.

    Filename order doesn't matter — sync_partition compares by count + size.
    """
    parts = SCHEMA_TO_PATH[schema]
    part_dir = root.joinpath(*parts, f"symbol={symbol}", f"date={date.isoformat()}")
    part_dir.mkdir(parents=True, exist_ok=True)
    for i, size in enumerate(sizes):
        f = part_dir / f"part-{i:03d}.parquet"
        f.write_bytes(b"x" * size)
    return part_dir


def test_partition_path_assembles_hive_layout(tmp_path: Path) -> None:
    p = _partition_path(
        tmp_path / "data", "bars-1m", "NQ.c.0", dt.date(2026, 4, 22)
    )
    assert p == (
        tmp_path
        / "data"
        / "processed"
        / "bars"
        / "timeframe=1m"
        / "symbol=NQ.c.0"
        / "date=2026-04-22"
    )


def test_partition_path_for_each_known_schema(tmp_path: Path) -> None:
    """Every key in SCHEMA_TO_PATH builds a real-looking partition path."""
    date = dt.date(2026, 4, 22)
    for schema in SCHEMA_TO_PATH:
        p = _partition_path(tmp_path / "data", schema, "NQ.c.0", date)
        # Sanity: ends in date partition; lives somewhere under our root.
        assert p.parts[-1] == "date=2026-04-22"
        assert p.parts[-2] == "symbol=NQ.c.0"


def test_date_range_inclusive_both_ends() -> None:
    days = _date_range(dt.date(2026, 4, 22), dt.date(2026, 4, 24))
    assert days == [
        dt.date(2026, 4, 22),
        dt.date(2026, 4, 23),
        dt.date(2026, 4, 24),
    ]


def test_date_range_single_day() -> None:
    assert _date_range(dt.date(2026, 4, 22), dt.date(2026, 4, 22)) == [
        dt.date(2026, 4, 22),
    ]


def test_sync_partition_copies_when_local_missing(tmp_path: Path) -> None:
    remote = tmp_path / "remote"
    local = tmp_path / "local"
    date = dt.date(2026, 4, 22)
    _seed_partition_files(remote, "bars-1m", "NQ.c.0", date, [100, 200])

    copied, total = sync_partition(
        schema="bars-1m",
        symbol="NQ.c.0",
        date=date,
        remote_root=remote,
        local_root=local,
        rebuild=False,
    )
    assert copied is True
    assert total == 300
    dst = _partition_path(local, "bars-1m", "NQ.c.0", date)
    assert sorted(p.name for p in dst.glob("*.parquet")) == [
        "part-000.parquet",
        "part-001.parquet",
    ]


def test_sync_partition_skips_when_count_and_size_match(tmp_path: Path) -> None:
    """Idempotency: re-sync a partition the local already has should be a no-op."""
    remote = tmp_path / "remote"
    local = tmp_path / "local"
    date = dt.date(2026, 4, 22)
    _seed_partition_files(remote, "bars-1m", "NQ.c.0", date, [100, 200])

    # First sync to seed local.
    sync_partition(
        schema="bars-1m",
        symbol="NQ.c.0",
        date=date,
        remote_root=remote,
        local_root=local,
        rebuild=False,
    )
    # Second sync — same inputs — must skip.
    copied, total = sync_partition(
        schema="bars-1m",
        symbol="NQ.c.0",
        date=date,
        remote_root=remote,
        local_root=local,
        rebuild=False,
    )
    assert copied is False
    assert total == 0


def test_sync_partition_rebuild_overrides_skip(tmp_path: Path) -> None:
    """`rebuild=True` re-copies even when local already exists."""
    remote = tmp_path / "remote"
    local = tmp_path / "local"
    date = dt.date(2026, 4, 22)
    _seed_partition_files(remote, "bars-1m", "NQ.c.0", date, [100, 200])
    sync_partition(
        schema="bars-1m",
        symbol="NQ.c.0",
        date=date,
        remote_root=remote,
        local_root=local,
        rebuild=False,
    )
    copied, total = sync_partition(
        schema="bars-1m",
        symbol="NQ.c.0",
        date=date,
        remote_root=remote,
        local_root=local,
        rebuild=True,
    )
    assert copied is True
    assert total == 300


def test_sync_partition_returns_zero_when_remote_missing(tmp_path: Path) -> None:
    remote = tmp_path / "remote"
    local = tmp_path / "local"
    # No partition seeded.
    copied, total = sync_partition(
        schema="bars-1m",
        symbol="NQ.c.0",
        date=dt.date(2026, 4, 22),
        remote_root=remote,
        local_root=local,
        rebuild=False,
    )
    assert copied is False
    assert total == 0


def test_main_dry_run_reports_without_copying(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    remote = tmp_path / "remote"
    local = tmp_path / "local"
    date = dt.date(2026, 4, 22)
    _seed_partition_files(remote, "bars-1m", "NQ.c.0", date, [100])

    rc = main(
        [
            "--symbols",
            "NQ.c.0",
            "--start",
            "2026-04-22",
            "--end",
            "2026-04-22",
            "--schemas",
            "bars-1m",
            "--remote-root",
            str(remote),
            "--local-root",
            str(local),
            "--dry-run",
        ]
    )

    assert rc == 0
    out = capsys.readouterr().out
    assert "WOULD COPY" in out
    # Nothing was actually copied to local.
    dst = _partition_path(local, "bars-1m", "NQ.c.0", date)
    assert not dst.exists()


def test_main_unknown_schema_returns_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    remote = tmp_path / "remote"
    remote.mkdir()
    local = tmp_path / "local"

    rc = main(
        [
            "--symbols",
            "NQ.c.0",
            "--start",
            "2026-04-22",
            "--end",
            "2026-04-22",
            "--schemas",
            "definitely-not-a-schema",
            "--remote-root",
            str(remote),
            "--local-root",
            str(local),
        ]
    )

    assert rc == 1
    err = capsys.readouterr().err
    assert "unknown schema" in err.lower()


def test_main_rejects_missing_remote_root(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The script bails fast when --remote-root doesn't exist (Tailscale not
    mounted etc.) rather than silently producing an empty subset."""
    rc = main(
        [
            "--symbols",
            "NQ.c.0",
            "--start",
            "2026-04-22",
            "--end",
            "2026-04-22",
            "--remote-root",
            str(tmp_path / "does-not-exist"),
            "--local-root",
            str(tmp_path / "local"),
        ]
    )
    assert rc == 1
    err = capsys.readouterr().err
    assert "remote-root does not exist" in err
