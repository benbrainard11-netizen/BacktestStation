"""Regression tests for RiskProfile.strategy_params + the 3 seed profiles."""

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
    engine = make_engine(f"sqlite:///{tmp_path / 'risk.sqlite'}")
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
            yield client, SessionLocal
    finally:
        app.dependency_overrides.pop(get_session, None)


def test_create_profile_round_trips_strategy_params(api_client) -> None:
    client, _ = api_client
    body = {
        "name": "param-test",
        "max_daily_loss_r": 4.0,
        "strategy_params": {
            "max_risk_dollars": 300,
            "target_r": 2.5,
        },
    }
    resp = client.post("/api/risk-profiles", json=body)
    assert resp.status_code == 201, resp.text
    body_out = resp.json()
    assert body_out["strategy_params"] == {
        "max_risk_dollars": 300,
        "target_r": 2.5,
    }

    # GET the same profile back; same params come through.
    profile_id = body_out["id"]
    fetched = client.get(f"/api/risk-profiles/{profile_id}").json()
    assert fetched["strategy_params"] == body_out["strategy_params"]


def test_patch_profile_can_set_and_clear_strategy_params(api_client) -> None:
    client, _ = api_client
    create_resp = client.post(
        "/api/risk-profiles",
        json={"name": "patch-test", "strategy_params": {"max_risk_dollars": 500}},
    )
    profile_id = create_resp.json()["id"]

    # Update params.
    patch_resp = client.patch(
        f"/api/risk-profiles/{profile_id}",
        json={"strategy_params": {"max_risk_dollars": 250, "target_r": 3.0}},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["strategy_params"] == {
        "max_risk_dollars": 250,
        "target_r": 3.0,
    }

    # Clear params.
    clear_resp = client.patch(
        f"/api/risk-profiles/{profile_id}",
        json={"strategy_params": None},
    )
    assert clear_resp.status_code == 200
    assert clear_resp.json()["strategy_params"] is None


def test_seed_profiles_present_after_create_all(api_client) -> None:
    """Conservative / Live-mirror / Aggressive must auto-seed."""
    client, _ = api_client
    resp = client.get("/api/risk-profiles")
    assert resp.status_code == 200
    names = {p["name"] for p in resp.json()}
    expected = {"Conservative", "Live-mirror", "Aggressive"}
    assert expected <= names

    # Spot-check Live-mirror's strategy_params reflect the live bot's
    # gates: $300 cap, max 2 trades/day, 3R target.
    live_mirror = next(p for p in resp.json() if p["name"] == "Live-mirror")
    assert live_mirror["strategy_params"] == {
        "max_risk_dollars": 300.0,
        "max_trades_per_day": 2,
        "target_r": 3.0,
    }


def test_seed_is_idempotent(api_client) -> None:
    """Calling create_all again doesn't duplicate the seed rows."""
    from app.db.session import create_all as create_all_fn

    client, SessionLocal = api_client
    # First fetch.
    before = client.get("/api/risk-profiles").json()
    before_names = sorted(p["name"] for p in before)
    # Re-run create_all on the same engine.
    engine = SessionLocal.kw["bind"]
    create_all_fn(engine)
    after = client.get("/api/risk-profiles").json()
    after_names = sorted(p["name"] for p in after)
    assert before_names == after_names
