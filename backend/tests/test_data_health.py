"""Tests for /api/data-health + the underlying service."""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import models
from app.db.session import (
    create_all,
    get_session,
    make_engine,
    make_session_factory,
)
from app.main import app
from app.services import data_health, scheduled_tasks

# --- Fixtures ------------------------------------------------------------


@pytest.fixture
def session(tmp_path: Path) -> Session:
    engine = make_engine(f"sqlite:///{tmp_path / 'data_health.sqlite'}")
    create_all(engine)
    SessionLocal = make_session_factory(engine)
    s = SessionLocal()
    yield s
    s.close()


@pytest.fixture
def api_client(tmp_path: Path):
    engine = make_engine(f"sqlite:///{tmp_path / 'api.sqlite'}")
    create_all(engine)
    SessionLocal = make_session_factory(engine)

    def _override():
        s = SessionLocal()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_session] = _override
    try:
        with TestClient(app) as client:
            yield client, SessionLocal
    finally:
        app.dependency_overrides.pop(get_session, None)


def _add_dataset(
    session: Session,
    *,
    file_path: str,
    schema: str,
    symbol: str | None,
    source: str,
    kind: str,
    file_size_bytes: int = 1000,
    start_ts: dt.datetime | None = None,
    last_seen_at: dt.datetime | None = None,
) -> models.Dataset:
    ds = models.Dataset(
        file_path=file_path,
        dataset_code="GLBX.MDP3",
        schema=schema,
        symbol=symbol,
        source=source,
        kind=kind,
        file_size_bytes=file_size_bytes,
        row_count=None,
        sha256=None,
        last_seen_at=last_seen_at or dt.datetime(2026, 4, 27, 22, 0, 0),
        start_ts=start_ts,
    )
    session.add(ds)
    session.commit()
    return ds


# --- Service: empty state -----------------------------------------------


def test_get_data_health_empty_warehouse_returns_zero_counts(
    session: Session,
) -> None:
    with patch.object(scheduled_tasks, "is_supported", return_value=False):
        payload = data_health.get_data_health(session)

    assert payload.warehouse.total_partitions == 0
    assert payload.warehouse.total_bytes == 0
    assert payload.warehouse.schemas == []
    assert payload.warehouse.last_scan_ts is None
    assert payload.scheduled_tasks == []
    assert payload.scheduled_tasks_supported is False


# --- Service: warehouse rollup ------------------------------------------


def test_warehouse_summary_rolls_up_per_schema(session: Session) -> None:
    _add_dataset(
        session,
        file_path="/d/raw/databento/tbbo/symbol=NQ.c.0/date=2026-04-27/p.parquet",
        schema="tbbo",
        symbol="NQ.c.0",
        source="live",
        kind="parquet",
        file_size_bytes=1_000_000,
        start_ts=dt.datetime(2026, 4, 27),
    )
    _add_dataset(
        session,
        file_path="/d/raw/databento/tbbo/symbol=ES.c.0/date=2026-04-27/p.parquet",
        schema="tbbo",
        symbol="ES.c.0",
        source="live",
        kind="parquet",
        file_size_bytes=2_000_000,
        start_ts=dt.datetime(2026, 4, 27),
    )
    _add_dataset(
        session,
        file_path="/d/raw/databento/mbp-1/symbol=NQ.c.0/date=2026-03-01/p.parquet",
        schema="mbp-1",
        symbol="NQ.c.0",
        source="historical",
        kind="parquet",
        file_size_bytes=10_000_000,
        start_ts=dt.datetime(2026, 3, 1),
    )

    with patch.object(scheduled_tasks, "is_supported", return_value=False):
        payload = data_health.get_data_health(session)

    assert payload.warehouse.total_partitions == 3
    assert payload.warehouse.total_bytes == 13_000_000

    by_schema = {s.schema: s for s in payload.warehouse.schemas}
    assert set(by_schema.keys()) == {"tbbo", "mbp-1"}
    assert by_schema["tbbo"].partition_count == 2
    assert by_schema["tbbo"].symbols == ["ES.c.0", "NQ.c.0"]
    assert by_schema["tbbo"].earliest_date == dt.date(2026, 4, 27)
    assert by_schema["mbp-1"].partition_count == 1
    assert by_schema["mbp-1"].earliest_date == dt.date(2026, 3, 1)


