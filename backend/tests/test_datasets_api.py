"""Tests for the datasets registry API + scanner."""

from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.db import models
from app.db.session import create_all, get_session, make_engine, make_session_factory
from app.main import app
from app.services import dataset_scanner


@pytest.fixture
def session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = make_engine(f"sqlite:///{tmp_path / 'datasets.sqlite'}")
    create_all(engine)
    return make_session_factory(engine)


@pytest.fixture
def data_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolated data root for the test, surfaced via BS_DATA_ROOT."""
    root = tmp_path / "data"
    (root / "raw" / "live").mkdir(parents=True)
    (root / "raw" / "historical").mkdir(parents=True)
    (root / "parquet" / "NQ.c.0" / "tbbo").mkdir(parents=True)
    monkeypatch.setenv("BS_DATA_ROOT", str(root))
    return root


@pytest.fixture
def client(
    session_factory: sessionmaker[Session], data_root: Path
) -> Generator[TestClient, None, None]:
    def override_get_session() -> Generator[Session, None, None]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _write_old_file(path: Path, content: bytes = b"x") -> None:
    """Write a file with mtime safely outside the SKIP_RECENT window."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    old = path.stat().st_mtime - 600  # 10 min ago
    os.utime(path, (old, old))


# --- list endpoint --------------------------------------------------------


def test_list_empty(client: TestClient) -> None:
    response = client.get("/api/datasets")
    assert response.status_code == 200
    assert response.json() == []


def test_list_after_scan(client: TestClient, data_root: Path) -> None:
    _write_old_file(
        data_root / "raw" / "live" / "GLBX.MDP3-tbbo-2026-04-24.dbn",
        b"abcdef",
    )
    scan = client.post("/api/datasets/scan").json()
    assert scan["scanned"] == 1
    assert scan["added"] == 1

    rows = client.get("/api/datasets").json()
    assert len(rows) == 1
    assert rows[0]["dataset_code"] == "GLBX.MDP3"
    assert rows[0]["schema"] == "tbbo"
    assert rows[0]["source"] == "live"
    assert rows[0]["kind"] == "dbn"
    assert rows[0]["file_size_bytes"] == 6


def test_list_filters(client: TestClient, data_root: Path) -> None:
    _write_old_file(
        data_root / "raw" / "live" / "GLBX.MDP3-tbbo-2026-04-24.dbn", b"a"
    )
    _write_old_file(
        data_root / "raw" / "historical" / "GLBX.MDP3-mbp-1-2026-03-15.dbn",
        b"b",
    )
    _write_old_file(
        data_root / "parquet" / "NQ.c.0" / "tbbo" / "2026-04-24.parquet",
        b"c",
    )
    client.post("/api/datasets/scan")

    live_only = client.get("/api/datasets", params={"source": "live"}).json()
    assert all(r["source"] == "live" for r in live_only)
    assert len(live_only) >= 1  # parquet defaults to "live" too

    parquet_only = client.get("/api/datasets", params={"kind": "parquet"}).json()
    assert len(parquet_only) == 1
    assert parquet_only[0]["symbol"] == "NQ.c.0"

    historical = client.get(
        "/api/datasets", params={"source": "historical"}
    ).json()
    assert len(historical) == 1
    assert historical[0]["schema"] == "mbp-1"


# --- scan idempotency / change detection ---------------------------------


def test_scan_idempotent(client: TestClient, data_root: Path) -> None:
    _write_old_file(
        data_root / "raw" / "live" / "GLBX.MDP3-tbbo-2026-04-24.dbn", b"x" * 100
    )
    first = client.post("/api/datasets/scan").json()
    assert first["added"] == 1
    assert first["updated"] == 0

    second = client.post("/api/datasets/scan").json()
    assert second["added"] == 0
    assert second["updated"] == 0
    assert second["scanned"] == 1


def test_scan_detects_growth(client: TestClient, data_root: Path) -> None:
    """File got bigger between scans (e.g. ingester appended) — row updates."""
    path = data_root / "raw" / "live" / "GLBX.MDP3-tbbo-2026-04-24.dbn"
    _write_old_file(path, b"x" * 100)
    client.post("/api/datasets/scan")

    _write_old_file(path, b"x" * 500)
    second = client.post("/api/datasets/scan").json()
    assert second["updated"] == 1

    rows = client.get("/api/datasets").json()
    assert rows[0]["file_size_bytes"] == 500


def test_scan_removes_missing_files(
    client: TestClient, data_root: Path
) -> None:
    path = data_root / "raw" / "live" / "GLBX.MDP3-tbbo-2026-04-24.dbn"
    _write_old_file(path)
    client.post("/api/datasets/scan")

    path.unlink()
    second = client.post("/api/datasets/scan").json()
    assert second["removed"] == 1

    assert client.get("/api/datasets").json() == []


def test_scan_skips_recent_files(
    client: TestClient, data_root: Path
) -> None:
    """File modified in the last minute is skipped (might be in-progress write)."""
    path = data_root / "raw" / "live" / "GLBX.MDP3-tbbo-2026-04-24.dbn"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"in-progress")
    # mtime is now (within SKIP_RECENT_SEC)

    result = client.post("/api/datasets/scan").json()
    assert result["scanned"] == 0
    assert result["skipped"] == 1


def test_scan_skips_unrecognized_filenames(
    client: TestClient, data_root: Path
) -> None:
    """Random files in the warehouse don't crash the scanner."""
    _write_old_file(data_root / "raw" / "live" / "garbage.txt", b"junk")
    result = client.post("/api/datasets/scan").json()
    # The .txt file isn't a DBN so the walker doesn't even consider it.
    # No errors, no rows added.
    assert result["added"] == 0


def test_scan_returns_503_when_root_missing(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("BS_DATA_ROOT", str(tmp_path / "does-not-exist"))
    response = client.post("/api/datasets/scan")
    assert response.status_code == 503


# --- direct scanner unit tests ------------------------------------------


def test_scanner_parses_parquet_path(
    session_factory: sessionmaker[Session], tmp_path: Path
) -> None:
    root = tmp_path / "data"
    parquet = root / "parquet" / "ES.c.0" / "ohlcv-1m" / "2026-04-24.parquet"
    _write_old_file(parquet, b"parq")

    with session_factory() as session:
        result = dataset_scanner.scan_datasets(session, root)

    assert result.added == 1

    with session_factory() as session:
        rows = list(session.scalars(
            __import__("sqlalchemy").select(models.Dataset)
        ).all())
        assert len(rows) == 1
        assert rows[0].symbol == "ES.c.0"
        assert rows[0].schema == "ohlcv-1m"
        assert rows[0].kind == "parquet"
