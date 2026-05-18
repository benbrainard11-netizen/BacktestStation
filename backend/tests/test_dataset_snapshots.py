from datetime import datetime
from pathlib import Path

from sqlalchemy import inspect, text

from app.db import models
from app.db.session import create_all, make_engine, make_session_factory


SNAPSHOT_ID = "5ad286d2" + "0" * 56


def test_dataset_snapshot_tables_and_backtest_columns_exist(tmp_path: Path) -> None:
    engine = make_engine(f"sqlite:///{tmp_path / 'snapshots_schema.sqlite'}")
    create_all(engine)
    inspector = inspect(engine)

    assert {
        "dataset_snapshots",
        "dataset_snapshot_partitions",
        "dataset_snapshot_inputs",
    }.issubset(set(inspector.get_table_names()))
    snapshot_columns = {c["name"] for c in inspector.get_columns("dataset_snapshots")}
    partition_columns = {
        c["name"] for c in inspector.get_columns("dataset_snapshot_partitions")
    }
    input_columns = {
        c["name"] for c in inspector.get_columns("dataset_snapshot_inputs")
    }
    run_columns = {c["name"] for c in inspector.get_columns("backtest_runs")}

    assert {
        "snapshot_id",
        "name",
        "created_by",
        "symbols_json",
        "date_start",
        "date_end",
        "schemas_json",
        "r2_inventory_hash",
        "research_events_manifest_sha256",
        "partition_count",
        "total_bytes",
        "roll_map_version",
        "known_exclusions_json",
        "status",
        "validation_report_id",
    }.issubset(snapshot_columns)
    assert {"snapshot_id", "r2_key", "size", "sha256"}.issubset(partition_columns)
    assert {
        "snapshot_id",
        "input_kind",
        "input_uri",
        "sha256",
        "size",
        "metadata_json",
    }.issubset(input_columns)
    assert {"dataset_snapshot_id", "code_commit_sha", "seed"}.issubset(run_columns)

    index_names = {
        index["name"]
        for table_name in (
            "dataset_snapshots",
            "dataset_snapshot_partitions",
            "dataset_snapshot_inputs",
            "backtest_runs",
        )
        for index in inspector.get_indexes(table_name)
    }
    assert {
        "ix_dataset_snapshots_snapshot_id",
        "ix_dataset_snapshots_status",
        "ix_dataset_snapshots_created_at",
        "ix_dataset_snapshot_partitions_snapshot_id",
        "ix_dataset_snapshot_partitions_r2_key",
        "ix_dataset_snapshot_partitions_sha256",
        "ix_dataset_snapshot_inputs_snapshot_id",
        "ix_dataset_snapshot_inputs_input_kind",
        "ix_dataset_snapshot_inputs_input_uri",
        "ix_dataset_snapshot_inputs_sha256",
        "ix_backtest_runs_dataset_snapshot_id",
    }.issubset(index_names)


def test_dataset_snapshot_roundtrip_with_backtest_run_and_partitions(
    tmp_path: Path,
) -> None:
    engine = make_engine(f"sqlite:///{tmp_path / 'snapshot_roundtrip.sqlite'}")
    create_all(engine)
    SessionLocal = make_session_factory(engine)

    with SessionLocal() as session:
        strategy = models.Strategy(name="Locked Runner", slug="locked-runner")
        version = models.StrategyVersion(version="v1", strategy=strategy)
        snapshot = models.DatasetSnapshot(
            snapshot_id=SNAPSHOT_ID,
            name="expanded universe v1 through 2026 YTD",
            created_by="benpc",
            symbols_json=["NQ.c.0", "ES.c.0"],
            date_start=datetime(2015, 1, 1),
            date_end=datetime(2026, 5, 17),
            schemas_json=["ohlcv-1m", "research_events"],
            r2_inventory_hash="1" * 64,
            research_events_manifest_sha256="2" * 64,
            partition_count=2,
            total_bytes=3000,
            roll_map_version="continuous-v1",
            known_exclusions_json=[
                {"date": "2016-01-01", "symbol": "NQ.c.0", "reason": "holiday"}
            ],
            status="active",
        )
        snapshot.partitions.extend(
            [
                models.DatasetSnapshotPartition(
                    r2_key="data/research_events/symbol=NQ.c.0/part-000.parquet",
                    size=1000,
                    sha256="a" * 64,
                ),
                models.DatasetSnapshotPartition(
                    r2_key="data/research_events/symbol=ES.c.0/part-000.parquet",
                    size=2000,
                    sha256="b" * 64,
                ),
            ]
        )
        snapshot.inputs.extend(
            [
                models.DatasetSnapshotInput(
                    input_kind="r2_inventory",
                    input_uri="r2://bsdata-prod/_research_inventory.json",
                    sha256="c" * 64,
                    size=500,
                    metadata_json={"version": "2026-05-17"},
                ),
                models.DatasetSnapshotInput(
                    input_kind="research_events_manifest",
                    input_uri="repo://data/research_events/manifest.json",
                    sha256="d" * 64,
                    size=600,
                    metadata_json={"source": "repo"},
                ),
            ]
        )
        run = models.BacktestRun(
            symbol="NQ",
            timeframe="1m",
            strategy_version=version,
            dataset_snapshot=snapshot,
            code_commit_sha="6727c90307c0f60768fac1eb5d4af5e1075dd3a1",
            seed=247,
        )
        session.add(strategy)
        session.commit()
        run_id = run.id

    with SessionLocal() as session:
        loaded_run = session.get(models.BacktestRun, run_id)
        assert loaded_run is not None
        assert loaded_run.dataset_snapshot_id == SNAPSHOT_ID
        assert loaded_run.dataset_snapshot is not None
        assert loaded_run.dataset_snapshot.symbols_json == ["NQ.c.0", "ES.c.0"]
        assert loaded_run.dataset_snapshot.partitions[0].snapshot_id == SNAPSHOT_ID
        assert loaded_run.dataset_snapshot.inputs[0].input_kind == "r2_inventory"
        assert loaded_run.dataset_snapshot.inputs[0].metadata_json == {
            "version": "2026-05-17"
        }
        assert loaded_run.code_commit_sha == "6727c90307c0f60768fac1eb5d4af5e1075dd3a1"
        assert loaded_run.seed == 247

        snapshots_with_nq_partition = (
            session.query(models.DatasetSnapshot)
            .join(models.DatasetSnapshotPartition)
            .filter(
                models.DatasetSnapshotPartition.r2_key
                == "data/research_events/symbol=NQ.c.0/part-000.parquet"
            )
            .all()
        )
        assert [snap.snapshot_id for snap in snapshots_with_nq_partition] == [
            SNAPSHOT_ID
        ]

        snapshots_with_inventory = (
            session.query(models.DatasetSnapshot)
            .join(models.DatasetSnapshotInput)
            .filter(models.DatasetSnapshotInput.input_kind == "r2_inventory")
            .all()
        )
        assert [snap.snapshot_id for snap in snapshots_with_inventory] == [
            SNAPSHOT_ID
        ]