def test_last_scan_ts_takes_max_across_datasets(session: Session) -> None:
    _add_dataset(
        session,
        file_path="/a.parquet",
        schema="tbbo",
        symbol="NQ.c.0",
        source="live",
        kind="parquet",
        last_seen_at=dt.datetime(2026, 4, 25, 10, 0, 0),
    )
    _add_dataset(
        session,
        file_path="/b.parquet",
        schema="mbp-1",
        symbol="ES.c.0",
        source="historical",
        kind="parquet",
        last_seen_at=dt.datetime(2026, 4, 27, 22, 0, 0),
    )

    with patch.object(scheduled_tasks, "is_supported", return_value=False):
        payload = data_health.get_data_health(session)

    assert payload.warehouse.last_scan_ts == dt.datetime(2026, 4, 27, 22, 0, 0)


# --- Scheduled tasks: PowerShell-unavailable path ------------------------


def test_scheduled_tasks_returns_empty_on_non_windows(session: Session) -> None:
    with patch.object(scheduled_tasks, "is_supported", return_value=False):
        payload = data_health.get_data_health(session)

    assert payload.scheduled_tasks == []
    assert payload.scheduled_tasks_supported is False


def test_dataset_scan_task_is_known() -> None:
    assert "BacktestStationDatasetScan" in scheduled_tasks.KNOWN_TASKS


def test_r2_upload_task_is_known() -> None:
    assert "BacktestStationR2Upload" in scheduled_tasks.KNOWN_TASKS


def test_scheduled_tasks_label_for_result_maps_correctly() -> None:
    """The 0/267011/None mapping is load-bearing for the UI's status dot."""
    assert scheduled_tasks._label_for_result(0, dt.datetime(2026, 4, 27)) == "ok"
    assert scheduled_tasks._label_for_result(1, dt.datetime(2026, 4, 27)) == "failed"
    # Special Windows sentinel for "task has not yet run".
    assert scheduled_tasks._label_for_result(267011, dt.datetime(2026, 4, 27)) == "never_run"
    # No last run yet (last_run_ts None) — also "never_run".
    assert scheduled_tasks._label_for_result(0, None) == "never_run"
    # Result is None (couldn't read) — "unknown".
    assert scheduled_tasks._label_for_result(None, dt.datetime(2026, 4, 27)) == "unknown"


# --- API endpoint --------------------------------------------------------


def test_data_health_endpoint_returns_structured_payload(api_client) -> None:
    client, SessionLocal = api_client
    with SessionLocal() as s:
        _add_dataset(
            s,
            file_path="/d/p.parquet",
            schema="tbbo",
            symbol="NQ.c.0",
            source="live",
            kind="parquet",
            file_size_bytes=500_000,
            start_ts=dt.datetime(2026, 4, 27),
        )

    with patch.object(scheduled_tasks, "is_supported", return_value=False):
        response = client.get("/api/data-health")

    assert response.status_code == 200, response.text
    body = response.json()
    assert "warehouse" in body
    assert "scheduled_tasks" in body
    assert "scheduled_tasks_supported" in body
    assert "disk" in body
    assert "fetched_at" in body
    assert body["warehouse"]["total_partitions"] == 1
    assert body["scheduled_tasks_supported"] is False


def test_data_health_endpoint_includes_disk_struct(api_client) -> None:
    client, _ = api_client
    with patch.object(scheduled_tasks, "is_supported", return_value=False):
        response = client.get("/api/data-health")
    assert response.status_code == 200
    disk = response.json()["disk"]
    assert "path" in disk
    assert "free_bytes" in disk
    assert "used_bytes" in disk
    assert "total_bytes" in disk
    # On a real host these are positive; if the warehouse path doesn't
    # exist they're 0. Either is OK for the test.
    assert disk["free_bytes"] >= 0
    assert disk["total_bytes"] >= 0
