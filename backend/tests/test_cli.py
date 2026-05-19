from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pytest
from typer.testing import CliRunner

from app.db import models
from app.db.session import create_all, make_engine, make_session_factory
from scripts.cli.main import app

runner = CliRunner()
TMP_ROOT = Path(__file__).parent / "_artifacts" / "cli"


def _db_url(label: str) -> str:
    root = TMP_ROOT / f"{label}_{uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    path = root / "cli.sqlite"
    return "sqlite:///" + str(path).replace("\\", "/")


def _session_factory(db_url: str):
    engine = make_engine(db_url)
    create_all(engine)
    return make_session_factory(engine)


def _seed_snapshot(db_url: str) -> str:
    SessionLocal = _session_factory(db_url)
    snapshot_id = "abc123" + "0" * 58
    with SessionLocal() as session:
        snapshot = models.DatasetSnapshot(
            snapshot_id=snapshot_id,
            name="cli fixture",
            symbols_json=["NQ.c.0"],
            date_start=datetime(2020, 1, 1),
            date_end=datetime(2026, 5, 17),
            schemas_json=["ohlcv-1m"],
            partition_count=1,
            status="active",
        )
        snapshot.partitions.append(
            models.DatasetSnapshotPartition(
                r2_key="processed/bars/symbol=NQ.c.0/date=2026-05-17/part-000.parquet",
                size=100,
                sha256="f" * 64,
            )
        )
        session.add(snapshot)
        session.commit()
    return snapshot_id


def _seed_trial_group(db_url: str) -> None:
    SessionLocal = _session_factory(db_url)
    with SessionLocal() as session:
        hypothesis = models.Hypothesis(
            title="CLI hypothesis",
            hypothesis_md="CLI should list this group.",
            status="active",
        )
        group = models.TrialGroup(
            hypothesis=hypothesis,
            name="cli group",
            status="running",
        )
        session.add(group)
        session.commit()


@pytest.mark.parametrize(
    "args",
    [
        ["doctor", "--help"],
        ["status", "--help"],
        ["data", "validate", "--help"],
        ["data", "inventory", "--help"],
        ["snapshot", "create", "--help"],
        ["snapshot", "list", "--help"],
        ["snapshot", "show", "--help"],
        ["trial", "list", "--help"],
    ],
)
def test_cli_help_surfaces(args: list[str]) -> None:
    result = runner.invoke(app, args)
    assert result.exit_code == 0
    assert "Usage" in result.stdout


def test_doctor_json_happy_path(monkeypatch) -> None:
    from scripts.cli import cmd_doctor

    monkeypatch.setattr(
        cmd_doctor,
        "run_checks",
        lambda: [{"name": "fixture", "ok": True, "detail": "ok"}],
    )
    result = runner.invoke(app, ["doctor", "--json"])
    assert result.exit_code == 0
    assert '"ok": true' in result.stdout


def test_doctor_failure_path(monkeypatch) -> None:
    from scripts.cli import cmd_doctor

    monkeypatch.setattr(
        cmd_doctor,
        "run_checks",
        lambda: [{"name": "fixture", "ok": False, "detail": "bad"}],
    )
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 1
    assert "[FAIL] fixture" in result.stdout


def test_status_json_happy_path(monkeypatch) -> None:
    db_url = _db_url("status")
    _seed_snapshot(db_url)
    _seed_trial_group(db_url)
    monkeypatch.setenv("BS_META_DB_URL", db_url)

    result = runner.invoke(app, ["status", "--json"])

    assert result.exit_code == 0
    assert "dataset_snapshots" in result.stdout
    assert "trial_groups" in result.stdout


def test_data_inventory_wraps_existing_script(monkeypatch) -> None:
    from scripts.cli import cmd_data

    def fake_run(args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=args, returncode=0, stdout="inventory ok\n", stderr=""
        )

    monkeypatch.setattr(cmd_data, "_run_script", fake_run)
    result = runner.invoke(app, ["data", "inventory", "--quick"])
    assert result.exit_code == 0
    assert "inventory ok" in result.stdout


def test_data_validate_stub_failure_path() -> None:
    result = runner.invoke(app, ["data", "validate", "snapshot-1"])
    assert result.exit_code == 1
    assert "Validation runner not landed yet" in result.stdout


def test_snapshot_create_wraps_existing_script(monkeypatch) -> None:
    from scripts.cli import cmd_snapshot

    def fake_run(*args, **kwargs) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=args[0], returncode=0, stdout="snapshot ok\n", stderr=""
        )

    monkeypatch.setattr(cmd_snapshot.subprocess, "run", fake_run)
    result = runner.invoke(
        app,
        [
            "snapshot",
            "create",
            "--symbols",
            "NQ.c.0",
            "--schemas",
            "ohlcv-1m",
            "--date-start",
            "2020-01-01",
            "--date-end",
            "2026-05-17",
            "--dry-run",
        ],
    )
    assert result.exit_code == 0
    assert "snapshot ok" in result.stdout


def test_snapshot_list_and_show(monkeypatch) -> None:
    db_url = _db_url("snapshot")
    snapshot_id = _seed_snapshot(db_url)
    monkeypatch.setenv("BS_META_DB_URL", db_url)

    listed = runner.invoke(app, ["snapshot", "list", "--status", "all"])
    shown = runner.invoke(app, ["snapshot", "show", snapshot_id])

    assert listed.exit_code == 0
    assert snapshot_id in listed.stdout
    assert shown.exit_code == 0
    assert "partition_count: 1" in shown.stdout


def test_snapshot_show_missing_fails(monkeypatch) -> None:
    monkeypatch.setenv("BS_META_DB_URL", _db_url("missing_snapshot"))
    result = runner.invoke(app, ["snapshot", "show", "missing"])
    assert result.exit_code == 1
    assert "snapshot not found" in result.stderr


def test_trial_list_happy_path(monkeypatch) -> None:
    db_url = _db_url("trial")
    _seed_trial_group(db_url)
    monkeypatch.setenv("BS_META_DB_URL", db_url)

    result = runner.invoke(app, ["trial", "list", "--status", "running"])

    assert result.exit_code == 0
    assert "cli group" in result.stdout
