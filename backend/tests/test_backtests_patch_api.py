"""PATCH /api/backtests/{id} rename endpoint tests."""

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
    engine = make_engine(f"sqlite:///{tmp_path / 'patch.sqlite'}")
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


def _seed_run(factory: sessionmaker[Session], name: str | None = None) -> int:
    with factory() as session:
        strategy = models.Strategy(name="Test", slug="test", status="testing")
        version = models.StrategyVersion(strategy=strategy, version="v1")
        run = models.BacktestRun(
            strategy_version=version,
            symbol="NQ",
            name=name,
            import_source="fixture",
            start_ts=datetime(2026, 1, 2),
            end_ts=datetime(2026, 1, 3),
        )
        session.add_all([strategy, version, run])
        session.commit()
        return run.id


def test_rename_existing_run(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    run_id = _seed_run(session_factory)

    response = client.patch(
        f"/api/backtests/{run_id}",
        json={"name": "Q1 sanity check"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == run_id
    assert body["name"] == "Q1 sanity check"

    # Confirmed via a follow-up GET.
    reread = client.get(f"/api/backtests/{run_id}")
    assert reread.json()["name"] == "Q1 sanity check"


def test_rename_trims_whitespace(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    run_id = _seed_run(session_factory)

    response = client.patch(
        f"/api/backtests/{run_id}",
        json={"name": "  padded name  "},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "padded name"


def test_rename_rejects_empty_string(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    run_id = _seed_run(session_factory, name="prior name")

    response = client.patch(
        f"/api/backtests/{run_id}",
        json={"name": ""},
    )
    assert response.status_code == 422
    # Name should not have changed.
    reread = client.get(f"/api/backtests/{run_id}")
    assert reread.json()["name"] == "prior name"


def test_rename_rejects_whitespace_only_string(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    run_id = _seed_run(session_factory, name="prior name")

    response = client.patch(
        f"/api/backtests/{run_id}",
        json={"name": "   "},
    )
    assert response.status_code == 422
    reread = client.get(f"/api/backtests/{run_id}")
    assert reread.json()["name"] == "prior name"


def test_rename_clears_with_null(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    run_id = _seed_run(session_factory, name="initial")

    response = client.patch(
        f"/api/backtests/{run_id}",
        json={"name": None},
    )
    assert response.status_code == 200
    assert response.json()["name"] is None

    reread = client.get(f"/api/backtests/{run_id}")
    assert reread.json()["name"] is None


def test_rename_missing_run_returns_404(client: TestClient) -> None:
    response = client.patch("/api/backtests/9999", json={"name": "ghost"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Backtest run not found"
