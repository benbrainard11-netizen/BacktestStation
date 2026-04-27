"""Tests for GET /api/backtests/strategies."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db.session import (
    create_all,
    get_session,
    make_engine,
    make_session_factory,
)
from app.main import app


@pytest.fixture
def api_client(tmp_path: Path):
    engine = make_engine(f"sqlite:///{tmp_path / 'strategies.sqlite'}")
    create_all(engine)
    SessionLocal = make_session_factory(engine)

    def _override():
        s = SessionLocal()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_session] = _override
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_session, None)


def test_list_strategies_returns_known_runnable_set(api_client) -> None:
    response = api_client.get("/api/backtests/strategies")
    assert response.status_code == 200, response.text
    body = response.json()
    names = {s["name"] for s in body}
    # Both engine-resolvable strategies must be exposed so the form
    # surfaces them. Drift-detection: when a 3rd lands, this asserts up.
    assert names == {"fractal_amd", "moving_average_crossover"}


def test_list_strategies_carries_default_params_and_schema(api_client) -> None:
    response = api_client.get("/api/backtests/strategies")
    body = response.json()
    fa = next(s for s in body if s["name"] == "fractal_amd")
    # Defaults pulled from FractalAMDConfig — pin the values that
    # carry behavior implications (per-trade dollar cap, target_r).
    assert fa["default_params"]["max_risk_dollars"] == 500.0
    assert fa["default_params"]["target_r"] == 3.0
    # Param schema includes max_risk_dollars with frontend-friendly hints.
    props = fa["param_schema"]["properties"]
    assert "max_risk_dollars" in props
    assert props["max_risk_dollars"]["type"] == "number"
    assert props["max_risk_dollars"]["min"] == 50
    assert props["max_risk_dollars"]["max"] == 5000


def test_moving_average_crossover_definition(api_client) -> None:
    response = api_client.get("/api/backtests/strategies")
    body = response.json()
    mac = next(s for s in body if s["name"] == "moving_average_crossover")
    assert mac["default_params"]["fast_period"] == 5
    assert mac["default_params"]["slow_period"] == 20
    assert "fast_period" in mac["param_schema"]["properties"]
    assert mac["param_schema"]["properties"]["fast_period"]["type"] == "integer"


def test_strategies_route_does_not_collide_with_id_route(api_client) -> None:
    """The literal /strategies path must be registered BEFORE /{backtest_id}
    or FastAPI will try to parse 'strategies' as an integer."""
    response = api_client.get("/api/backtests/strategies")
    assert response.status_code == 200
    # Sanity: a missing-id 404 is also distinct.
    response_404 = api_client.get("/api/backtests/999999")
    assert response_404.status_code == 404
