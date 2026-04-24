"""GET /api/backtests/{id}/config tests."""

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
    engine = make_engine(f"sqlite:///{tmp_path / 'cfg.sqlite'}")
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


def test_config_snapshot_returns_stored_payload(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    with session_factory() as session:
        strategy = models.Strategy(name="T", slug="t")
        version = models.StrategyVersion(strategy=strategy, version="v1")
        run = models.BacktestRun(
            strategy_version=version,
            symbol="NQ",
            import_source="t",
            start_ts=datetime(2024, 1, 2),
            end_ts=datetime(2024, 1, 3),
        )
        run.config_snapshot = models.ConfigSnapshot(
            payload={"symbol": "NQ", "slippage": 0.25, "commission": 1.5}
        )
        session.add(strategy)
        session.commit()
        run_id = run.id

    response = client.get(f"/api/backtests/{run_id}/config")
    assert response.status_code == 200
    body = response.json()
    assert body["backtest_run_id"] == run_id
    assert body["payload"] == {
        "symbol": "NQ",
        "slippage": 0.25,
        "commission": 1.5,
    }


def test_config_snapshot_missing_snapshot_returns_404(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    with session_factory() as session:
        strategy = models.Strategy(name="NoConfig", slug="no-config")
        version = models.StrategyVersion(strategy=strategy, version="v1")
        run = models.BacktestRun(
            strategy_version=version, symbol="NQ", import_source="t"
        )
        session.add(strategy)
        session.commit()
        run_id = run.id

    response = client.get(f"/api/backtests/{run_id}/config")
    assert response.status_code == 404
    assert response.json()["detail"] == "Backtest config snapshot not found"


def test_config_snapshot_missing_run_returns_404(client: TestClient) -> None:
    response = client.get("/api/backtests/9999/config")
    assert response.status_code == 404
    assert response.json()["detail"] == "Backtest run not found"
