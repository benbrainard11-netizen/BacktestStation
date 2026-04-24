"""Strategy autopsy report tests."""

from collections.abc import Generator
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.db import models
from app.db.session import create_all, get_session, make_engine, make_session_factory
from app.main import app


@pytest.fixture
def session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = make_engine(f"sqlite:///{tmp_path / 'autopsy.sqlite'}")
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


def _seed_run_with_metrics(
    factory: sessionmaker[Session],
    r_values: list[float],
    pf: float | None = None,
    wr: float | None = None,
    net_r: float | None = None,
    max_dd: float | None = None,
    trade_count: int | None = None,
) -> int:
    with factory() as session:
        strategy = models.Strategy(name="T", slug="t")
        version = models.StrategyVersion(strategy=strategy, version="v1")
        run = models.BacktestRun(
            strategy_version=version,
            symbol="NQ",
            import_source="test",
            start_ts=datetime(2024, 1, 2),
            end_ts=datetime(2024, 1, 5),
        )
        # Spread trades across a few hours/days so best/worst conditions populate.
        base = datetime(2024, 1, 2, 10, 0)
        for i, r in enumerate(r_values):
            # Each trade 1 hour apart — handles 400-trade fixtures cleanly.
            ts = base + timedelta(hours=i)
            run.trades.append(
                models.Trade(
                    entry_ts=ts,
                    symbol="NQ",
                    side="long" if r > 0 else "short",
                    entry_price=21000.0,
                    size=1.0,
                    r_multiple=r,
                )
            )
        run.metrics = models.RunMetrics(
            net_pnl=None,
            net_r=net_r,
            win_rate=wr,
            profit_factor=pf,
            max_drawdown=max_dd,
            avg_r=sum(r_values) / len(r_values) if r_values else None,
            trade_count=trade_count if trade_count is not None else len(r_values),
        )
        session.add(strategy)
        session.commit()
        return run.id


def test_autopsy_high_confidence_on_strong_stats(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    # Strong PF, big sample, shallow DD.
    r_values = [3.0 if i % 2 == 0 else -1.0 for i in range(400)]
    run_id = _seed_run_with_metrics(
        session_factory,
        r_values,
        pf=3.0,
        wr=0.5,
        net_r=400.0,
        max_dd=-8.0,
    )

    body = client.get(f"/api/backtests/{run_id}/autopsy").json()
    assert body["backtest_run_id"] == run_id
    # PF=3 on 400 trades → concentration check triggers "curve fit" warning.
    # Plus PF=3 trips the high-concentration rule too, so expect some overfit flags.
    assert body["edge_confidence"] >= 60
    assert body["go_live_recommendation"] in {
        "small_size",
        "validated",
        "forward_test_only",
    }
    assert body["strengths"]


def test_autopsy_low_confidence_on_bad_stats(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    r_values = [-1.0] * 20  # Tiny losing run.
    run_id = _seed_run_with_metrics(
        session_factory,
        r_values,
        pf=0.3,
        wr=0.1,
        net_r=-20.0,
        max_dd=-20.0,
    )

    body = client.get(f"/api/backtests/{run_id}/autopsy").json()
    assert body["edge_confidence"] < 40
    assert body["go_live_recommendation"] == "not_ready"
    assert body["weaknesses"]
    assert any("sample" in w.lower() or "trades" in w.lower() for w in body["overfitting_warnings"])


def test_autopsy_flags_concentration_when_top_winners_dominate(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    # 20 trades: 1 massive winner, 19 small losers → top 10% (= 2 trades) carry
    # basically all gains.
    r_values = [30.0, 0.5] + [-1.0] * 18
    run_id = _seed_run_with_metrics(
        session_factory,
        r_values,
        pf=1.4,
        wr=0.1,
        net_r=12.5,
        max_dd=-5.0,
    )

    body = client.get(f"/api/backtests/{run_id}/autopsy").json()
    assert any("Top 10%" in w for w in body["overfitting_warnings"])


def test_autopsy_missing_run_returns_404(client: TestClient) -> None:
    response = client.get("/api/backtests/9999/autopsy")
    assert response.status_code == 404


def test_autopsy_has_best_and_worst_conditions(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    r_values = [3.0] * 5 + [-1.0] * 5 + [3.0] * 5
    run_id = _seed_run_with_metrics(
        session_factory,
        r_values,
        pf=2.0,
        wr=0.5,
        net_r=20.0,
        max_dd=-6.0,
    )
    body = client.get(f"/api/backtests/{run_id}/autopsy").json()
    assert isinstance(body["best_conditions"], list)
    assert isinstance(body["worst_conditions"], list)
    assert "suggested_next_test" in body
    assert len(body["suggested_next_test"]) > 0
