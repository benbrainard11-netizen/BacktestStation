from __future__ import annotations

import importlib
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import typer
from sqlalchemy import inspect

from app.core.paths import DATA_DIR, META_DB_PATH, REPO_ROOT
from app.db.session import create_all, make_engine
from app.ingest.r2_client import make_s3_client
from scripts.cli.output_format import emit_json, emit_lines

EXPECTED_TABLES = {
    "dataset_snapshots",
    "dataset_snapshot_partitions",
    "dataset_snapshot_inputs",
    "partition_validation_reports",
    "partition_validation_findings",
    "hypotheses",
    "trial_groups",
    "trials",
    "trial_lock_records",
}


def _check(name: str, ok: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "ok": ok, "detail": detail}


def _db_check() -> dict[str, Any]:
    try:
        engine = make_engine(os.getenv("BS_META_DB_URL"))
        create_all(engine)
        tables = set(inspect(engine).get_table_names())
        missing = sorted(EXPECTED_TABLES - tables)
        return _check(
            "metadata_db", not missing, f"missing={missing}" if missing else str(META_DB_PATH)
        )
    except Exception as exc:  # noqa: BLE001
        return _check("metadata_db", False, str(exc))


def _r2_check() -> dict[str, Any]:
    try:
        client, bucket = make_s3_client()
        client.head_object(Bucket=bucket, Key="_research_inventory.json")
        return _check("r2", True, f"{bucket}/_research_inventory.json reachable")
    except Exception as exc:  # noqa: BLE001
        return _check("r2", False, str(exc))


def _path_checks() -> list[dict[str, Any]]:
    paths = [
        DATA_DIR / "research_events",
        DATA_DIR / "ml" / "levels",
        DATA_DIR / "ml" / "catalog",
        Path("D:/data"),
    ]
    return [_check(f"path:{path}", path.exists(), str(path)) for path in paths]


def _dep_checks() -> list[dict[str, Any]]:
    results = []
    for module in ("boto3", "pandas", "sqlalchemy", "typer"):
        try:
            importlib.import_module(module)
            results.append(_check(f"dep:{module}", True, "import ok"))
        except Exception as exc:  # noqa: BLE001
            results.append(_check(f"dep:{module}", False, str(exc)))
    return results


def _git_check() -> dict[str, Any]:
    result = subprocess.run(
        ["git", "status", "--short"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        timeout=15,
    )
    dirty = len([line for line in result.stdout.splitlines() if line.strip()])
    return _check("git_status", result.returncode == 0, f"dirty_files={dirty}")


def _pytest_collect_check() -> dict[str, Any]:
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-q"],
            cwd=REPO_ROOT / "backend",
            text=True,
            capture_output=True,
            timeout=30,
        )
        detail = "collect ok" if result.returncode == 0 else result.stderr[-300:]
        return _check("pytest_collect", result.returncode == 0, detail)
    except Exception as exc:  # noqa: BLE001
        return _check("pytest_collect", False, str(exc))


def run_checks() -> list[dict[str, Any]]:
    return [
        _db_check(),
        _r2_check(),
        *_path_checks(),
        *_dep_checks(),
        _git_check(),
        _pytest_collect_check(),
    ]


def doctor(json_output: bool = typer.Option(False, "--json", help="Emit JSON.")) -> None:
    """Run project health checks."""
    checks = run_checks()
    ok = all(check["ok"] for check in checks)
    if json_output:
        emit_json({"ok": ok, "checks": checks})
    else:
        lines = ["BacktestStation doctor", ""]
        for check in checks:
            mark = "OK" if check["ok"] else "FAIL"
            lines.append(f"[{mark}] {check['name']} - {check['detail']}")
        emit_lines(lines)
    if not ok:
        raise typer.Exit(1)
