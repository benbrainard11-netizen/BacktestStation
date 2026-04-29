"""Tests for the Monte Carlo prop-firm simulator API."""

from __future__ import annotations

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
    engine = make_engine(f"sqlite:///{tmp_path / 'sim.sqlite'}")
    create_all(engine)
    return make_session_factory(engine)


@pytest.fixture
def client(
    session_factory: sessionmaker[Session],
) -> Generator[TestClient, None, None]:
    def override_get_session() -> Generator[Session, None, None]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _seed_run_with_trades(
    factory: sessionmaker[Session],
    *,
    n_trades: int = 60,
    win_rate: float = 0.5,
    avg_r_win: float = 1.5,
    avg_r_loss: float = -1.0,
) -> int:
    """Seed a strategy + version + backtest_run + N trades. Returns run id."""
    with factory() as session:
        strategy = models.Strategy(name="Fractal AMD", slug="fractal-amd", status="live")
        version = models.StrategyVersion(strategy=strategy, version="trusted_v1")
        run = models.BacktestRun(
            strategy_version=version,
            symbol="NQ.c.0",
            timeframe="1m",
            start_ts=datetime(2026, 4, 1),
            end_ts=datetime(2026, 4, 24),
            import_source="test",
            source="imported",
            status="complete",
        )
        session.add_all([strategy, version, run])
        session.flush()

        # Spread trades across 24 calendar days.
        for i in range(n_trades):
            day = datetime(2026, 4, 1 + (i % 24), 14, 0)
            r = avg_r_win if (i / max(n_trades, 1)) < win_rate else avg_r_loss
            session.add(
                models.Trade(
                    backtest_run_id=run.id,
                    entry_ts=day,
                    exit_ts=day,
                    symbol="NQ.c.0",
                    side="long",
                    entry_price=21000.0,
                    exit_price=21000.0,
                    stop_price=None,
                    target_price=None,
                    size=1.0,
                    pnl=None,
                    r_multiple=r,
                    exit_reason="target" if r > 0 else "stop",
                )
            )
        session.commit()
        return run.id


def _payload(run_id: int, *, simulation_count: int = 50, **overrides) -> dict:
    base = {
        "name": "Test sim",
        "selected_backtest_ids": [run_id],
        "firm_profile_id": "topstep_50k",
        "account_size": 50_000.0,
        "starting_balance": 50_000.0,
        "phase_mode": "eval_only",
        "sampling_mode": "trade_bootstrap",
        "simulation_count": simulation_count,
        "use_replacement": True,
        "random_seed": 42,
        "risk_mode": "fixed_dollar",
        "risk_per_trade": 200.0,
        "fees_enabled": True,
        "payout_rules_enabled": True,
        "copy_trade_accounts": 1,
        "notes": "",
    }
    base.update(overrides)
    return base


