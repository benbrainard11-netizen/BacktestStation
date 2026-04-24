"""End-to-end import check against the real Fractal AMD sample bundle.

Verifies the bundle at `samples/fractal_trusted_multiyear/` imports cleanly
through the public POST /api/import/backtest endpoint and that the imported
run is readable through the read endpoints.
"""

from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.core.paths import REPO_ROOT
from app.db.session import create_all, get_session, make_engine, make_session_factory
from app.main import app

SAMPLE_DIR = REPO_ROOT / "samples" / "fractal_trusted_multiyear"
EXPECTED_TRADES = 586
EXPECTED_EQUITY_POINTS = 586


@pytest.fixture
def session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = make_engine(f"sqlite:///{tmp_path / 'fractal_sample.sqlite'}")
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


def test_fractal_trusted_multiyear_sample_imports(client: TestClient) -> None:
    trades_bytes = (SAMPLE_DIR / "trades.csv").read_bytes()
    equity_bytes = (SAMPLE_DIR / "equity.csv").read_bytes()
    metrics_bytes = (SAMPLE_DIR / "metrics.json").read_bytes()
    config_bytes = (SAMPLE_DIR / "config.json").read_bytes()

    response = client.post(
        "/api/import/backtest",
        files={
            "trades_file": ("trades.csv", trades_bytes, "text/csv"),
            "equity_file": ("equity.csv", equity_bytes, "text/csv"),
            "metrics_file": ("metrics.json", metrics_bytes, "application/json"),
            "config_file": ("config.json", config_bytes, "application/json"),
        },
        data={"import_source": "samples/fractal_trusted_multiyear"},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["trades_imported"] == EXPECTED_TRADES
    assert body["equity_points_imported"] == EXPECTED_EQUITY_POINTS
    assert body["metrics_imported"] is True
    assert body["config_imported"] is True

    run_id = body["backtest_id"]

    strategies = client.get("/api/strategies").json()
    assert any(s["slug"] == "fractal-amd" for s in strategies)

    run = client.get(f"/api/backtests/{run_id}").json()
    assert run["symbol"] == "NQ"
    assert run["session_label"] == "RTH"
    assert run["status"] == "imported"

    trades = client.get(f"/api/backtests/{run_id}/trades").json()
    assert len(trades) == EXPECTED_TRADES
    assert {t["side"] for t in trades} <= {"long", "short"}

    equity = client.get(f"/api/backtests/{run_id}/equity").json()
    assert len(equity) == EXPECTED_EQUITY_POINTS
    assert all(point["drawdown"] is not None for point in equity)

    metrics = client.get(f"/api/backtests/{run_id}/metrics").json()
    assert metrics["trade_count"] == EXPECTED_TRADES
    assert metrics["net_r"] is not None
    assert metrics["win_rate"] is not None
