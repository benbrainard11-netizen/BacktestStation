"""Strategy + StrategyVersion CRUD endpoint tests."""

from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.db import models
from app.db.session import create_all, get_session, make_engine, make_session_factory
from app.main import app


@pytest.fixture
def session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = make_engine(f"sqlite:///{tmp_path / 'strategies.sqlite'}")
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


def test_stages_endpoint_returns_lifecycle_vocabulary(client: TestClient) -> None:
    response = client.get("/api/strategies/stages")
    assert response.status_code == 200
    stages = response.json()["stages"]
    assert "idea" in stages
    assert "research" in stages
    assert "live" in stages
    assert "archived" in stages


def test_create_strategy_success(client: TestClient) -> None:
    response = client.post(
        "/api/strategies",
        json={
            "name": "ORB Fade",
            "slug": "orb-fade",
            "description": "Fade the opening-range breakout.",
            "status": "idea",
            "tags": ["intraday", "nq"],
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["name"] == "ORB Fade"
    assert body["slug"] == "orb-fade"
    assert body["status"] == "idea"
    assert body["tags"] == ["intraday", "nq"]
    assert body["versions"] == []


def test_create_strategy_rejects_duplicate_slug(client: TestClient) -> None:
    client.post(
        "/api/strategies",
        json={"name": "First", "slug": "dup"},
    )
    response = client.post(
        "/api/strategies",
        json={"name": "Second", "slug": "dup"},
    )
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_create_strategy_rejects_invalid_status(client: TestClient) -> None:
    response = client.post(
        "/api/strategies",
        json={"name": "X", "slug": "x", "status": "bogus"},
    )
    assert response.status_code == 422


def test_create_strategy_rejects_empty_name(client: TestClient) -> None:
    response = client.post(
        "/api/strategies",
        json={"name": "   ", "slug": "x"},
    )
    assert response.status_code == 422


def test_patch_strategy_partial_update(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    with session_factory() as session:
        strategy = models.Strategy(name="X", slug="x", status="idea")
        session.add(strategy)
        session.commit()
        sid = strategy.id

    response = client.patch(
        f"/api/strategies/{sid}", json={"status": "research"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "research"
    assert response.json()["name"] == "X"

    client.patch(f"/api/strategies/{sid}", json={"description": "new"})
    response = client.patch(
        f"/api/strategies/{sid}", json={"description": None}
    )
    assert response.status_code == 200
    assert response.json()["description"] is None


def test_patch_strategy_rejects_invalid_status(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    with session_factory() as session:
        s = models.Strategy(name="X", slug="x")
        session.add(s)
        session.commit()
        sid = s.id
    response = client.patch(
        f"/api/strategies/{sid}", json={"status": "nope"}
    )
    assert response.status_code == 422


def test_delete_strategy_cascades(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    with session_factory() as session:
        strategy = models.Strategy(name="X", slug="x")
        version = models.StrategyVersion(strategy=strategy, version="v1")
        session.add(strategy)
        session.commit()
        sid = strategy.id
        vid = version.id

    response = client.delete(f"/api/strategies/{sid}")
    assert response.status_code == 204
    assert client.get(f"/api/strategies/{sid}").status_code == 404
    with session_factory() as session:
        assert session.get(models.StrategyVersion, vid) is None


def test_create_strategy_version_success(client: TestClient) -> None:
    created = client.post(
        "/api/strategies", json={"name": "X", "slug": "x"}
    ).json()
    sid = created["id"]

    response = client.post(
        f"/api/strategies/{sid}/versions",
        json={
            "version": "v1",
            "entry_md": "Enter on breakout.",
            "exit_md": "Stop at low.",
            "risk_md": "1% per trade.",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["version"] == "v1"
    assert body["entry_md"] == "Enter on breakout."
    assert body["strategy_id"] == sid


def test_create_strategy_version_rejects_duplicate(client: TestClient) -> None:
    created = client.post(
        "/api/strategies", json={"name": "X", "slug": "x"}
    ).json()
    sid = created["id"]
    client.post(f"/api/strategies/{sid}/versions", json={"version": "v1"})
    response = client.post(
        f"/api/strategies/{sid}/versions", json={"version": "v1"}
    )
    assert response.status_code == 409


def test_patch_strategy_version_applies_only_sent_fields(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    with session_factory() as session:
        strategy = models.Strategy(name="X", slug="x")
        version = models.StrategyVersion(
            strategy=strategy,
            version="v1",
            entry_md="initial entry",
            exit_md="initial exit",
        )
        session.add(strategy)
        session.commit()
        vid = version.id

    response = client.patch(
        f"/api/strategy-versions/{vid}",
        json={"entry_md": "updated entry"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["entry_md"] == "updated entry"
    assert body["exit_md"] == "initial exit"


def test_delete_strategy_version(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    with session_factory() as session:
        strategy = models.Strategy(name="X", slug="x")
        v = models.StrategyVersion(strategy=strategy, version="v1")
        session.add(strategy)
        session.commit()
        vid = v.id

    assert client.delete(f"/api/strategy-versions/{vid}").status_code == 204
    assert (
        client.patch(
            f"/api/strategy-versions/{vid}", json={"version": "v2"}
        ).status_code
        == 404
    )


def test_missing_strategy_returns_404(client: TestClient) -> None:
    assert client.patch("/api/strategies/9999", json={"name": "x"}).status_code == 404
    assert client.delete("/api/strategies/9999").status_code == 404
    assert (
        client.post(
            "/api/strategies/9999/versions", json={"version": "v1"}
        ).status_code
        == 404
    )
