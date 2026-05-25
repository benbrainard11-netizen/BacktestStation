from __future__ import annotations

import subprocess
import sys
from typing import Annotated

import typer

from app.core.paths import REPO_ROOT
from app.ingest import r2_freshness_audit
from app.ingest import r2_inventory_repair
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


@app.command("r2-freshness")
def r2_freshness(
    schemas: str = typer.Option("mbo", "--schemas", help="Comma-separated schema filter."),
    expected_symbols: str = typer.Option(
        ",".join(r2_freshness_audit.CORE_MBO_SYMBOLS),
        "--expected-symbols",
        help="Comma-separated symbols expected in the selected schema.",
    ),
    expected_schemas: str = typer.Option(
        ",".join(r2_freshness_audit.EXPECTED_MARKET_SCHEMAS),
        "--expected-schemas",
        help="Comma-separated schemas expected somewhere in R2 _inventory.json.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON."),
    no_write: bool = typer.Option(False, "--no-write", help="Do not write the latest JSON report."),
) -> None:
    """Audit local/R2 freshness for selected warehouse schemas."""
    audit = r2_freshness_audit.run(
        schemas=r2_freshness_audit._parse_csv_set(schemas),
        expected_symbols=r2_freshness_audit._parse_csv_list(expected_symbols),
        expected_schemas=r2_freshness_audit._parse_csv_list(expected_schemas),
        write_report=not no_write,
    )
    if json_output:
        emit_json(r2_freshness_audit.to_dict(audit))
    else:
        emit_lines(r2_freshness_audit.format_text(audit).splitlines())
    if not audit.ok:
        raise typer.Exit(1)


@app.command("r2-repair-inventory")
def r2_repair_inventory(
    schemas: str = typer.Option("mbo", "--schemas", help="Comma-separated schema filter."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show counts without writing."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON."),
) -> None:
    """Repair selected R2 inventory schemas from bucket objects."""
    result = r2_inventory_repair.run(
        schemas=r2_freshness_audit._parse_csv_set(schemas),
        dry_run=dry_run,
    )
    if json_output:
        emit_json(r2_inventory_repair.to_dict(result))
    else:
        emit_lines(r2_inventory_repair.format_text(result).splitlines())
    if not result.ok:
        raise typer.Exit(1)
