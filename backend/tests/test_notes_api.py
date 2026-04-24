from collections.abc import Generator
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.db import models
from app.db.session import create_all, get_session, make_engine, make_session_factory
from app.main import app


@pytest.fixture
def session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = make_engine(f"sqlite:///{tmp_path / 'notes.sqlite'}")
    create_all(engine)
    return make_session_factory(engine)


@pytest.fixture
def client(session_factory: sessionmaker[Session]) -> Generator[TestClient, None, None]:
    def override_get_session() -> Generator[Session, None, None]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _seed_run_with_trade(factory: sessionmaker[Session]) -> tuple[int, int]:
    """Insert a strategy + version + run + trade. Return (run_id, trade_id)."""
    with factory() as session:
        strategy = models.Strategy(name="Test", slug="test", status="testing")
        version = models.StrategyVersion(strategy=strategy, version="v1")
        run = models.BacktestRun(
            strategy_version=version,
            symbol="NQ",
            import_source="test-fixture",
        )
        trade = models.Trade(
            entry_ts=datetime(2026, 1, 2, 10, 0),
            symbol="NQ",
            side="long",
            entry_price=21000.0,
            size=1.0,
        )
        run.trades.append(trade)
        session.add(strategy)
        session.commit()
        return run.id, trade.id


def test_create_note_without_attachment(client: TestClient) -> None:
    response = client.post(
        "/api/notes",
        json={"body": "quick thought about NQ regime"},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["id"] > 0
    assert body["body"] == "quick thought about NQ regime"
    assert body["backtest_run_id"] is None
    assert body["trade_id"] is None


def test_create_and_filter_by_backtest_run_id(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    run_id, _ = _seed_run_with_trade(session_factory)

    attached = client.post(
        "/api/notes",
        json={"body": "attached to run", "backtest_run_id": run_id},
    )
    assert attached.status_code == 201
    assert attached.json()["backtest_run_id"] == run_id

    unattached = client.post("/api/notes", json={"body": "floating note"})
    assert unattached.status_code == 201

    filtered = client.get("/api/notes", params={"backtest_run_id": run_id})
    assert filtered.status_code == 200
    rows = filtered.json()
    assert len(rows) == 1
    assert rows[0]["body"] == "attached to run"


def test_create_and_filter_by_trade_id(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    _, trade_id = _seed_run_with_trade(session_factory)

    trade_note = client.post(
        "/api/notes",
        json={"body": "specific trade comment", "trade_id": trade_id},
    )
    assert trade_note.status_code == 201
    assert trade_note.json()["trade_id"] == trade_id

    client.post("/api/notes", json={"body": "unrelated"})

    filtered = client.get("/api/notes", params={"trade_id": trade_id})
    assert filtered.status_code == 200
    rows = filtered.json()
    assert len(rows) == 1
    assert rows[0]["trade_id"] == trade_id


def test_list_notes_newest_first(client: TestClient) -> None:
    ids: list[int] = []
    for i in range(3):
        response = client.post("/api/notes", json={"body": f"note {i}"})
        assert response.status_code == 201
        ids.append(response.json()["id"])

    listed = client.get("/api/notes")
    assert listed.status_code == 200
    rows = listed.json()
    assert len(rows) == 3
    returned_ids = [row["id"] for row in rows]
    assert returned_ids == sorted(ids, reverse=True)


def test_create_note_rejects_missing_run_id(client: TestClient) -> None:
    response = client.post(
        "/api/notes",
        json={"body": "attached to ghost", "backtest_run_id": 9999},
    )
    assert response.status_code == 422
    assert "backtest_run_id 9999 not found" in response.json()["detail"]


def test_create_note_rejects_missing_trade_id(client: TestClient) -> None:
    response = client.post(
        "/api/notes",
        json={"body": "attached to ghost trade", "trade_id": 9999},
    )
    assert response.status_code == 422
    assert "trade_id 9999 not found" in response.json()["detail"]


def test_create_note_rejects_empty_body(client: TestClient) -> None:
    response = client.post("/api/notes", json={"body": ""})
    assert response.status_code == 422


def test_filter_by_both_run_and_trade(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    run_id, trade_id = _seed_run_with_trade(session_factory)

    client.post(
        "/api/notes",
        json={
            "body": "run+trade",
            "backtest_run_id": run_id,
            "trade_id": trade_id,
        },
    )
    client.post(
        "/api/notes", json={"body": "run only", "backtest_run_id": run_id}
    )
    client.post("/api/notes", json={"body": "trade only", "trade_id": trade_id})

    both = client.get(
        "/api/notes",
        params={"backtest_run_id": run_id, "trade_id": trade_id},
    )
    assert both.status_code == 200
    rows = both.json()
    assert len(rows) == 1
    assert rows[0]["body"] == "run+trade"
