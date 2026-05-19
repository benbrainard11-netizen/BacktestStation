"""Tests for the snapshot validation runner.

Uses synthetic parquet partitions in tmp dirs + an in-memory sqlite
session. Covers:
  - r2_key → PartitionContext parsing
  - happy path: clean snapshot → all-pass report
  - failure path: partition with broken OHLC → fail finding
  - skipped partition: missing local file → fail finding (no crash)
  - unknown r2_key → warn finding (no crash)
  - strict mode promotes warns to fails (verified via missing_minutes)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import Base
from app.db.models import DatasetSnapshot, DatasetSnapshotPartition
from app.research.validation.runner import (
    RunnerConfig,
    parse_r2_key,
    run_snapshot_validation,
)


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture
def db_session(tmp_path: Path) -> Session:
    """Fresh in-memory sqlite session with all tables created."""
    engine = create_engine(f"sqlite:///{tmp_path / 'test.sqlite'}")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def fake_bars_root(tmp_path: Path) -> Path:
    """A directory we'll point the runner at via --local-roots override."""
    root = tmp_path / "fake_bars_root"
    root.mkdir()
    return root


def _good_ohlcv_partition(symbol: str = "NQ.c.0", date: str = "2026-05-15") -> pd.DataFrame:
    base = pd.Timestamp(f"{date} 14:30:00", tz="UTC")
    return pd.DataFrame(
        [
            {
                "ts_event": base + pd.Timedelta(minutes=i),
                "symbol": symbol,
                "open": 20000.0 + i,
                "high": 20005.0 + i,
                "low": 19995.0 + i,
                "close": 20002.0 + i,
                "volume": 100 + i,
                "trade_count": 10 + i,
                "vwap": 20001.0 + i,
            }
            for i in range(60)
        ]
    )


def _write_bars_partition(
    root: Path, symbol: str, date: str, df: pd.DataFrame, timeframe: str = "1m"
) -> str:
    """Write a parquet under <root>/timeframe=.../symbol=.../date=.../part-000.parquet.

    `root` should be the equivalent of `D:/data/processed/bars/` — i.e. the
    directory where the prefix-stripped remainder of an R2 key lands.

    Returns the r2_key for this partition.
    """
    part_dir = (
        root / f"timeframe={timeframe}" / f"symbol={symbol}" / f"date={date}"
    )
    part_dir.mkdir(parents=True, exist_ok=True)
    path = part_dir / "part-000.parquet"
    df.to_parquet(path, index=False)
    return f"processed/bars/timeframe={timeframe}/symbol={symbol}/date={date}/part-000.parquet"


def _make_snapshot(
    db: Session, snapshot_id: str, partitions: list[tuple[str, int, str]]
) -> DatasetSnapshot:
    """Insert a dataset_snapshots row + N partitions.

    `partitions` is a list of (r2_key, size, sha256) tuples.
    """
    snap = DatasetSnapshot(
        snapshot_id=snapshot_id,
        name="test_snapshot",
        created_by="pytest",
        symbols_json=["NQ.c.0"],
        date_start=datetime(2026, 5, 15, tzinfo=timezone.utc),
        date_end=datetime(2026, 5, 16, tzinfo=timezone.utc),
        schemas_json=["ohlcv-1m"],
        partition_count=len(partitions),
        total_bytes=sum(p[1] for p in partitions),
        status="active",
    )
    db.add(snap)
    db.flush()
    for r2_key, size, sha256 in partitions:
        db.add(DatasetSnapshotPartition(
            snapshot_id=snapshot_id,
            r2_key=r2_key,
            size=size,
            sha256=sha256,
        ))
    db.commit()
    return snap


# ===========================================================================
# parse_r2_key
# ===========================================================================


