from __future__ import annotations

import subprocess
import sys
from typing import Annotated

import typer

from app.core.paths import REPO_ROOT
from scripts.cli.output_format import emit_json, emit_lines

app = typer.Typer(
    help="Data inventory and validation commands.",
    add_completion=False,
    rich_markup_mode=None,
)


def _run_script(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=REPO_ROOT, text=True, capture_output=True)


@app.command()
def inventory(
    quick: bool = typer.Option(False, "--quick", help="Sample a smaller inventory."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON wrapper."),
) -> None:
    """Generate a fresh inventory report."""
    script = REPO_ROOT / "scripts" / "data_inventory_report.py"
    args = [sys.executable, str(script)]
    if quick:
        args.append("--quick")
    result = _run_script(args)
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


@app.command()
def validate(
    snapshot_id: Annotated[str, typer.Argument(help="dataset_snapshots.snapshot_id")],
    schemas: str | None = typer.Option(None, "--schemas", help="Comma-separated schema filter."),
    strict: bool = typer.Option(False, "--strict", help="Promote warn-severity gates to fail."),
    quick: bool = typer.Option(False, "--quick", help="Skip slow gates."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON."),
) -> None:
    """Validate a dataset snapshot.

    Wraps `backend/scripts/data/validate_snapshot.py`. Reads the
    snapshot's partitions, runs per-schema gates, writes a
    `partition_validation_reports` row + per-partition findings.

    Exits 0 if all partitions pass, 1 if any fail.
    """
    script = REPO_ROOT / "backend" / "scripts" / "data" / "validate_snapshot.py"
    args = [sys.executable, str(script), snapshot_id]
    if strict:
        args.append("--strict")
    if quick:
        args.append("--quick")
    if schemas:
        args.extend(["--schemas", schemas])
    if json_output:
        args.append("--json")
    result = _run_script(args)
    if result.stdout:
        typer.echo(result.stdout.rstrip())
    if result.stderr:
        typer.echo(result.stderr.rstrip(), err=True)
    if result.returncode != 0:
        raise typer.Exit(result.returncode)
