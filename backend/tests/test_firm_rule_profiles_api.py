"""CRUD + verification semantics for FirmRuleProfile endpoints.

The DB seeds itself from `app.services.prop_firm.PRESETS` on first
boot — every test below starts from that seeded state.
"""

from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import create_all, get_session, make_engine, make_session_factory
from app.main import app
from app.services.prop_firm import PRESETS


@pytest.fixture
def session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = make_engine(f"sqlite:///{tmp_path / 'firm.sqlite'}")
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


# --- Seed behavior ----------------------------------------------------


def test_first_boot_seeds_every_preset(client: TestClient) -> None:
    response = client.get("/api/prop-firm/profiles")
    assert response.status_code == 200
    profiles = response.json()
    profile_ids = {p["profile_id"] for p in profiles}
    # Every PRESETS key should be in the DB after first boot.
    for key in PRESETS:
        assert key in profile_ids, f"seed missed {key}"
    # Every seeded profile carries the seed flag.
    for p in profiles:
        if p["profile_id"] in PRESETS:
            assert p["is_seed"] is True
            assert p["verification_status"] == "unverified"


def test_seed_is_idempotent_when_called_twice(
    session_factory: sessionmaker[Session],
) -> None:
    """create_all() runs the seed; calling it again should not duplicate."""
    from sqlalchemy import text
    from app.db.session import _seed_default_firm_rule_profiles

    engine = session_factory.kw["bind"]
    # Initial seed already happened during create_all() in the fixture.
    with engine.connect() as conn:
        before = conn.execute(
            text("SELECT COUNT(*) FROM firm_rule_profiles")
        ).scalar()

    # Re-seed — should be a no-op for every existing row.
    with engine.begin() as conn:
        _seed_default_firm_rule_profiles(conn)

    with engine.connect() as conn:
        after = conn.execute(
            text("SELECT COUNT(*) FROM firm_rule_profiles")
        ).scalar()

    assert before == after
    assert before == len(PRESETS)


# --- Read endpoints ---------------------------------------------------


def test_get_single_profile_returns_full_shape(client: TestClient) -> None:
    response = client.get("/api/prop-firm/profiles/topstep_50k")
    assert response.status_code == 200
    body = response.json()
    assert body["profile_id"] == "topstep_50k"
    assert body["firm_name"] == "Topstep"
    assert body["profit_target"] == 3000.0
    assert body["source_url"] == "https://www.topstep.com/"


def test_get_unknown_profile_returns_404(client: TestClient) -> None:
    response = client.get("/api/prop-firm/profiles/no_such_firm")
    assert response.status_code == 404


def test_list_excludes_archived_by_default(client: TestClient) -> None:
    archive = client.post("/api/prop-firm/profiles/topstep_50k/archive")
    assert archive.status_code == 200
    response = client.get("/api/prop-firm/profiles")
    keys = {p["profile_id"] for p in response.json()}
    assert "topstep_50k" not in keys


def test_list_with_include_archived_returns_all(client: TestClient) -> None:
    client.post("/api/prop-firm/profiles/topstep_50k/archive")
    response = client.get("/api/prop-firm/profiles?include_archived=true")
    keys = {p["profile_id"] for p in response.json()}
    assert "topstep_50k" in keys


# --- PATCH semantics --------------------------------------------------


