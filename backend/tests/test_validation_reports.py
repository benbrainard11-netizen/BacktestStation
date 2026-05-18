from datetime import datetime
from pathlib import Path

from sqlalchemy import inspect, text

from app.db import models
from app.db.session import create_all, make_engine, make_session_factory


SNAPSHOT_ID = "9e6c2d1a" + "1" * 56
PARTITION_A = "processed/bars/symbol=NQ.c.0/date=2026-05-17/part-000.parquet"
PARTITION_B = "processed/bars/symbol=NQ.c.0/date=2026-05-18/part-000.parquet"


def _snapshot() -> models.DatasetSnapshot:
    return models.DatasetSnapshot(
        snapshot_id=SNAPSHOT_ID,
        symbols_json=["NQ.c.0"],
        date_start=datetime(2015, 1, 1),
        date_end=datetime(2026, 5, 17),
        schemas_json=["ohlcv-1m"],
        partition_count=2,
        status="active",
    )


def _validation_report() -> models.PartitionValidationReport:
    report = models.PartitionValidationReport(
        snapshot_id=SNAPSHOT_ID,
        generator_version="validation-v1",
        total_partitions=2,
        partitions_pass=1,
        partitions_warn=1,
        partitions_fail=0,
        summary_json='{"warn": 1, "fail": 0}',
        status="completed",
        notes="fixture report",
    )
    report.findings.extend(
        [
            models.PartitionValidationFinding(
                partition_r2_key=PARTITION_A,
                schema="ohlcv-1m",
                symbol="NQ.c.0",
                date="2026-05-17",
                gate_name="row_count",
                severity="warn",
                message="Unexpected low row count",
                details_json='{"rows": 10}',
            ),
            models.PartitionValidationFinding(
                partition_r2_key=PARTITION_B,
                schema="ohlcv-1m",
                symbol="NQ.c.0",
                date="2026-05-18",
                gate_name="hash_present",
                severity="pass",
                message="Hash present",
                details_json='{"sha256": true}',
            ),
        ]
    )
    return report


def test_validation_report_tables_and_indexes_exist(tmp_path: Path) -> None:
    engine = make_engine(f"sqlite:///{tmp_path / 'validation_schema.sqlite'}")
    create_all(engine)
    inspector = inspect(engine)

    assert {
        "partition_validation_reports",
        "partition_validation_findings",
    }.issubset(set(inspector.get_table_names()))

    report_columns = {
        c["name"] for c in inspector.get_columns("partition_validation_reports")
    }
    finding_columns = {
        c["name"] for c in inspector.get_columns("partition_validation_findings")
    }
    snapshot_columns = {c["name"] for c in inspector.get_columns("dataset_snapshots")}

    assert {
        "snapshot_id",
        "generated_at",
        "generator_version",
        "total_partitions",
        "partitions_pass",
        "partitions_warn",
        "partitions_fail",
        "summary_json",
        "status",
        "notes",
    }.issubset(report_columns)
    assert {
        "report_id",
        "partition_r2_key",
        "schema",
        "symbol",
        "date",
        "gate_name",
        "severity",
        "message",
        "details_json",
    }.issubset(finding_columns)
    assert "validation_report_id" in snapshot_columns

    index_names = {
        index["name"]
        for table_name in (
            "partition_validation_reports",
            "partition_validation_findings",
        )
        for index in inspector.get_indexes(table_name)
    }
    assert {"idx_pvr_snapshot", "idx_pvf_report", "idx_pvf_severity"}.issubset(
        index_names
    )


def test_validation_report_roundtrip_with_findings(tmp_path: Path) -> None:
    engine = make_engine(f"sqlite:///{tmp_path / 'validation_roundtrip.sqlite'}")
    create_all(engine)
    SessionLocal = make_session_factory(engine)

    with SessionLocal() as session:
        snapshot = _snapshot()
        report = _validation_report()
        session.add_all([snapshot, report])
        session.flush()
        snapshot.validation_report_id = report.id
        session.commit()
        report_id = report.id

    with SessionLocal() as session:
        loaded_report = session.get(models.PartitionValidationReport, report_id)
        assert loaded_report is not None
        assert loaded_report.snapshot_id == SNAPSHOT_ID
        assert loaded_report.partitions_warn == 1
        assert len(loaded_report.findings) == 2
        assert loaded_report.findings[0].severity == "warn"

        warn_findings = (
            session.query(models.PartitionValidationFinding)
            .filter(models.PartitionValidationFinding.severity == "warn")
            .all()
        )
        assert [finding.gate_name for finding in warn_findings] == ["row_count"]

        linked_report_id = session.execute(
            text(
                "SELECT validation_report_id FROM dataset_snapshots "
                "WHERE snapshot_id = :snapshot_id"
            ),
            {"snapshot_id": SNAPSHOT_ID},
        ).scalar_one()
        assert linked_report_id == report_id


def test_validation_report_migration_is_idempotent(tmp_path: Path) -> None:
    engine = make_engine(f"sqlite:///{tmp_path / 'validation_legacy.sqlite'}")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE dataset_snapshots ("
                " id INTEGER PRIMARY KEY,"
                " snapshot_id VARCHAR(64) NOT NULL UNIQUE,"
                " name VARCHAR(200),"
                " created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,"
                " created_by VARCHAR(80),"
                " symbols_json JSON NOT NULL,"
                " date_start DATETIME NOT NULL,"
                " date_end DATETIME NOT NULL,"
                " schemas_json JSON NOT NULL,"
                " r2_inventory_hash VARCHAR(64),"
                " research_events_manifest_sha256 VARCHAR(64),"
                " partition_count INTEGER NOT NULL,"
                " total_bytes BIGINT,"
                " roll_map_version VARCHAR(40),"
                " known_exclusions_json JSON,"
                " notes TEXT,"
                " status VARCHAR(20) NOT NULL DEFAULT 'draft'"
                ")"
            )
        )

    create_all(engine)
    create_all(engine)

    inspector = inspect(engine)
    assert {
        "partition_validation_reports",
        "partition_validation_findings",
    }.issubset(set(inspector.get_table_names()))

    snapshot_columns = {c["name"] for c in inspector.get_columns("dataset_snapshots")}
    assert "validation_report_id" in snapshot_columns
