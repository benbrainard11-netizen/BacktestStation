"""Tests for the scheduled-task dataset scan CLI."""

from __future__ import annotations

import json
import os
from pathlib import Path

from sqlalchemy import select

from app.cli import scan_datasets
from app.db import models
from app.db.session import make_engine, make_session_factory


def _write_old_file(path: Path, content: bytes = b"x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    old = path.stat().st_mtime - 600
    os.utime(path, (old, old))


def test_scan_datasets_cli_refreshes_registry(tmp_path: Path, capsys) -> None:
    data_root = tmp_path / "warehouse"
    parquet = (
        data_root
        / "processed"
        / "bars"
        / "timeframe=1m"
        / "symbol=NQ.c.0"
        / "date=2026-04-24"
        / "part-000.parquet"
    )
    _write_old_file(parquet, b"bars")
    db_url = f"sqlite:///{tmp_path / 'meta.sqlite'}"

    rc = scan_datasets.main(
        [
            "--data-root",
            str(data_root),
            "--database-url",
            db_url,
            "--json",
        ]
    )

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["scanned"] == 1
    assert payload["added"] == 1
    assert payload["errors"] == []

    engine = make_engine(db_url)
    SessionLocal = make_session_factory(engine)
    with SessionLocal() as session:
        rows = list(session.scalars(select(models.Dataset)).all())
    assert len(rows) == 1
    assert rows[0].schema == "ohlcv-1m"
    assert rows[0].symbol == "NQ.c.0"
    assert rows[0].kind == "parquet"


def test_scan_datasets_cli_returns_error_when_root_missing(tmp_path: Path, capsys) -> None:
    rc = scan_datasets.main(["--data-root", str(tmp_path / "missing")])

    assert rc == 2
    assert "data_root does not exist" in capsys.readouterr().err