class TestParseR2Key:
    def test_ohlcv_1m_bars(self):
        ctx = parse_r2_key(
            "processed/bars/timeframe=1m/symbol=NQ.c.0/date=2026-05-15/part-000.parquet"
        )
        assert ctx is not None
        assert ctx.schema == "ohlcv-1m"
        assert ctx.symbol == "NQ.c.0"
        assert ctx.date == "2026-05-15"
        assert ctx.timeframe == "1m"

    def test_tbbo(self):
        ctx = parse_r2_key(
            "processed/bars/timeframe=tbbo/symbol=ES.c.0/date=2025-08-05/part-000.parquet"
        )
        assert ctx is not None
        assert ctx.schema == "tbbo"

    def test_mbp1(self):
        ctx = parse_r2_key(
            "processed/bars/timeframe=mbp-1/symbol=NQ.c.0/date=2026-03-02/part-000.parquet"
        )
        assert ctx is not None
        assert ctx.schema == "mbp-1"

    def test_research_events(self):
        ctx = parse_r2_key(
            "data/research_events/feature_name=fvg_formation/event_year=2024/part-000040.parquet"
        )
        assert ctx is not None
        assert ctx.schema == "research_events"
        assert ctx.feature_name == "fvg_formation"
        assert ctx.event_year == 2024

    def test_unknown_key_returns_none(self):
        assert parse_r2_key("raw/databento/some_bundle.dbn.zst") is None
        assert parse_r2_key("garbage") is None

    def test_unknown_timeframe_returns_none(self):
        ctx = parse_r2_key(
            "processed/bars/timeframe=5m/symbol=NQ.c.0/date=2026-05-15/part-000.parquet"
        )
        assert ctx is None


# ===========================================================================
# Runner happy path
# ===========================================================================


class TestRunnerHappyPath:
    def test_all_good_partitions_produce_clean_report(
        self, db_session: Session, fake_bars_root: Path
    ):
        # 3 good ohlcv-1m partitions
        r2_keys = []
        for date in ("2026-05-13", "2026-05-14", "2026-05-15"):
            df = _good_ohlcv_partition(date=date)
            r2_key = _write_bars_partition(fake_bars_root, "NQ.c.0", date, df)
            r2_keys.append((r2_key, 1024, "deadbeef" * 8))
        _make_snapshot(db_session, "snap-good", r2_keys)

        report_id = run_snapshot_validation(
            snapshot_id="snap-good",
            db=db_session,
            config=RunnerConfig(
                local_roots={"processed/bars/": fake_bars_root},
            ),
            progress=False,
        )
        db_session.commit()

        from app.db.models import PartitionValidationReport, PartitionValidationFinding
        report = db_session.get(PartitionValidationReport, report_id)
        assert report.total_partitions == 3
        assert report.partitions_pass == 3
        assert report.partitions_warn == 0
        assert report.partitions_fail == 0
        summary = json.loads(report.summary_json)
        assert summary["by_severity"] == {"pass": 3, "warn": 0, "fail": 0}
        assert summary["top_failing_gates"] == []
        # No findings since everything passed
        n_findings = db_session.query(PartitionValidationFinding).filter_by(
            report_id=report_id
        ).count()
        assert n_findings == 0

        # snapshot.validation_report_id should be linked
        snap = (
            db_session.query(DatasetSnapshot)
            .filter_by(snapshot_id="snap-good")
            .one()
        )
        assert snap.validation_report_id == report_id


# ===========================================================================
# Failure paths
# ===========================================================================


