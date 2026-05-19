"""Tests for dashboard Data Health endpoints."""

from __future__ import annotations

import datetime as dt
import io
import json
import uuid
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.db import models
from app.db.session import create_all, get_session, make_engine, make_session_factory
from app.main import app
from app.services import dashboard_data_health as service
from app.services import dashboard_r2_status as r2_service

ARTIFACT_ROOT = Path(__file__).parent / "_artifacts" / "dashboard_data_health"


class _R2Client:
    def __init__(self, payload: dict):
        self.payload = payload

    def get_object(self, *, Bucket: str, Key: str) -> dict:
        assert Bucket == "bsdata-prod"
        assert Key == "_research_inventory.json"
        body = io.BytesIO(json.dumps(self.payload).encode("utf-8"))
        return {"Body": body}


@pytest.fixture
def session_factory() -> Generator[sessionmaker[Session], None, None]:
    ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    db_path = ARTIFACT_ROOT / f"{uuid.uuid4().hex}.sqlite"
    engine = make_engine(f"sqlite:///{db_path}")
    create_all(engine)
    try:
        yield make_session_factory(engine)
    finally:
        engine.dispose()
        db_path.unlink(missing_ok=True)


@pytest.fixture
def client(
    session_factory: sessionmaker[Session],
) -> Generator[TestClient, None, None]:
    def override_get_session() -> Generator[Session, None, None]:
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = override_get_session
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_session, None)


def _now() -> dt.datetime:
    return dt.datetime(2026, 5, 18, 12, 0, 0, tzinfo=dt.timezone.utc)


def _add_dataset(
    session: Session,
    *,
    schema: str,
    symbol: str,
    date: dt.datetime,
    rows: int,
) -> None:
    session.add(
        models.Dataset(
            file_path=f"C:/data/{schema}/{symbol}/{date:%Y-%m-%d}.parquet",
            dataset_code="GLBX.MDP3",
            schema=schema,
            symbol=symbol,
            source="historical",
            kind="parquet",
            start_ts=date,
            end_ts=date + dt.timedelta(hours=23),
            file_size_bytes=1_000,
            row_count=rows,
            sha256=None,
            last_seen_at=date,
        )
    )


def _add_research_event(
    session: Session,
    *,
    event_id: str,
    feature_name: str,
    symbol: str,
    bar_end_utc: dt.datetime,
) -> None:
    session.add(
        models.ResearchEvent(
            event_id=event_id,
            feature_name=feature_name,
            event_type="fixture",
            bar_end_utc=bar_end_utc,
            primary_symbol=symbol,
            symbols=[symbol],
            timeframe="1m",
            side="high",
            event_data={"fixture": True},
        )
    )


def _add_validation_report(session: Session) -> None:
    report = models.PartitionValidationReport(
        snapshot_id="snap-001",
        generated_at=dt.datetime(2026, 5, 18, 8, 30, 0),
        generator_version="validation-v1",
        total_partitions=3,
        partitions_pass=1,
        partitions_warn=1,
        partitions_fail=1,
        status="completed",
    )
    report.findings.extend(
        [
            models.PartitionValidationFinding(
                partition_r2_key="data/ohlcv/NQ/2026-05-17.parquet",
                schema="ohlcv-1m",
                symbol="NQ.c.0",
                date="2026-05-17",
                gate_name="missing_minutes",
                severity="fail",
            ),
            models.PartitionValidationFinding(
                partition_r2_key="data/ohlcv/ES/2026-05-17.parquet",
                schema="ohlcv-1m",
                symbol="ES.c.0",
                date="2026-05-17",
                gate_name="missing_minutes",
                severity="fail",
            ),
            models.PartitionValidationFinding(
                partition_r2_key="data/tbbo/NQ/2026-05-17.parquet",
                schema="tbbo",
                symbol="NQ.c.0",
                date="2026-05-17",
                gate_name="bid_le_ask",
                severity="warn",
            ),
        ]
    )
    session.add(report)


