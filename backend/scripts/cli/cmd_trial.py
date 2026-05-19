from __future__ import annotations

import os
from typing import Any

import typer
from sqlalchemy import select

from app.db import models
from app.db.session import create_all, make_engine, make_session_factory
from scripts.cli.output_format import compact_dt, emit_json, emit_lines, render_table

app = typer.Typer(
    help="Trial registry commands.",
    add_completion=False,
    rich_markup_mode=None,
)


def _session():
    engine = make_engine(os.getenv("BS_META_DB_URL"))
    create_all(engine)
    return make_session_factory(engine)()


def _row(group: models.TrialGroup) -> dict[str, Any]:
    return {
        "id": group.id,
        "hypothesis_id": group.hypothesis_id,
        "name": group.name,
        "status": group.status,
        "created_at": compact_dt(group.created_at),
        "completed_at": compact_dt(group.completed_at),
    }


@app.command("list")
def list_trials(
    hypothesis_id: int | None = typer.Option(None, "--hypothesis-id", help="Filter by hypothesis."),
    status: str | None = typer.Option(None, "--status", help="Filter by group status."),
    limit: int = typer.Option(20, "--limit", min=1, max=500, help="Max rows."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON."),
) -> None:
    """List trial groups."""
    with _session() as session:
        stmt = select(models.TrialGroup).order_by(models.TrialGroup.created_at.desc())
        if hypothesis_id is not None:
            stmt = stmt.where(models.TrialGroup.hypothesis_id == hypothesis_id)
        if status is not None:
            stmt = stmt.where(models.TrialGroup.status == status)
        rows = [_row(group) for group in session.scalars(stmt.limit(limit))]
    if json_output:
        emit_json({"trial_groups": rows})
    else:
        emit_lines(
            render_table(
                rows,
                [
                    ("id", "id"),
                    ("hypothesis_id", "hypothesis"),
                    ("status", "status"),
                    ("name", "name"),
                ],
            )
        )
