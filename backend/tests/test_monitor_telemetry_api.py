"""Tests for the telemetry endpoints used by remote runners.

Covers POST /api/monitor/heartbeats and POST /api/monitor/signals — the
HTTP path ben-247's pre10_live_runner uses to land status updates in
benpc's canonical DB. Plus the GET /heartbeats and /heartbeats/latest
that back the Overview's Live Bot panel.
"""

from collections.abc import Generator
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.db import models
from app.db.session import (
    create_all,
    get_session,
    make_engine,
    make_session_factory,
)
from app.main import app


@pytest.fixture
def session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = make_engine(f"sqlite:///{tmp_path / 'monitor.sqlite'}")
    create_all(engine)
    return make_session_factory(engine)


@pytest.fixture
def client(
    session_factory: sessionmaker[Session],
) -> Generator[TestClient, None, None]:
    def override_get_session() -> Generator[Session, None, None]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# --- POST /heartbeats ---------------------------------------------------------


def test_post_heartbeat_persists_payload(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    body = {
        "source": "pre10_live_runner",
        "status": "running",
        "ts": "2026-05-07T13:30:00",
        "payload": {
            "balance": 25_329.0,
            "profit": 329.0,
            "mode": "PAPER",
            "trades_today": 1,
        },
    }
    res = client.post("/api/monitor/heartbeats", json=body)
    assert res.status_code == 201
    data = res.json()
    assert data["source"] == "pre10_live_runner"
    assert data["status"] == "running"
    assert data["payload"]["balance"] == 25_329.0
    assert data["payload"]["mode"] == "PAPER"

    with session_factory() as session:
        rows = session.query(models.LiveHeartbeat).all()
        assert len(rows) == 1
        assert rows[0].payload["profit"] == 329.0


def test_post_heartbeat_without_ts_uses_server_time(client: TestClient) -> None:
    body = {"source": "test_runner", "status": "running"}
    res = client.post("/api/monitor/heartbeats", json=body)
    assert res.status_code == 201
    ts = datetime.fromisoformat(res.json()["ts"])
    # Server stamped — should be within a few seconds of "now"
    assert abs((datetime.utcnow() - ts).total_seconds()) < 5


def test_post_heartbeat_rejects_long_source(client: TestClient) -> None:
    body = {"source": "x" * 200, "status": "running"}
    res = client.post("/api/monitor/heartbeats", json=body)
    assert res.status_code == 422


# --- GET /heartbeats and /heartbeats/latest -----------------------------------


def _seed_heartbeats(
    factory: sessionmaker[Session],
    rows: list[tuple[datetime, str, str, dict | None]],
) -> None:
    with factory() as session:
        for ts, source, status, payload in rows:
            session.add(
                models.LiveHeartbeat(
                    ts=ts, source=source, status=status, payload=payload
                )
            )
        session.commit()


def test_list_heartbeats_newest_first(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    base = datetime(2026, 5, 7, 13, 0)
    _seed_heartbeats(
        session_factory,
        [
            (base, "pre10_live_runner", "running", {"v": 1}),
            (base + timedelta(minutes=1), "pre10_live_runner", "running", {"v": 2}),
            (base + timedelta(minutes=2), "other_bot", "running", {"v": 99}),
        ],
    )
    res = client.get("/api/monitor/heartbeats")
    assert res.status_code == 200
    payloads = [r["payload"]["v"] for r in res.json()]
    assert payloads == [99, 2, 1]


def test_list_heartbeats_filtered_by_source(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    base = datetime(2026, 5, 7, 13, 0)
    _seed_heartbeats(
        session_factory,
        [
            (base, "pre10_live_runner", "running", {"v": 1}),
            (base + timedelta(minutes=1), "other_bot", "running", {"v": 99}),
        ],
    )
    res = client.get("/api/monitor/heartbeats?source=pre10_live_runner")
    assert res.status_code == 200
    body = res.json()
    assert len(body) == 1
    assert body[0]["payload"]["v"] == 1


def test_latest_heartbeat_404_when_empty(client: TestClient) -> None:
    res = client.get("/api/monitor/heartbeats/latest")
    assert res.status_code == 404


def test_latest_heartbeat_returns_newest(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    base = datetime(2026, 5, 7, 13, 0)
    _seed_heartbeats(
        session_factory,
        [
            (base, "pre10_live_runner", "running", {"v": 1}),
            (base + timedelta(minutes=2), "pre10_live_runner", "halted", {"v": 2}),
            (base + timedelta(minutes=1), "pre10_live_runner", "running", {"v": 3}),
        ],
    )
    res = client.get("/api/monitor/heartbeats/latest?source=pre10_live_runner")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "halted"
    assert body["payload"]["v"] == 2


# --- POST /signals ------------------------------------------------------------


def test_post_signal_persists(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    # Seed a strategy + version so strategy_version_id resolves
    with session_factory() as session:
        strat = models.Strategy(name="Pre10", slug="pre10")
        ver = models.StrategyVersion(strategy=strat, version="v04")
        session.add(strat)
        session.flush()
        version_id = ver.id
        session.commit()

    body = {
        "strategy_version_id": version_id,
        "ts": "2026-05-07T13:50:00",
        "side": "sell",
        "price": 25_278.75,
        "reason": "router P_up=0.071",
        "executed": False,
    }
    res = client.post("/api/monitor/signals", json=body)
    assert res.status_code == 201
    data = res.json()
    assert data["side"] == "sell"
    assert data["price"] == 25_278.75
    assert data["reason"] == "router P_up=0.071"
    assert data["executed"] is False

    with session_factory() as session:
        rows = session.query(models.LiveSignal).all()
        assert len(rows) == 1
        assert rows[0].strategy_version_id == version_id


def test_post_signal_orphan_version_id_allowed(client: TestClient) -> None:
    """No FK enforcement — sometimes the runner doesn't know its version_id."""
    body = {
        "ts": "2026-05-07T13:50:00",
        "side": "exit",
        "price": 25_192.5,
        "reason": "trail_stop R=+2.11",
        "executed": True,
    }
    res = client.post("/api/monitor/signals", json=body)
    assert res.status_code == 201
    assert res.json()["strategy_version_id"] is None
