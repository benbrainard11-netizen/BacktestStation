from __future__ import annotations

import os
import subprocess
import sys
from typing import Annotated, Any

import typer
from sqlalchemy import func, select

from app.core.paths import REPO_ROOT
from app.db import models
from app.db.session import create_all, make_engine, make_session_factory
from scripts.cli.output_format import compact_dt, emit_json, emit_lines, fail, render_table

app = typer.Typer(
    help="Dataset snapshot commands.",
    add_completion=False,
    rich_markup_mode=None,
)


def _session():
    engine = make_engine(os.getenv("BS_META_DB_URL"))
    create_all(engine)
    return make_session_factory(engine)()


def _snapshot_row(
    snapshot: models.DatasetSnapshot, partition_count: int | None = None
) -> dict[str, Any]:
    return {
        "snapshot_id": snapshot.snapshot_id,
        "name": snapshot.name or "",
        "status": snapshot.status,
        "created_at": compact_dt(snapshot.created_at),
        "symbols": snapshot.symbols_json,
        "schemas": snapshot.schemas_json,
        "partition_count": partition_count
        if partition_count is not None
        else snapshot.partition_count,
        "validation_report_id": snapshot.validation_report_id,
    }


@app.command()
def create(
    symbols: str = typer.Option(..., "--symbols", help="Comma-separated symbols."),
    schemas: str = typer.Option("ohlcv-1m", "--schemas", help="Comma-separated schemas."),
    date_start: str = typer.Option(..., "--date-start", help="YYYY-MM-DD."),
    date_end: str = typer.Option(..., "--date-end", help="YYYY-MM-DD."),
    name: str | None = typer.Option(None, "--name", help="Human-readable snapshot name."),
    with_hash: bool = typer.Option(False, "--with-hash", help="Compute partition hashes."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Walk data without writing DB rows."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON wrapper."),
) -> None:
    """Wrap backend/scripts/data/create_snapshot.py."""
    script = REPO_ROOT / "backend" / "scripts" / "data" / "create_snapshot.py"
    args = [
        sys.executable,
        str(script),
        "--symbols",
        symbols,
        "--schemas",
        schemas,
        "--date-start",
        date_start,
        "--date-end",
        date_end,
    ]
    if name:
        args.extend(["--name", name])
    if with_hash:
        args.append("--with-hash")
    if dry_run:
        args.append("--dry-run")
    result = subprocess.run(args, cwd=REPO_ROOT, text=True, capture_output=True)
    if json_output:
        emit_json(
            {"returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr}
        )
    else:
        if result.stdout:
            typer.echo(result.stdout.rstrip())
        if result.stderr:
            typer.echo(result.stderr.rstrip(), err=True)
    if result.returncode != 0:
        raise typer.Exit(result.returncode)


@app.command("list")
def list_snapshots(
    status: str = typer.Option("active", "--status", help="active, archived, draft, or all."),
    limit: int = typer.Option(20, "--limit", min=1, max=500, help="Max rows."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON."),
) -> None:
    """List dataset snapshots."""
    with _session() as session:
        stmt = select(models.DatasetSnapshot).order_by(models.DatasetSnapshot.created_at.desc())
        if status != "all":
            stmt = stmt.where(models.DatasetSnapshot.status == status)
        rows = [_snapshot_row(snapshot) for snapshot in session.scalars(stmt.limit(limit))]
    if json_output:
        emit_json({"snapshots": rows})
    else:
        emit_lines(
            render_table(
                rows,
                [("snapshot_id", "snapshot"), ("status", "status"), ("name", "name")],
            )
        )


@app.command()
def show(
    snapshot_id: Annotated[str, typer.Argument(help="Snapshot id to show.")],
    json_output: bool = typer.Option(False, "--json", help="Emit JSON."),
) -> None:
    """Show one dataset snapshot with partition and validation summary."""
    with _session() as session:
        snapshot = session.scalar(
            select(models.DatasetSnapshot).where(models.DatasetSnapshot.snapshot_id == snapshot_id)
        )
        if snapshot is None:
            fail(f"snapshot not found: {snapshot_id}", code=1)
        partition_count = session.scalar(
            select(func.count())
            .select_from(models.DatasetSnapshotPartition)
            .where(models.DatasetSnapshotPartition.snapshot_id == snapshot_id)
        )
        report = None
        if snapshot.validation_report_id:
            report = session.get(models.PartitionValidationReport, snapshot.validation_report_id)
        payload = _snapshot_row(snapshot, partition_count)
        payload["validation"] = {
            "report_id": report.id if report else None,
            "status": report.status if report else "none",
        }
    if json_output:
        emit_json(payload)
        return
    emit_lines(
        [
            f"snapshot_id: {payload['snapshot_id']}",
            f"name: {payload['name']}",
            f"status: {payload['status']}",
            f"created_at: {payload['created_at']}",
            f"partition_count: {payload['partition_count']}",
            f"validation: {payload['validation']['status']}",
        ]
    )
