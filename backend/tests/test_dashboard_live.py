"""Tests for dashboard Live Monitor endpoints."""

from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.db import models
from app.db.session import create_all, get_session, make_engine, make_session_factory
from app.main import app

ARTIFACT_ROOT = Path(__file__).parent / "_artifacts" / "dashboard_live"


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
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_session, None)


def _seed_live_fixture(factory: sessionmaker[Session]) -> dict[str, int]:
    with factory() as session:
        strategy = models.Strategy(
            name="Two Family Core",
            slug="two-family-core",
            status="testing",
        )
        version = models.StrategyVersion(strategy=strategy, version="v21")
        session.add(strategy)
        session.flush()
        candidate = models.StrategyPromotionCheck(
            strategy_id=strategy.id,
            strategy_version_id=version.id,
            candidate_name="2-family core",
            candidate_config_id="two_family_core_v21",
            status="pass_paper",
        )
        signal = models.LiveSignal(
            strategy_version_id=version.id,
            ts=dt.datetime(2026, 5, 18, 12, 30),
            side="long",
            price=18750.25,
            reason="fixture signal",
            executed=False,
        )
        session.add_all([candidate, signal])
        session.commit()
        return {"candidate_id": candidate.id, "signal_id": signal.id}


def test_live_active_candidates_returns_empty_state_and_start_options(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    ids = _seed_live_fixture(session_factory)

    response = client.get("/api/dashboard/live/active-candidates")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["paper_trade_active"] is False
    assert body["active_count"] == 0
    assert body["candidates"] == []
    assert body["start_command_template"] == "bs paper start <candidate_id>"
    assert body["paper_ready_candidates"][0]["candidate_id"] == ids["candidate_id"]
    assert body["paper_ready_candidates"][0]["start_command"] == (
        f"bs paper start {ids['candidate_id']}"
    )


def test_live_signals_and_empty_stub_payloads(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    ids = _seed_live_fixture(session_factory)

    signals = client.get(
        "/api/dashboard/live/signals",
        params={"since": "2026-05-18T12:00:00"},
    )
    assert signals.status_code == 200, signals.text
    signals_body = signals.json()
    assert signals_body["count"] == 1
    assert signals_body["signals"][0]["id"] == ids["signal_id"]
    assert signals_body["signals"][0]["executed"] is False

    drift = client.get("/api/dashboard/live/drift-report")
    assert drift.status_code == 200, drift.text
    assert drift.json()["has_report"] is False
    assert drift.json()["status"] == "not_started"

    positions = client.get("/api/dashboard/live/positions")
    assert positions.status_code == 200, positions.text
    assert positions.json()["count"] == 0
    assert positions.json()["positions"] == []
