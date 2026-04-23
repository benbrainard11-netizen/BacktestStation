from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import create_all, get_session, make_engine, make_session_factory
from app.main import app


@pytest.fixture
def session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = make_engine(f"sqlite:///{tmp_path / 'import.sqlite'}")
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


def test_import_backtest_bundle_then_read_it(client: TestClient) -> None:
    files = {
        "trades_file": (
            "trades.csv",
            "\n".join(
                [
                    "entry_time,exit_time,symbol,side,entry_price,exit_price,"
                    "stop,target,size,pnl,r,exit_reason,tags",
                    "2026-01-02T15:00:00,2026-01-02T15:15:00,NQ,long,"
                    "21000,21025,20990,21025,1,500,2,target,breakout|rth",
                ]
            ),
            "text/csv",
        ),
        "equity_file": (
            "equity.csv",
            "\n".join(
                [
                    "timestamp,equity",
                    "2026-01-02T15:00:00,100000",
                    "2026-01-02T15:15:00,100500",
                ]
            ),
            "text/csv",
        ),
        "metrics_file": (
            "metrics.json",
            '{"net_pnl": 500, "net_r": 2, "win_rate": 1, "trade_count": 1}',
            "application/json",
        ),
        "config_file": (
            "config.json",
            '{"strategy_name": "ORB", "version": "v1", "timeframe": "1m"}',
            "application/json",
        ),
    }

    response = client.post(
        "/api/import/backtest",
        data={"session_label": "RTH", "import_source": "unit-test-bundle"},
        files=files,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["trades_imported"] == 1
    assert body["equity_points_imported"] == 2
    assert body["metrics_imported"] is True
    assert body["config_imported"] is True

    run_id = body["backtest_id"]
    strategies = client.get("/api/strategies").json()
    assert strategies[0]["name"] == "ORB"
    assert strategies[0]["versions"][0]["version"] == "v1"

    backtest = client.get(f"/api/backtests/{run_id}").json()
    assert backtest["symbol"] == "NQ"
    assert backtest["session_label"] == "RTH"
    assert backtest["import_source"] == "unit-test-bundle"

    trades = client.get(f"/api/backtests/{run_id}/trades").json()
    assert trades[0]["tags"] == ["breakout", "rth"]

    equity = client.get(f"/api/backtests/{run_id}/equity").json()
    assert equity[0]["drawdown"] == 0.0

    metrics = client.get(f"/api/backtests/{run_id}/metrics").json()
    assert metrics["net_pnl"] == 500.0
    assert metrics["trade_count"] == 1


def test_import_backtest_validation_error(client: TestClient) -> None:
    response = client.post(
        "/api/import/backtest",
        files={
            "trades_file": (
                "trades.csv",
                "entry_time,symbol,side,entry_price,size\nnot-a-date,NQ,long,1,1",
                "text/csv",
            ),
            "equity_file": (
                "equity.csv",
                "timestamp,equity\n2026-01-02T15:00:00,100000",
                "text/csv",
            ),
        },
    )

    assert response.status_code == 422
    assert "Invalid datetime value" in response.json()["detail"]


def test_import_backtest_rejects_non_object_config(client: TestClient) -> None:
    response = client.post(
        "/api/import/backtest",
        files={
            "trades_file": (
                "trades.csv",
                "entry_time,symbol,side,entry_price,size\n"
                "2026-01-02T15:00:00,NQ,long,21000,1",
                "text/csv",
            ),
            "equity_file": (
                "equity.csv",
                "timestamp,equity\n2026-01-02T15:00:00,100000",
                "text/csv",
            ),
            "config_file": ("config.json", '["not", "an", "object"]', "application/json"),
        },
    )

    assert response.status_code == 422
    assert "config.json must contain a JSON object" in response.json()["detail"]


def test_import_backtest_rejects_ambiguous_entry_column(client: TestClient) -> None:
    response = client.post(
        "/api/import/backtest",
        files={
            "trades_file": (
                "trades.csv",
                "entry,symbol,side,size\n21000,NQ,long,1",
                "text/csv",
            ),
            "equity_file": (
                "equity.csv",
                "timestamp,equity\n2026-01-02T15:00:00,100000",
                "text/csv",
            ),
        },
    )

    assert response.status_code == 422
    assert "missing entry_ts" in response.json()["detail"]
