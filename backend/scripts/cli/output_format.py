from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import date, datetime
from typing import Any

import typer


def _json_default(value: Any) -> str:
    if isinstance(value, datetime | date):
        return value.isoformat()
    return str(value)


def emit_json(payload: Any) -> None:
    typer.echo(json.dumps(payload, indent=2, default=_json_default))


def emit_lines(lines: Iterable[str]) -> None:
    for line in lines:
        typer.echo(line)


def fail(message: str, *, code: int = 1) -> None:
    typer.echo(message, err=True)
    raise typer.Exit(code)


def render_table(rows: list[dict[str, Any]], columns: list[tuple[str, str]]) -> list[str]:
    if not rows:
        return ["(none)"]
    widths = []
    for key, label in columns:
        values = [label, *(str(row.get(key, "")) for row in rows)]
        widths.append(max(len(value) for value in values))
    header = "  ".join(label.ljust(widths[i]) for i, (_, label) in enumerate(columns))
    rule = "  ".join("-" * width for width in widths)
    lines = [header, rule]
    for row in rows:
        lines.append(
            "  ".join(str(row.get(key, "")).ljust(widths[i]) for i, (key, _) in enumerate(columns))
        )
    return lines


def compact_dt(value: Any) -> str:
    if isinstance(value, datetime):
        return value.replace(microsecond=0).isoformat(sep=" ")
    return "" if value is None else str(value)
