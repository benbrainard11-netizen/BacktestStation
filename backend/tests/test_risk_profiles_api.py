"""CRUD endpoint tests for /api/risk-profiles."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.db.session import (
    create_all,
    get_session,
    make_engine,
    make_session_factory,
)
from app.main import app


@pytest.fixture
def session_factory(tmp_path: Path) -> sessionmaker:
    engine = make_engine(f"sqlite:///{tmp_path / 'rp.sqlite'}")
    create_all(engine)
    return make_session_factory(engine)


@pytest.fixture
def client(session_factory) -> Generator[TestClient, None, None]:
    def _override():
        s = session_factory()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_session] = _override
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_session, None)


# --- statuses vocabulary --------------------------------------------------


def test_statuses_endpoint_returns_vocabulary(client: TestClient) -> None:
    response = client.get("/api/risk-profiles/statuses")
    assert response.status_code == 200
    body = response.json()
    assert set(body["statuses"]) == {"active", "archived"}


# --- POST -----------------------------------------------------------------


def test_post_creates_profile_with_all_caps(client: TestClient) -> None:
    response = client.post(
        "/api/risk-profiles",
        json={
            "name": "Conservative",
            "max_daily_loss_r": 5.0,
            "max_drawdown_r": 20.0,
            "max_consecutive_losses": 3,
            "max_position_size": 2,
            "allowed_hours": [13, 14, 15],
            "notes": "lunch hour only",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["name"] == "Conservative"
    assert body["status"] == "active"
    assert body["max_daily_loss_r"] == 5.0
    assert body["allowed_hours"] == [13, 14, 15]


def test_post_with_minimal_body_uses_none_for_optional_caps(
    client: TestClient,
) -> None:
    response = client.post("/api/risk-profiles", json={"name": "Bare"})
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["max_daily_loss_r"] is None
    assert body["max_drawdown_r"] is None
    assert body["allowed_hours"] is None


def test_post_duplicate_name_returns_409(client: TestClient) -> None:
    client.post("/api/risk-profiles", json={"name": "Dup"})
    response = client.post("/api/risk-profiles", json={"name": "Dup"})
    assert response.status_code == 409


def test_post_extra_field_returns_422(client: TestClient) -> None:
    response = client.post(
        "/api/risk-profiles",
        json={"name": "Extra", "unknown_field": True},
    )
    assert response.status_code == 422


def test_post_invalid_status_returns_422(client: TestClient) -> None:
    response = client.post(
        "/api/risk-profiles", json={"name": "BadStatus", "status": "spicy"}
    )
    assert response.status_code == 422


def test_post_invalid_hour_returns_422(client: TestClient) -> None:
    response = client.post(
        "/api/risk-profiles",
        json={"name": "BadHours", "allowed_hours": [5, 25]},
    )
    assert response.status_code == 422


# --- GET ------------------------------------------------------------------


def test_get_list_returns_all_profiles(client: TestClient) -> None:
    client.post("/api/risk-profiles", json={"name": "A"})
    client.post("/api/risk-profiles", json={"name": "B"})
    response = client.get("/api/risk-profiles")
    assert response.status_code == 200
    names = {p["name"] for p in response.json()}
    assert names == {"A", "B"}


def test_get_one_returns_profile(client: TestClient) -> None:
    create = client.post(
        "/api/risk-profiles",
        json={"name": "One", "max_daily_loss_r": 4.0},
    )
    pid = create.json()["id"]
    response = client.get(f"/api/risk-profiles/{pid}")
    assert response.status_code == 200
    assert response.json()["name"] == "One"
    assert response.json()["max_daily_loss_r"] == 4.0


def test_get_missing_returns_404(client: TestClient) -> None:
    response = client.get("/api/risk-profiles/99999")
    assert response.status_code == 404


# --- PATCH ----------------------------------------------------------------


def test_patch_applies_only_touched_fields(client: TestClient) -> None:
    create = client.post(
        "/api/risk-profiles",
        json={
            "name": "Origin",
            "max_daily_loss_r": 5.0,
            "max_drawdown_r": 20.0,
            "notes": "original notes",
        },
    )
    pid = create.json()["id"]
    response = client.patch(
        f"/api/risk-profiles/{pid}",
        json={"max_daily_loss_r": 3.0},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    # touched.
    assert body["max_daily_loss_r"] == 3.0
    # not touched -> unchanged.
    assert body["max_drawdown_r"] == 20.0
    assert body["notes"] == "original notes"


def test_patch_unknown_field_returns_422(client: TestClient) -> None:
    create = client.post("/api/risk-profiles", json={"name": "Unk"})
    pid = create.json()["id"]
    response = client.patch(
        f"/api/risk-profiles/{pid}", json={"definitely_not_a_field": 1}
    )
    assert response.status_code == 422


def test_patch_clear_a_cap_via_explicit_null(client: TestClient) -> None:
    """Sending allowed_hours=null clears the cap."""
    create = client.post(
        "/api/risk-profiles",
        json={"name": "ClearMe", "allowed_hours": [10, 11]},
    )
    pid = create.json()["id"]
    response = client.patch(
        f"/api/risk-profiles/{pid}", json={"allowed_hours": None}
    )
    assert response.status_code == 200
    assert response.json()["allowed_hours"] is None


def test_patch_missing_returns_404(client: TestClient) -> None:
    response = client.patch(
        "/api/risk-profiles/99999", json={"max_daily_loss_r": 1.0}
    )
    assert response.status_code == 404


# --- DELETE ---------------------------------------------------------------


def test_delete_returns_204_and_removes(client: TestClient) -> None:
    create = client.post("/api/risk-profiles", json={"name": "Bye"})
    pid = create.json()["id"]
    response = client.delete(f"/api/risk-profiles/{pid}")
    assert response.status_code == 204
    response = client.get(f"/api/risk-profiles/{pid}")
    assert response.status_code == 404


def test_delete_missing_returns_404(client: TestClient) -> None:
    response = client.delete("/api/risk-profiles/99999")
    assert response.status_code == 404


# --- evaluate -------------------------------------------------------------


def test_evaluate_missing_profile_returns_404(client: TestClient) -> None:
    response = client.post("/api/risk-profiles/99999/evaluate?run_id=1")
    assert response.status_code == 404


def test_evaluate_missing_run_returns_404(client: TestClient) -> None:
    create = client.post("/api/risk-profiles", json={"name": "Eval"})
    pid = create.json()["id"]
    response = client.post(f"/api/risk-profiles/{pid}/evaluate?run_id=99999")
    assert response.status_code == 404
