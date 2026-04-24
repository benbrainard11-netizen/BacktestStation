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


# --- Research Workspace extensions ---


def _seed_strategy_and_version(
    factory: sessionmaker[Session],
) -> tuple[int, int]:
    """Insert strategy + version, return (strategy_id, version_id)."""
    with factory() as session:
        strategy = models.Strategy(name="ORB", slug="orb")
        version = models.StrategyVersion(strategy=strategy, version="v1")
        session.add(strategy)
        session.commit()
        return strategy.id, version.id


def test_note_types_endpoint(client: TestClient) -> None:
    response = client.get("/api/notes/types")
    assert response.status_code == 200
    types = response.json()["types"]
    assert "observation" in types
    assert "hypothesis" in types
    assert "decision" in types
    assert "risk_note" in types


def test_create_note_with_strategy_attachment(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    strategy_id, _ = _seed_strategy_and_version(session_factory)
    response = client.post(
        "/api/notes",
        json={
            "body": "thesis: post-RTH retests fade",
            "note_type": "hypothesis",
            "tags": ["RTH", "fade"],
            "strategy_id": strategy_id,
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["strategy_id"] == strategy_id
    assert body["note_type"] == "hypothesis"
    assert body["tags"] == ["RTH", "fade"]


def test_create_note_with_strategy_version_attachment(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    _, version_id = _seed_strategy_and_version(session_factory)
    response = client.post(
        "/api/notes",
        json={
            "body": "v1 risk: stop is too tight on Mondays",
            "note_type": "risk_note",
            "strategy_version_id": version_id,
        },
    )
    assert response.status_code == 201
    assert response.json()["strategy_version_id"] == version_id


def test_create_note_defaults_to_observation(
    client: TestClient,
) -> None:
    response = client.post("/api/notes", json={"body": "just looking"})
    assert response.status_code == 201
    assert response.json()["note_type"] == "observation"


def test_create_note_rejects_invalid_type(client: TestClient) -> None:
    response = client.post(
        "/api/notes",
        json={"body": "x", "note_type": "ai_idea"},
    )
    assert response.status_code == 422


def test_create_note_rejects_missing_strategy(client: TestClient) -> None:
    response = client.post(
        "/api/notes",
        json={"body": "ghost", "strategy_id": 9999},
    )
    assert response.status_code == 422
    assert "strategy_id 9999 not found" in response.json()["detail"]


def test_create_note_rejects_missing_strategy_version(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/notes",
        json={"body": "ghost v", "strategy_version_id": 9999},
    )
    assert response.status_code == 422
    assert "strategy_version_id 9999 not found" in response.json()["detail"]


def test_filter_by_strategy_id(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    s1, _ = _seed_strategy_and_version(session_factory)
    with session_factory() as session:
        other = models.Strategy(name="Other", slug="other")
        session.add(other)
        session.commit()
        s2 = other.id

    client.post("/api/notes", json={"body": "s1 a", "strategy_id": s1})
    client.post("/api/notes", json={"body": "s1 b", "strategy_id": s1})
    client.post("/api/notes", json={"body": "s2 a", "strategy_id": s2})

    rows = client.get("/api/notes", params={"strategy_id": s1}).json()
    assert len(rows) == 2
    assert all(r["strategy_id"] == s1 for r in rows)


def test_filter_by_note_type(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    strategy_id, _ = _seed_strategy_and_version(session_factory)
    client.post(
        "/api/notes",
        json={"body": "h1", "note_type": "hypothesis", "strategy_id": strategy_id},
    )
    client.post(
        "/api/notes",
        json={"body": "o1", "note_type": "observation", "strategy_id": strategy_id},
    )
    client.post(
        "/api/notes",
        json={"body": "h2", "note_type": "hypothesis", "strategy_id": strategy_id},
    )

    rows = client.get(
        "/api/notes",
        params={"strategy_id": strategy_id, "note_type": "hypothesis"},
    ).json()
    assert len(rows) == 2
    assert all(r["note_type"] == "hypothesis" for r in rows)


def test_filter_by_note_type_rejects_invalid(client: TestClient) -> None:
    response = client.get("/api/notes", params={"note_type": "bogus"})
    assert response.status_code == 422


def test_filter_by_tag(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    strategy_id, _ = _seed_strategy_and_version(session_factory)
    client.post(
        "/api/notes",
        json={"body": "x", "strategy_id": strategy_id, "tags": ["RTH", "stop"]},
    )
    client.post(
        "/api/notes",
        json={"body": "y", "strategy_id": strategy_id, "tags": ["overnight"]},
    )
    client.post(
        "/api/notes",
        json={"body": "z", "strategy_id": strategy_id, "tags": ["stop"]},
    )

    rows = client.get(
        "/api/notes",
        params={"strategy_id": strategy_id, "tag": "stop"},
    ).json()
    assert len(rows) == 2
    bodies = {r["body"] for r in rows}
    assert bodies == {"x", "z"}


def test_tags_are_normalized_on_create(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    strategy_id, _ = _seed_strategy_and_version(session_factory)
    response = client.post(
        "/api/notes",
        json={
            "body": "x",
            "strategy_id": strategy_id,
            "tags": ["RTH", "  RTH  ", "", "fade"],
        },
    )
    assert response.status_code == 201
    assert response.json()["tags"] == ["RTH", "fade"]


def test_patch_note_updates_body_and_tags(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    strategy_id, _ = _seed_strategy_and_version(session_factory)
    created = client.post(
        "/api/notes",
        json={"body": "draft", "strategy_id": strategy_id, "tags": ["draft"]},
    ).json()
    note_id = created["id"]

    response = client.patch(
        f"/api/notes/{note_id}",
        json={"body": "final thought", "tags": ["fade", "RTH"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["body"] == "final thought"
    assert body["tags"] == ["fade", "RTH"]
    assert body["updated_at"] is not None
    # note_type untouched
    assert body["note_type"] == "observation"


def test_patch_note_can_change_type(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    strategy_id, _ = _seed_strategy_and_version(session_factory)
    created = client.post(
        "/api/notes",
        json={
            "body": "maybe?",
            "strategy_id": strategy_id,
            "note_type": "question",
        },
    ).json()
    note_id = created["id"]

    response = client.patch(
        f"/api/notes/{note_id}", json={"note_type": "decision"}
    )
    assert response.status_code == 200
    assert response.json()["note_type"] == "decision"


def test_patch_note_rejects_invalid_type(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    strategy_id, _ = _seed_strategy_and_version(session_factory)
    created = client.post(
        "/api/notes", json={"body": "x", "strategy_id": strategy_id}
    ).json()
    response = client.patch(
        f"/api/notes/{created['id']}", json={"note_type": "ai_idea"}
    )
    assert response.status_code == 422


def test_patch_note_rejects_empty_body(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    strategy_id, _ = _seed_strategy_and_version(session_factory)
    created = client.post(
        "/api/notes", json={"body": "x", "strategy_id": strategy_id}
    ).json()
    response = client.patch(
        f"/api/notes/{created['id']}", json={"body": "   "}
    )
    assert response.status_code == 422


def test_delete_note(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    strategy_id, _ = _seed_strategy_and_version(session_factory)
    created = client.post(
        "/api/notes", json={"body": "x", "strategy_id": strategy_id}
    ).json()
    note_id = created["id"]

    assert client.delete(f"/api/notes/{note_id}").status_code == 204
    assert client.patch(f"/api/notes/{note_id}", json={"body": "y"}).status_code == 404


def test_delete_missing_note_returns_404(client: TestClient) -> None:
    assert client.delete("/api/notes/9999").status_code == 404
