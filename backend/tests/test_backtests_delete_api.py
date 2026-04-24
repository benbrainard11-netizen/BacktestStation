"""DELETE /api/backtests/{id} tests."""

from collections.abc import Generator
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.db import models
from app.db.session import create_all, get_session, make_engine, make_session_factory
from app.main import app


@pytest.fixture
def session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = make_engine(f"sqlite:///{tmp_path / 'delete.sqlite'}")
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


def _seed_full_run(
    factory: sessionmaker[Session], slug: str = "test"
) -> tuple[int, int]:
    """Insert strategy + version + run with trade + equity + metrics + config + note.
    Returns (run_id, trade_id)."""
    with factory() as session:
        strategy = models.Strategy(name="Test", slug=slug, status="testing")
        version = models.StrategyVersion(strategy=strategy, version="v1")
        run = models.BacktestRun(
            strategy_version=version,
            symbol="NQ",
            import_source="fixture",
            start_ts=datetime(2026, 1, 2),
            end_ts=datetime(2026, 1, 3),
        )
        trade = models.Trade(
            entry_ts=datetime(2026, 1, 2, 10, 0),
            symbol="NQ",
            side="long",
            entry_price=21000.0,
            size=1.0,
        )
        equity = models.EquityPoint(ts=datetime(2026, 1, 2, 10, 5), equity=500.0)
        metrics = models.RunMetrics(net_pnl=500.0, trade_count=1)
        config = models.ConfigSnapshot(payload={"symbol": "NQ"})
        run.trades.append(trade)
        run.equity_points.append(equity)
        run.metrics = metrics
        run.config_snapshot = config
        session.add(strategy)
        session.commit()
        note = models.Note(
            body="survives deletion", backtest_run_id=run.id, trade_id=trade.id
        )
        session.add(note)
        session.commit()
        return run.id, trade.id


def test_delete_existing_run_cascades(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    run_id, trade_id = _seed_full_run(session_factory)

    response = client.delete(f"/api/backtests/{run_id}")
    assert response.status_code == 204
    assert response.content == b""

    # Follow-up GET is 404.
    assert client.get(f"/api/backtests/{run_id}").status_code == 404

    # Verify the children are gone at the DB level too.
    with session_factory() as session:
        assert session.get(models.BacktestRun, run_id) is None
        assert session.get(models.Trade, trade_id) is None
        trades = list(
            session.scalars(
                select(models.Trade).where(models.Trade.backtest_run_id == run_id)
            )
        )
        assert trades == []
        equity = list(
            session.scalars(
                select(models.EquityPoint).where(
                    models.EquityPoint.backtest_run_id == run_id
                )
            )
        )
        assert equity == []
        metrics = list(
            session.scalars(
                select(models.RunMetrics).where(
                    models.RunMetrics.backtest_run_id == run_id
                )
            )
        )
        assert metrics == []
        config = list(
            session.scalars(
                select(models.ConfigSnapshot).where(
                    models.ConfigSnapshot.backtest_run_id == run_id
                )
            )
        )
        assert config == []


def test_delete_leaves_notes_as_floating(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """Notes are not cascade-deleted; their run_id/trade_id go to null is NOT the
    current policy — they stay with dangling FKs. This test pins that behavior
    so future changes are deliberate."""
    run_id, _ = _seed_full_run(session_factory)

    client.delete(f"/api/backtests/{run_id}")

    # Note body still accessible via /api/notes (floats without its parent).
    notes = client.get("/api/notes").json()
    assert len(notes) == 1
    assert notes[0]["body"] == "survives deletion"


def test_delete_missing_run_404(client: TestClient) -> None:
    response = client.delete("/api/backtests/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Backtest run not found"


def test_delete_only_removes_target_run(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    run_a_id, _ = _seed_full_run(session_factory, slug="strategy-a")
    run_b_id, _ = _seed_full_run(session_factory, slug="strategy-b")
    assert run_a_id != run_b_id

    client.delete(f"/api/backtests/{run_a_id}")

    assert client.get(f"/api/backtests/{run_a_id}").status_code == 404
    assert client.get(f"/api/backtests/{run_b_id}").status_code == 200