def test_create_simulation_returns_full_detail(
    client: TestClient, session_factory: sessionmaker[Session]
):
    run_id = _seed_run_with_trades(session_factory)
    response = client.post(
        "/api/prop-firm/simulations",
        json=_payload(run_id, simulation_count=50),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    # Full SimulationRunDetail shape sanity.
    assert "config" in body
    assert "firm" in body
    assert "aggregated" in body
    assert "selected_paths" in body
    assert "fan_bands" in body
    assert "confidence" in body
    # Aggregated stats have CI fields.
    assert "value" in body["aggregated"]["pass_rate"]
    assert "low" in body["aggregated"]["pass_rate"]
    # Five archetypal paths.
    assert len(body["selected_paths"]) == 5
    assert {p["bucket"] for p in body["selected_paths"]} == {
        "best", "worst", "median", "near_fail", "near_pass"
    }
    # Fan bands are non-empty arrays.
    assert len(body["fan_bands"]["median"]) > 0
    # Confidence has all 7 sub-scores.
    expected_subs = {
        "monte_carlo_stability", "trade_pool_quality", "day_pool_quality",
        "firm_rule_accuracy", "risk_model_accuracy",
        "sampling_method_quality", "backtest_input_quality",
    }
    assert set(body["confidence"]["subscores"].keys()) == expected_subs


def test_simulation_persists_and_appears_in_list(
    client: TestClient, session_factory: sessionmaker[Session]
):
    run_id = _seed_run_with_trades(session_factory)
    create = client.post(
        "/api/prop-firm/simulations",
        json=_payload(run_id, simulation_count=30),
    )
    assert create.status_code == 201
    sim_id = create.json()["config"]["simulation_id"]

    list_resp = client.get("/api/prop-firm/simulations")
    assert list_resp.status_code == 200
    rows = list_resp.json()
    assert len(rows) == 1
    assert rows[0]["simulation_id"] == sim_id
    assert rows[0]["strategy_name"] == "Fractal AMD"

    detail = client.get(f"/api/prop-firm/simulations/{sim_id}")
    assert detail.status_code == 200
    assert detail.json()["config"]["simulation_id"] == sim_id


def _seed_second_run_with_trades(
    factory: sessionmaker[Session],
    *,
    strategy_name: str,
    strategy_slug: str,
    symbol: str = "ES.c.0",
    n_trades: int = 30,
) -> int:
    """Seed a SECOND, distinct strategy + version + run with trades."""
    with factory() as session:
        strategy = models.Strategy(name=strategy_name, slug=strategy_slug)
        version = models.StrategyVersion(strategy=strategy, version="v1")
        run = models.BacktestRun(
            strategy_version=version,
            symbol=symbol,
            timeframe="1m",
            start_ts=datetime(2026, 4, 1),
            end_ts=datetime(2026, 4, 24),
            import_source="test2",
            source="imported",
            status="complete",
        )
        session.add_all([strategy, version, run])
        session.flush()
        for i in range(n_trades):
            day = datetime(2026, 4, 1 + (i % 24), 14, 0)
            session.add(
                models.Trade(
                    backtest_run_id=run.id,
                    entry_ts=day,
                    exit_ts=day,
                    symbol=symbol,
                    side="long",
                    entry_price=5_000.0,
                    exit_price=5_000.0,
                    size=1.0,
                    r_multiple=1.0 if i % 2 == 0 else -1.0,
                    exit_reason="target" if i % 2 == 0 else "stop",
                )
            )
        session.commit()
        return run.id


def test_multi_strategy_pool_carries_per_run_metadata(
    client: TestClient, session_factory: sessionmaker[Session]
):
    """Codex review 2026-04-29 finding #8: when the pool spans multiple
    strategies, each pool_backtests row must carry its OWN strategy/
    version/symbol — not the first run's metadata copy-pasted across
    every row. Top-level strategy_name should label the mix as
    "Mixed pool" rather than misleadingly using the first run's name."""
    run_a = _seed_run_with_trades(session_factory)
    run_b = _seed_second_run_with_trades(
        session_factory,
        strategy_name="Opening Range Breakout",
        strategy_slug="orb",
        symbol="ES.c.0",
    )

    response = client.post(
        "/api/prop-firm/simulations",
        json=_payload(run_a, simulation_count=30) | {
            "selected_backtest_ids": [run_a, run_b],
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()

    # Each pool_backtests row carries its own strategy + symbol.
    pool = body["pool_backtests"]
    assert len(pool) == 2
    by_run = {row["backtest_id"]: row for row in pool}
    assert by_run[run_a]["strategy_name"] == "Fractal AMD"
    assert by_run[run_a]["symbol"] == "NQ.c.0"
    assert by_run[run_b]["strategy_name"] == "Opening Range Breakout"
    assert by_run[run_b]["symbol"] == "ES.c.0"

    # Top-level persisted strategy_name (visible on the list endpoint)
    # is honest about the multi-strategy mix instead of the first run's
    # name.
    rows = client.get("/api/prop-firm/simulations").json()
    assert len(rows) == 1
    assert "Mixed pool" in rows[0]["strategy_name"], (
        f"expected 'Mixed pool' label, got {rows[0]['strategy_name']!r}"
    )


def test_single_strategy_pool_keeps_real_strategy_name(
    client: TestClient, session_factory: sessionmaker[Session]
):
    """Single-strategy pool: persisted strategy_name should be the real
    name, not 'Mixed'. Regression on the Mixed-label edge."""
    run_id = _seed_run_with_trades(session_factory)
    response = client.post(
        "/api/prop-firm/simulations",
        json=_payload(run_id, simulation_count=30),
    )
    assert response.status_code == 201
    rows = client.get("/api/prop-firm/simulations").json()
    assert rows[0]["strategy_name"] == "Fractal AMD"


def test_simulation_with_no_trades_returns_422(
    client: TestClient, session_factory: sessionmaker[Session]
):
    """Empty backtest -> can't bootstrap, explicit 422."""
    run_id = _seed_run_with_trades(session_factory, n_trades=0)
    resp = client.post(
        "/api/prop-firm/simulations",
        json=_payload(run_id, simulation_count=20),
    )
    assert resp.status_code == 422
    assert "no trades" in resp.text.lower()


def test_simulation_with_unknown_backtest_returns_404(
    client: TestClient, session_factory: sessionmaker[Session]
):
    resp = client.post(
        "/api/prop-firm/simulations",
        json=_payload(99999, simulation_count=20),
    )
    assert resp.status_code == 404


def test_simulation_with_unknown_firm_profile_returns_404(
    client: TestClient, session_factory: sessionmaker[Session]
):
    run_id = _seed_run_with_trades(session_factory)
    resp = client.post(
        "/api/prop-firm/simulations",
        json=_payload(run_id, firm_profile_id="not_a_real_firm"),
    )
    assert resp.status_code == 404


def test_simulation_determinism_same_seed_same_results(
    client: TestClient, session_factory: sessionmaker[Session]
):
    run_id = _seed_run_with_trades(session_factory)
    a = client.post(
        "/api/prop-firm/simulations",
        json=_payload(run_id, simulation_count=50, random_seed=42),
    )
    b = client.post(
        "/api/prop-firm/simulations",
        json=_payload(run_id, simulation_count=50, random_seed=42),
    )
    assert a.status_code == 201 and b.status_code == 201
    # Pass rate should be identical for identical seed + config.
    assert (
        a.json()["aggregated"]["pass_rate"]["value"]
        == b.json()["aggregated"]["pass_rate"]["value"]
    )


def test_get_unknown_simulation_returns_404(
    client: TestClient,
):
    resp = client.get("/api/prop-firm/simulations/99999")
    assert resp.status_code == 404