def test_r2_status_reads_research_inventory(client: TestClient, monkeypatch) -> None:
    payload = {
        "generated_at": "2026-05-18T11:30:00+00:00",
        "artifacts": [{"r2_key": "a.parquet", "size": 1_000_000_000}],
    }
    monkeypatch.setattr(r2_service, "_utc_now", _now)
    monkeypatch.setattr(
        r2_service, "make_s3_client", lambda: (_R2Client(payload), "bsdata-prod")
    )

    response = client.get("/api/dashboard/data-health/r2-status")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["reachable"] is True
    assert body["status"] == "recent"
    assert body["inventory_key"] == "_research_inventory.json"
    assert body["object_count"] == 1
    assert body["total_gb"] == 1.0


def test_r2_status_handles_unavailable_inventory(
    client: TestClient, monkeypatch
) -> None:
    monkeypatch.setattr(r2_service, "_utc_now", _now)
    monkeypatch.setattr(
        r2_service,
        "make_s3_client",
        lambda: (_ for _ in ()).throw(RuntimeError("missing R2 credentials")),
    )

    response = client.get("/api/dashboard/data-health/r2-status")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["reachable"] is False
    assert body["status"] == "unavailable"
    assert "missing R2 credentials" in body["error"]


def test_local_coverage_rolls_up_datasets_and_research_events(
    client: TestClient,
    session_factory: sessionmaker[Session],
    monkeypatch,
) -> None:
    monkeypatch.setattr(service, "_utc_now", _now)
    with session_factory() as session:
        _add_dataset(
            session,
            schema="ohlcv-1m",
            symbol="NQ.c.0",
            date=dt.datetime(2026, 5, 17),
            rows=100,
        )
        _add_dataset(
            session,
            schema="ohlcv-1m",
            symbol="ES.c.0",
            date=dt.datetime(2026, 5, 17),
            rows=100,
        )
        _add_research_event(
            session,
            event_id="evt-1",
            feature_name="smt",
            symbol="NQ.c.0",
            bar_end_utc=dt.datetime(2026, 5, 17, 14, 0, 0),
        )
        _add_research_event(
            session,
            event_id="evt-2",
            feature_name="sweep",
            symbol="ES.c.0",
            bar_end_utc=dt.datetime(2026, 5, 18, 14, 0, 0),
        )
        session.commit()

    response = client.get("/api/dashboard/data-health/local-coverage")

    assert response.status_code == 200, response.text
    items = {item["schema"]: item for item in response.json()["items"]}
    assert items["ohlcv-1m"]["partition_count"] == 2
    assert items["ohlcv-1m"]["symbol_count"] == 2
    assert items["ohlcv-1m"]["row_count"] == 200
    assert items["research_events"]["row_count"] == 2
    assert items["research_events"]["feature_count"] == 2


def test_latest_validation_returns_report_summary(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    with session_factory() as session:
        _add_validation_report(session)
        session.commit()

    response = client.get("/api/dashboard/data-health/latest-validation")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["has_report"] is True
    assert body["snapshot_id"] == "snap-001"
    assert body["partitions_fail"] == 1
    assert body["top_failing_gates"] == [
        {
            "gate_name": "missing_minutes",
            "finding_count": 2,
            "partition_count": 2,
        }
    ]


def test_latest_validation_empty_state(client: TestClient) -> None:
    response = client.get("/api/dashboard/data-health/latest-validation")

    assert response.status_code == 200, response.text
    assert response.json()["has_report"] is False


def test_findings_endpoint_filters_by_severity_and_schema(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    with session_factory() as session:
        _add_validation_report(session)
        session.commit()

    response = client.get(
        "/api/dashboard/data-health/findings",
        params={"severity": "fail", "schema": "ohlcv-1m"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["severity"] == "fail"
    assert body["count"] == 2
    assert {finding["gate_name"] for finding in body["findings"]} == {
        "missing_minutes"
    }