class TestRunnerFailures:
    def test_broken_ohlc_produces_fail_findings(
        self, db_session: Session, fake_bars_root: Path
    ):
        df = _good_ohlcv_partition(date="2026-05-15")
        df.loc[0, "high"] = df.loc[0, "low"] - 1  # invariant violation
        r2_key = _write_bars_partition(fake_bars_root, "NQ.c.0", "2026-05-15", df)
        _make_snapshot(db_session, "snap-broken", [(r2_key, 1024, "x" * 64)])

        report_id = run_snapshot_validation(
            snapshot_id="snap-broken",
            db=db_session,
            config=RunnerConfig(
                local_roots={"processed/bars/": fake_bars_root},
            ),
            progress=False,
        )
        db_session.commit()

        from app.db.models import PartitionValidationReport, PartitionValidationFinding
        report = db_session.get(PartitionValidationReport, report_id)
        assert report.partitions_fail == 1
        assert report.partitions_pass == 0

        findings = (
            db_session.query(PartitionValidationFinding)
            .filter_by(report_id=report_id)
            .all()
        )
        gate_names = {f.gate_name for f in findings}
        # high < low triggers a cluster of OHLC gates
        assert "ohlc_high_ge_low" in gate_names
        # Each finding should have schema/symbol/date populated
        for f in findings:
            assert f.schema == "ohlcv-1m"
            assert f.symbol == "NQ.c.0"
            assert f.date == "2026-05-15"

    def test_missing_local_file_produces_fail(
        self, db_session: Session, fake_bars_root: Path
    ):
        # Reference a partition we never wrote
        r2_key = "processed/bars/timeframe=1m/symbol=NQ.c.0/date=2026-05-15/part-000.parquet"
        _make_snapshot(db_session, "snap-missing", [(r2_key, 0, "0" * 64)])

        report_id = run_snapshot_validation(
            snapshot_id="snap-missing",
            db=db_session,
            config=RunnerConfig(
                local_roots={"processed/bars/": fake_bars_root},
            ),
            progress=False,
        )
        db_session.commit()

        from app.db.models import PartitionValidationReport, PartitionValidationFinding
        report = db_session.get(PartitionValidationReport, report_id)
        assert report.partitions_fail == 1
        findings = (
            db_session.query(PartitionValidationFinding)
            .filter_by(report_id=report_id)
            .all()
        )
        assert any(f.gate_name == "_partition_load" for f in findings)

    def test_unknown_r2_key_produces_warn(
        self, db_session: Session, fake_bars_root: Path
    ):
        r2_key = "raw/databento/something.dbn.zst"
        _make_snapshot(db_session, "snap-raw", [(r2_key, 1024, "a" * 64)])

        report_id = run_snapshot_validation(
            snapshot_id="snap-raw",
            db=db_session,
            config=RunnerConfig(
                local_roots={"processed/bars/": fake_bars_root},
            ),
            progress=False,
        )
        db_session.commit()

        from app.db.models import PartitionValidationReport, PartitionValidationFinding
        report = db_session.get(PartitionValidationReport, report_id)
        assert report.partitions_warn == 1
        findings = (
            db_session.query(PartitionValidationFinding)
            .filter_by(report_id=report_id)
            .all()
        )
        assert any(f.gate_name == "_partition_parser" for f in findings)

    def test_unknown_snapshot_raises(self, db_session: Session):
        with pytest.raises(ValueError, match="not found"):
            run_snapshot_validation(snapshot_id="nope", db=db_session, progress=False)

    def test_empty_snapshot_raises(self, db_session: Session):
        # Snapshot with zero partitions
        snap = DatasetSnapshot(
            snapshot_id="snap-empty",
            symbols_json=["NQ.c.0"],
            date_start=datetime(2026, 1, 1, tzinfo=timezone.utc),
            date_end=datetime(2026, 1, 2, tzinfo=timezone.utc),
            schemas_json=["ohlcv-1m"],
            partition_count=0,
            status="active",
        )
        db_session.add(snap)
        db_session.commit()
        with pytest.raises(ValueError, match="no partitions"):
            run_snapshot_validation(
                snapshot_id="snap-empty", db=db_session, progress=False
            )


# ===========================================================================
# Strict mode
# ===========================================================================


class TestStrictMode:
    def test_strict_promotes_vwap_warn_to_fail(
        self, db_session: Session, fake_bars_root: Path
    ):
        df = _good_ohlcv_partition(date="2026-05-15")
        # Out-of-range vwap is a warn-level violation
        df.loc[0, "vwap"] = df.loc[0, "high"] + 100.0
        r2_key = _write_bars_partition(fake_bars_root, "NQ.c.0", "2026-05-15", df)
        _make_snapshot(db_session, "snap-vwap", [(r2_key, 1024, "v" * 64)])

        report_id = run_snapshot_validation(
            snapshot_id="snap-vwap",
            db=db_session,
            config=RunnerConfig(
                strict=True,
                local_roots={"processed/bars/": fake_bars_root},
            ),
            progress=False,
        )
        db_session.commit()

        from app.db.models import PartitionValidationReport, PartitionValidationFinding
        report = db_session.get(PartitionValidationReport, report_id)
        # In strict mode, warn becomes fail
        assert report.partitions_fail == 1
        assert report.partitions_warn == 0

        findings = (
            db_session.query(PartitionValidationFinding)
            .filter_by(report_id=report_id)
            .all()
        )
        vwap = [f for f in findings if f.gate_name == "vwap_in_range"]
        assert len(vwap) == 1
        assert vwap[0].severity == "fail"
