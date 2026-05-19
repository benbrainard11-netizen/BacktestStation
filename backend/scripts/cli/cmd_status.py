from __future__ import annotations

import os
import subprocess
from typing import Any

import typer
from sqlalchemy import inspect, select, text

from app.core.paths import REPO_ROOT
from app.db import models
from app.db.session import create_all, make_engine, make_session_factory
from scripts.cli.output_format import compact_dt, emit_json, emit_lines, render_table


def _session():
    engine = make_engine(os.getenv("BS_META_DB_URL"))
    create_all(engine)
    return make_session_factory(engine)()


def _git_snapshot() -> dict[str, Any]:
    def run(args: list[str]) -> str:
        result = subprocess.run(args, cwd=REPO_ROOT, text=True, capture_output=True)
        return result.stdout.strip() if result.returncode == 0 else ""

    branch = run(["git", "branch", "--show-current"])
    sha = run(["git", "rev-parse", "--short", "HEAD"])
    upstream = run(["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"])
    ahead = behind = 0
    if upstream:
        counts = run(["git", "rev-list", "--left-right", "--count", f"{upstream}...HEAD"])
        if counts:
            behind, ahead = [int(part) for part in counts.split()]
    return {"branch": branch, "sha": sha, "upstream": upstream, "ahead": ahead, "behind": behind}


def _candidate_counts(session) -> list[dict[str, Any]]:
    inspector = inspect(session.bind)
    columns = {col["name"] for col in inspector.get_columns("strategy_versions")}
    if "status" not in columns:
        return []
    rows = session.execute(
        text(
            "SELECT status, COUNT(*) AS count "
            "FROM strategy_versions GROUP BY status ORDER BY status"
        )
    ).all()
    return [{"status": status, "count": count} for status, count in rows]


def _recent_trial_groups(session) -> list[dict[str, Any]]:
    rows = session.scalars(
        select(models.TrialGroup).order_by(models.TrialGroup.created_at.desc()).limit(5)
    ).all()
    return [
        {
            "id": row.id,
            "name": row.name,
            "status": row.status,
            "created_at": compact_dt(row.created_at),
        }
        for row in rows
    ]


def _recent_snapshots(session) -> list[dict[str, Any]]:
    rows = session.scalars(
        select(models.DatasetSnapshot).order_by(models.DatasetSnapshot.created_at.desc()).limit(5)
    ).all()
    return [
        {
            "snapshot_id": row.snapshot_id,
            "name": row.name or "",
            "status": row.status,
            "created_at": compact_dt(row.created_at),
        }
        for row in rows
    ]


def _recent_runs(session) -> list[dict[str, Any]]:
    rows = session.scalars(
        select(models.BacktestRun).order_by(models.BacktestRun.created_at.desc()).limit(5)
    ).all()
    return [
        {
            "id": row.id,
            "symbol": row.symbol,
            "status": row.status,
            "created_at": compact_dt(row.created_at),
        }
        for row in rows
    ]


def build_status() -> dict[str, Any]:
    with _session() as session:
        return {
            "git": _git_snapshot(),
            "candidate_counts": _candidate_counts(session),
            "trial_groups": _recent_trial_groups(session),
            "dataset_snapshots": _recent_snapshots(session),
            "backtest_runs": _recent_runs(session),
        }


def status(json_output: bool = typer.Option(False, "--json", help="Emit JSON.")) -> None:
    """Show current project status."""
    payload = build_status()
    if json_output:
        emit_json(payload)
        return
    lines = [
        "BacktestStation status",
        "",
        f"Git: {payload['git']['branch']} @ {payload['git']['sha']} "
        f"(ahead {payload['git']['ahead']}, behind {payload['git']['behind']})",
        "",
        "Candidate status counts:",
        *render_table(payload["candidate_counts"], [("status", "status"), ("count", "count")]),
        "",
        "Recent trial groups:",
        *render_table(
            payload["trial_groups"], [("id", "id"), ("name", "name"), ("status", "status")]
        ),
        "",
        "Recent dataset snapshots:",
        *render_table(
            payload["dataset_snapshots"], [("snapshot_id", "snapshot"), ("status", "status")]
        ),
        "",
        "Recent backtest runs:",
        *render_table(
            payload["backtest_runs"], [("id", "id"), ("symbol", "symbol"), ("status", "status")]
        ),
    ]
    emit_lines(lines)
