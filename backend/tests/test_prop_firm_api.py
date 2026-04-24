"""Prop-firm simulator endpoint + service tests."""

from collections.abc import Generator
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.db import models
from app.db.session import create_all, get_session, make_engine, make_session_factory
from app.main import app
from app.services import prop_firm


@pytest.fixture
def session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = make_engine(f"sqlite:///{tmp_path / 'prop.sqlite'}")
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


def _seed_run_with_trades(
    factory: sessionmaker[Session],
    r_multiples_per_day: list[list[float]],
) -> int:
    """Create a run with trades across consecutive days. Each inner list is one
    day; each float is a trade's r_multiple."""
    with factory() as session:
        strategy = models.Strategy(name="T", slug="t")
        version = models.StrategyVersion(strategy=strategy, version="v1")
        run = models.BacktestRun(
            strategy_version=version,
            symbol="NQ",
            import_source="test",
            start_ts=datetime(2024, 1, 2),
            end_ts=datetime(2024, 1, 2 + len(r_multiples_per_day)),
        )
        day = 2
        for day_trades in r_multiples_per_day:
            hour = 10
            for r in day_trades:
                run.trades.append(
                    models.Trade(
                        entry_ts=datetime(2024, 1, day, hour, 0),
                        symbol="NQ",
                        side="long",
                        entry_price=21000.0,
                        size=1.0,
                        r_multiple=r,
                    )
                )
                hour += 1
            day += 1
        session.add(strategy)
        session.commit()
        return run.id


def test_presets_endpoint_lists_known_presets(client: TestClient) -> None:
    response = client.get("/api/prop-firm/presets")
    assert response.status_code == 200
    presets = response.json()
    keys = [p["key"] for p in presets]
    assert "topstep_50k" in keys
    assert "apex_50k" in keys


def test_simulate_passes_quickly_with_winning_trades(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    # 3 consecutive days of solid wins → hit +$3000 target at $250/R.
    run_id = _seed_run_with_trades(session_factory, [[3.0, 3.0], [3.0], [3.0]])

    response = client.post(
        f"/api/backtests/{run_id}/prop-firm-sim",
        json={
            "starting_balance": 50_000,
            "profit_target": 3_000,
            "max_drawdown": 2_500,
            "trailing_drawdown": True,
            "daily_loss_limit": None,
            "consistency_pct": None,
            "max_trades_per_day": None,
            "risk_per_trade_dollars": 250,
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["passed"] is True
    assert body["fail_reason"] is None
    assert body["days_to_pass"] is not None
    assert body["days_to_pass"] <= 3
    assert body["final_balance"] > 50_000


def test_simulate_fails_max_drawdown(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    # One catastrophic trade that wipes out DD buffer.
    run_id = _seed_run_with_trades(session_factory, [[-15.0]])

    response = client.post(
        f"/api/backtests/{run_id}/prop-firm-sim",
        json={
            "starting_balance": 50_000,
            "profit_target": 3_000,
            "max_drawdown": 2_500,
            "trailing_drawdown": True,
            "risk_per_trade_dollars": 250,
        },
    )
    body = response.json()
    assert body["passed"] is False
    assert "Max drawdown" in body["fail_reason"]


def test_simulate_fails_daily_loss_limit(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    # Two -2R trades at $250/R = -$1000 day → breaches $1000 daily limit.
    # Three -2R = -$1500.
    run_id = _seed_run_with_trades(session_factory, [[-2.0, -2.0, -2.0]])

    response = client.post(
        f"/api/backtests/{run_id}/prop-firm-sim",
        json={
            "starting_balance": 50_000,
            "profit_target": 3_000,
            "max_drawdown": 2_500,
            "trailing_drawdown": True,
            "daily_loss_limit": 1_000,
            "risk_per_trade_dollars": 250,
        },
    )
    body = response.json()
    assert body["passed"] is False
    assert "Daily loss limit" in body["fail_reason"]


def test_simulate_respects_max_trades_per_day(
    session_factory: sessionmaker[Session],
) -> None:
    # 10 losing trades, but cap = 2 → only 2 per day count, spread across days.
    _ = _seed_run_with_trades(session_factory, [[1.0] * 10])
    with session_factory() as session:
        trades = list(session.scalars(select_trades()))
    config = prop_firm.PropFirmConfig(
        starting_balance=50_000,
        profit_target=3_000,
        max_drawdown=2_500,
        trailing_drawdown=True,
        daily_loss_limit=None,
        consistency_pct=None,
        max_trades_per_day=2,
        risk_per_trade_dollars=250,
    )
    result = prop_firm.simulate(trades, config)
    # Day 1 had 10 trades in the fixture but cap = 2 → only 2 counted.
    day_rows = result.days
    assert day_rows[0].trades == 2


def test_simulate_consistency_rule_blocks_pass(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    # Day 1: massive win. Day 2: small win. Target hits on day 1, but best-day
    # share is 100% → consistency not met → keep going.
    run_id = _seed_run_with_trades(session_factory, [[20.0], [2.0]])

    response = client.post(
        f"/api/backtests/{run_id}/prop-firm-sim",
        json={
            "starting_balance": 50_000,
            "profit_target": 3_000,
            "max_drawdown": 2_500,
            "trailing_drawdown": True,
            "consistency_pct": 0.5,
            "risk_per_trade_dollars": 250,
        },
    )
    body = response.json()
    assert body["consistency_ok"] is False
    # Best day dollar = 20 * 250 = 5000. Total profit = (20+2)*250 = 5500.
    # Best share = 5000/5500 ≈ 0.909, over the 0.5 limit.
    assert body["best_day_share_of_profit"] > 0.5


def test_sim_missing_run_returns_404(client: TestClient) -> None:
    response = client.post(
        "/api/backtests/9999/prop-firm-sim",
        json={
            "starting_balance": 50_000,
            "profit_target": 3_000,
            "max_drawdown": 2_500,
            "trailing_drawdown": True,
            "risk_per_trade_dollars": 250,
        },
    )
    assert response.status_code == 404


# Tiny helper for the one test that uses the service directly.
def select_trades() -> "object":
    from sqlalchemy import select
    from app.db.models import Trade

    return select(Trade).order_by(Trade.entry_ts.asc())