def test_patch_updates_specified_fields_only(client: TestClient) -> None:
    response = client.patch(
        "/api/prop-firm/profiles/topstep_50k",
        json={"profit_target": 5000.0, "notes": "edited by ben"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["profit_target"] == 5000.0
    assert body["notes"] == "edited by ben"
    # Untouched field stays at seed value.
    assert body["max_drawdown"] == 2000.0


def test_patch_explicit_verified_stamps_verified_at(
    client: TestClient,
) -> None:
    response = client.patch(
        "/api/prop-firm/profiles/topstep_50k",
        json={"verification_status": "verified", "verified_by": "ben"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["verification_status"] == "verified"
    assert body["verified_at"] is not None
    assert body["verified_by"] == "ben"


def test_patch_rule_field_invalidates_verification(client: TestClient) -> None:
    # First, mark verified.
    client.patch(
        "/api/prop-firm/profiles/topstep_50k",
        json={"verification_status": "verified", "verified_by": "ben"},
    )
    # Now edit a rule field — verification should auto-revert.
    response = client.patch(
        "/api/prop-firm/profiles/topstep_50k",
        json={"profit_target": 4000.0},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["profit_target"] == 4000.0
    assert body["verification_status"] == "unverified"
    assert body["verified_at"] is None
    assert body["verified_by"] is None


def test_patch_notes_alone_keeps_verified(client: TestClient) -> None:
    """Editing notes / source_url / verified_by alone should NOT
    invalidate verification — only rule fields do."""
    client.patch(
        "/api/prop-firm/profiles/topstep_50k",
        json={"verification_status": "verified", "verified_by": "ben"},
    )
    response = client.patch(
        "/api/prop-firm/profiles/topstep_50k",
        json={"notes": "checked the site again on 2026-04-25"},
    )
    body = response.json()
    assert body["verification_status"] == "verified"
    assert body["verified_at"] is not None


def test_patch_unknown_profile_returns_404(client: TestClient) -> None:
    response = client.patch(
        "/api/prop-firm/profiles/no_such_firm",
        json={"profit_target": 1000.0},
    )
    assert response.status_code == 404


def test_patch_with_empty_body_is_a_noop(client: TestClient) -> None:
    response = client.patch(
        "/api/prop-firm/profiles/topstep_50k", json={}
    )
    assert response.status_code == 200
    assert response.json()["profile_id"] == "topstep_50k"


# --- POST (create custom firm) ----------------------------------------


def test_create_custom_profile(client: TestClient) -> None:
    response = client.post(
        "/api/prop-firm/profiles",
        json={
            "profile_id": "my_custom_25k",
            "firm_name": "Ben's Firm",
            "account_name": "Ben's Custom $25K",
            "account_size": 25_000.0,
            "profit_target": 1_500.0,
            "max_drawdown": 1_500.0,
            "daily_loss_limit": 500.0,
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["profile_id"] == "my_custom_25k"
    assert body["is_seed"] is False
    assert body["verification_status"] == "unverified"


def test_create_duplicate_profile_id_is_409(client: TestClient) -> None:
    response = client.post(
        "/api/prop-firm/profiles",
        json={
            "profile_id": "topstep_50k",  # already seeded
            "firm_name": "X",
            "account_name": "X",
            "account_size": 10.0,
            "profit_target": 10.0,
            "max_drawdown": 10.0,
        },
    )
    assert response.status_code == 409


# --- Reset ------------------------------------------------------------


def test_reset_restores_seed_values(client: TestClient) -> None:
    # Edit then reset.
    client.patch(
        "/api/prop-firm/profiles/topstep_50k",
        json={"profit_target": 99_999.0, "notes": "edited"},
    )
    response = client.post("/api/prop-firm/profiles/topstep_50k/reset")
    assert response.status_code == 200
    body = response.json()
    assert body["profit_target"] == 3000.0
    assert "Trading Combine" in (body["notes"] or "")


def test_reset_user_created_returns_404(client: TestClient) -> None:
    client.post(
        "/api/prop-firm/profiles",
        json={
            "profile_id": "user_made",
            "firm_name": "X",
            "account_name": "X",
            "account_size": 10.0,
            "profit_target": 10.0,
            "max_drawdown": 10.0,
        },
    )
    response = client.post("/api/prop-firm/profiles/user_made/reset")
    assert response.status_code == 404


# --- Archive / unarchive ----------------------------------------------


def test_archive_then_unarchive_round_trip(client: TestClient) -> None:
    archive = client.post("/api/prop-firm/profiles/topstep_50k/archive")
    assert archive.json()["is_archived"] is True
    unarchive = client.post("/api/prop-firm/profiles/topstep_50k/unarchive")
    assert unarchive.json()["is_archived"] is False


# --- Backwards-compat presets endpoint --------------------------------


def test_legacy_presets_endpoint_reads_from_db(client: TestClient) -> None:
    """The legacy endpoint shape stays the same, but the data source is
    now the editable DB. Editing a profile via PATCH should change what
    the legacy endpoint returns."""
    # Mutate the seed profile.
    client.patch(
        "/api/prop-firm/profiles/topstep_50k",
        json={"profit_target": 7777.0},
    )
    response = client.get("/api/prop-firm/presets")
    presets = {p["key"]: p for p in response.json()}
    assert presets["topstep_50k"]["profit_target"] == 7777.0


# --- Monte Carlo create_simulation reads from DB ----------------------


def _seed_run_with_trades(
    factory: sessionmaker[Session],
    r_multiples_per_day: list[list[float]],
) -> int:
    """Reused helper — see test_prop_firm_api.py."""
    from datetime import datetime
    from app.db import models

    with factory() as session:
        strategy = models.Strategy(name="T", slug="t-firm")
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


def test_create_simulation_uses_edited_firm_profile(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """Editing topstep_50k's profit target should be reflected in the
    firm_profile snapshot stored with a freshly-created Monte Carlo run."""
    run_id = _seed_run_with_trades(
        session_factory, [[2.0, 2.0], [2.0]]
    )
    # Push a custom profit target via PATCH.
    client.patch(
        "/api/prop-firm/profiles/topstep_50k",
        json={"profit_target": 12_345.0},
    )
    create = client.post(
        "/api/prop-firm/simulations",
        json={
            "name": "uses-edited-profile",
            "selected_backtest_ids": [run_id],
            "firm_profile_id": "topstep_50k",
            "account_size": 50_000,
            "starting_balance": 50_000,
            "phase_mode": "eval_only",
            "sampling_mode": "trade_bootstrap",
            "simulation_count": 50,
            "use_replacement": True,
            "random_seed": 1,
            "risk_mode": "fixed_dollar",
            "risk_per_trade": 100,
            "fees_enabled": True,
            "payout_rules_enabled": True,
        },
    )
    assert create.status_code == 201, create.text
    detail = create.json()
    # The stored firm snapshot should reflect the edited value.
    assert detail["firm"]["profit_target"] == 12_345.0