def test_trial_lock_record_soft_references_dataset_snapshot(tmp_path: Path) -> None:
    engine = make_engine(f"sqlite:///{tmp_path / 'snapshot_lock.sqlite'}")
    create_all(engine)
    SessionLocal = make_session_factory(engine)

    with SessionLocal() as session:
        snapshot = models.DatasetSnapshot(
            snapshot_id=SNAPSHOT_ID,
            symbols_json=["NQ.c.0"],
            date_start=datetime(2015, 1, 1),
            date_end=datetime(2026, 5, 17),
            schemas_json=["research_events"],
            partition_count=0,
            status="active",
        )
        strategy = models.Strategy(name="S", slug="s")
        version = models.StrategyVersion(version="v1", strategy=strategy)
        hypothesis = models.Hypothesis(
            title="H",
            hypothesis_md="Frozen candidate should survive holdout.",
            parent_strategy_version=version,
        )
        group = models.TrialGroup(hypothesis=hypothesis, name="G")
        lock = models.TrialLockRecord(
            trial_group=group,
            lock_type="pre_validation",
            candidate_set_hash="c" * 64,
            dataset_snapshot_id=SNAPSHOT_ID,
            code_commit_sha="6727c90307c0f60768fac1eb5d4af5e1075dd3a1",
            status="active",
        )
        session.add_all([snapshot, strategy])
        session.commit()
        lock_id = lock.id

    with SessionLocal() as session:
        loaded_lock = session.get(models.TrialLockRecord, lock_id)
        loaded_snapshot = session.execute(
            text(
                "SELECT snapshot_id FROM dataset_snapshots "
                "WHERE snapshot_id = :snapshot_id"
            ),
            {"snapshot_id": loaded_lock.dataset_snapshot_id},
        ).scalar_one()
        assert loaded_snapshot == SNAPSHOT_ID


def test_dataset_snapshot_migration_is_idempotent_on_legacy_backtest_runs(
    tmp_path: Path,
) -> None:
    engine = make_engine(f"sqlite:///{tmp_path / 'legacy_snapshot.sqlite'}")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE backtest_runs ("
                " id INTEGER PRIMARY KEY,"
                " strategy_version_id INTEGER NOT NULL,"
                " name VARCHAR(200),"
                " symbol VARCHAR(40) NOT NULL,"
                " timeframe VARCHAR(20),"
                " session_label VARCHAR(40),"
                " start_ts DATETIME,"
                " end_ts DATETIME,"
                " import_source TEXT,"
                " status VARCHAR(20) NOT NULL DEFAULT 'imported',"
                " created_at DATETIME"
                ")"
            )
        )

    create_all(engine)
    create_all(engine)

    inspector = inspect(engine)
    run_columns = {c["name"] for c in inspector.get_columns("backtest_runs")}
    assert {"dataset_snapshot_id", "code_commit_sha", "seed"}.issubset(run_columns)
    assert {
        "dataset_snapshots",
        "dataset_snapshot_partitions",
        "dataset_snapshot_inputs",
    }.issubset(set(inspector.get_table_names()))
