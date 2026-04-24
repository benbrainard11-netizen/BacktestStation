"""CSV export endpoint tests."""

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
    engine = make_engine(f"sqlite:///{tmp_path / 'export.sqlite'}")
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


def _seed_run_with_data(factory: sessionmaker[Session]) -> int:
    with factory() as session:
        strategy = models.Strategy(name="Test", slug="test", status="testing")
        version = models.StrategyVersion(strategy=strategy, version="v1")
        run = models.BacktestRun(
            strategy_version=version,
            symbol="NQ",
            timeframe="5m",
            import_source="fixture",
        )
        run.trades.extend(
            [
                models.Trade(
                    entry_ts=datetime(2026, 1, 2, 10, 0),
                    exit_ts=datetime(2026, 1, 2, 10, 5),
                    symbol="NQ",
                    side="long",
                    entry_price=21000.0,
                    exit_price=21025.0,
                    stop_price=20990.0,
                    target_price=21025.0,
                    size=1.0,
                    pnl=500.0,
                    r_multiple=2.5,
                    exit_reason="target",
                    tags=["breakout", "rth"],
                ),
                models.Trade(
                    entry_ts=datetime(2026, 1, 2, 11, 0),
                    exit_ts=datetime(2026, 1, 2, 11, 10),
                    symbol="NQ",
                    side="short",
                    entry_price=21050.0,
                    exit_price=21065.0,
                    stop_price=21065.0,
                    target_price=21005.0,
                    size=1.0,
                    pnl=-300.0,
                    r_multiple=-1.0,
                    exit_reason="SL",
                    tags=None,
                ),
            ]
        )
        run.equity_points.extend(
            [
                models.EquityPoint(
                    ts=datetime(2026, 1, 2, 10, 5), equity=500.0, drawdown=0.0
                ),
                models.EquityPoint(
                    ts=datetime(2026, 1, 2, 11, 10), equity=200.0, drawdown=-300.0
                ),
            ]
        )
        run.metrics = models.RunMetrics(
            net_pnl=200.0,
            net_r=1.5,
            win_rate=0.5,
            profit_factor=1.67,
            max_drawdown=-300.0,
            trade_count=2,
        )
        session.add(strategy)
        session.commit()
        return run.id


def test_trades_csv_exports_rows(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    run_id = _seed_run_with_data(session_factory)

    response = client.get(f"/api/backtests/{run_id}/trades.csv")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert (
        f'filename="backtest_{run_id}_trades.csv"'
        in response.headers["content-disposition"]
    )

    text = response.text
    lines = text.strip().splitlines()
    assert len(lines) == 3  # header + 2 trades
    header = lines[0].split(",")
    assert "entry_ts" in header
    assert "symbol" in header
    assert "tags" in header
    # First trade has tags joined by semicolon
    assert "breakout;rth" in lines[1]
    # Second trade has empty tags cell
    assert lines[2].endswith(",")


def test_equity_csv_exports_rows(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    run_id = _seed_run_with_data(session_factory)

    response = client.get(f"/api/backtests/{run_id}/equity.csv")
    assert response.status_code == 200
    lines = response.text.strip().splitlines()
    assert lines[0] == "ts,equity,drawdown"
    assert len(lines) == 3
    assert "500.0" in lines[1]
    assert "-300.0" in lines[2]


def test_metrics_csv_exports_single_row(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    run_id = _seed_run_with_data(session_factory)

    response = client.get(f"/api/backtests/{run_id}/metrics.csv")
    assert response.status_code == 200
    lines = response.text.strip().splitlines()
    assert len(lines) == 2  # header + 1 row
    assert "net_pnl" in lines[0]
    assert "trade_count" in lines[0]


def test_trades_csv_missing_run_404(client: TestClient) -> None:
    response = client.get("/api/backtests/9999/trades.csv")
    assert response.status_code == 404


def test_metrics_csv_missing_metrics_404(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    # Create a run WITHOUT metrics
    with session_factory() as session:
        strategy = models.Strategy(name="NoMetrics", slug="no-metrics")
        version = models.StrategyVersion(strategy=strategy, version="v1")
        run = models.BacktestRun(
            strategy_version=version, symbol="NQ", import_source="test"
        )
        session.add(strategy)
        session.commit()
        run_id = run.id

    response = client.get(f"/api/backtests/{run_id}/metrics.csv")
    assert response.status_code == 404
    assert response.json()["detail"] == "Backtest metrics not found"
