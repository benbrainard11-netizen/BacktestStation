"""PUT /api/backtests/{id}/tags tests."""

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
    engine = make_engine(f"sqlite:///{tmp_path / 'tags.sqlite'}")
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


def _seed_run(factory: sessionmaker[Session]) -> int:
    with factory() as session:
        strategy = models.Strategy(name="T", slug="t")
        version = models.StrategyVersion(strategy=strategy, version="v1")
        run = models.BacktestRun(
            strategy_version=version,
            symbol="NQ",
            import_source="t",
            start_ts=datetime(2026, 1, 2),
            end_ts=datetime(2026, 1, 3),
        )
        session.add(strategy)
        session.commit()
        return run.id


def test_set_tags_success(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    run_id = _seed_run(session_factory)

    response = client.put(
        f"/api/backtests/{run_id}/tags",
        json={"tags": ["validated", "live-candidate"]},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["tags"] == ["validated", "live-candidate"]


def test_set_tags_trims_and_dedupes(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    run_id = _seed_run(session_factory)

    response = client.put(
        f"/api/backtests/{run_id}/tags",
        json={"tags": ["  validated  ", "validated", "live", ""]},
    )
    assert response.status_code == 200
    assert response.json()["tags"] == ["validated", "live"]


def test_set_tags_empty_list_clears(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    run_id = _seed_run(session_factory)
    client.put(
        f"/api/backtests/{run_id}/tags",
        json={"tags": ["foo"]},
    )
    response = client.put(f"/api/backtests/{run_id}/tags", json={"tags": []})
    assert response.status_code == 200
    assert response.json()["tags"] is None


def test_set_tags_missing_run_returns_404(client: TestClient) -> None:
    response = client.put("/api/backtests/9999/tags", json={"tags": ["a"]})
    assert response.status_code == 404
