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
    engine = make_engine(f"sqlite:///{tmp_path / 'api.sqlite'}")
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


def seed_imported_run(session_factory: sessionmaker[Session]) -> int:
    with session_factory() as session:
        strategy = models.Strategy(
            name="Opening Range Breakout",
            slug="orb",
            description="Imported strategy fixture",
            status="testing",
            tags=["nq", "intraday"],
        )
        version = models.StrategyVersion(
            strategy=strategy,
            version="v1",
            entry_md="Breakout entry",
            exit_md="Stop or target",
            risk_md="1R fixed stop",
            git_commit_sha="abc123",
        )
        run = models.BacktestRun(
            strategy_version=version,
            name="January sample",
            symbol="NQ",
            timeframe="1m",
            session_label="RTH",
            start_ts=datetime(2026, 1, 2, 14, 30),
            end_ts=datetime(2026, 1, 2, 21, 0),
            import_source="sample/results",
        )
        run.metrics = models.RunMetrics(
            net_pnl=1250.25,
            net_r=5.5,
            win_rate=0.625,
            profit_factor=1.8,
            max_drawdown=-350.0,
            avg_r=0.22,
            avg_win=1.1,
            avg_loss=-0.8,
            trade_count=8,
            longest_losing_streak=2,
            best_trade=500.0,
            worst_trade=-250.0,
        )
        run.config_snapshot = models.ConfigSnapshot(
            payload={"symbol": "NQ", "risk_per_trade": 100}
        )
        run.trades.append(
            models.Trade(
                entry_ts=datetime(2026, 1, 2, 15, 0),
                exit_ts=datetime(2026, 1, 2, 15, 15),
                symbol="NQ",
                side="long",
                entry_price=21000.0,
                exit_price=21025.0,
                stop_price=20990.0,
                target_price=21025.0,
                size=1.0,
                pnl=500.0,
                r_multiple=2.0,
                exit_reason="target",
                tags=["breakout"],
            )
        )
        run.equity_points.append(
            models.EquityPoint(
                ts=datetime(2026, 1, 2, 15, 15),
                equity=101_250.25,
                drawdown=0.0,
            )
        )
        session.add(strategy)
        session.commit()
        return run.id


def test_read_endpoints_on_empty_db(client: TestClient) -> None:
    assert client.get("/api/strategies").json() == []
    assert client.get("/api/backtests").json() == []
    assert client.get("/api/strategies/1").status_code == 404
    assert client.get("/api/backtests/1").status_code == 404


def test_read_endpoints_return_seeded_imported_run(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    run_id = seed_imported_run(session_factory)

    strategies = client.get("/api/strategies")
    assert strategies.status_code == 200
    strategy = strategies.json()[0]
    assert strategy["slug"] == "orb"
    assert strategy["versions"][0]["version"] == "v1"

    strategy_detail = client.get(f"/api/strategies/{strategy['id']}")
    assert strategy_detail.status_code == 200
    assert strategy_detail.json()["tags"] == ["nq", "intraday"]

    backtests = client.get("/api/backtests")
    assert backtests.status_code == 200
    backtest = backtests.json()[0]
    assert backtest["id"] == run_id
    assert backtest["symbol"] == "NQ"
    assert backtest["status"] == "imported"

    backtest_detail = client.get(f"/api/backtests/{run_id}")
    assert backtest_detail.status_code == 200
    assert backtest_detail.json()["name"] == "January sample"

    trades = client.get(f"/api/backtests/{run_id}/trades")
    assert trades.status_code == 200
    assert trades.json()[0]["exit_reason"] == "target"

    equity = client.get(f"/api/backtests/{run_id}/equity")
    assert equity.status_code == 200
    assert equity.json()[0]["equity"] == 101_250.25

    metrics = client.get(f"/api/backtests/{run_id}/metrics")
    assert metrics.status_code == 200
    assert metrics.json()["profit_factor"] == 1.8
