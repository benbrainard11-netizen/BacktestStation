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
    quick: bool = typer.Option(False, "--quick", help="Skip slow gates when runner lands."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON."),
) -> None:
    """Validate a dataset snapshot once the full runner is wired."""
    payload = {
        "snapshot_id": snapshot_id,
        "schemas": schemas,
        "quick": quick,
        "status": "not_implemented",
        "message": "validation runner not landed yet",
    }
    if json_output:
        emit_json(payload)
    else:
        emit_lines(
            [
                "Validation runner not landed yet.",
                f"snapshot_id: {snapshot_id}",
                f"schemas: {schemas or 'all'}",
                f"quick: {quick}",
            ]
        )
    raise typer.Exit(1)
