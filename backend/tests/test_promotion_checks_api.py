"""Strategy Promotion Checklist CRUD + seed-script tests."""

from collections.abc import Generator
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.db import models
from app.db.session import (
    create_all,
    get_session,
    make_engine,
    make_session_factory,
)
from app.main import app
from scripts import import_fractal_promotion_checks as seed


@pytest.fixture
def session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = make_engine(f"sqlite:///{tmp_path / 'promotion.sqlite'}")
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


def _seed_strategy_with_version_and_run(
    factory: sessionmaker[Session],
) -> tuple[int, int, int]:
    with factory() as session:
        strategy = models.Strategy(name="Test", slug="test", status="research")
        version = models.StrategyVersion(strategy=strategy, version="v1")
        run = models.BacktestRun(
            strategy_version=version,
            symbol="NQ",
            import_source="t",
            start_ts=datetime(2026, 1, 2),
            end_ts=datetime(2026, 1, 3),
            source="engine",
        )
        session.add_all([strategy, version, run])
        session.commit()
        return strategy.id, version.id, run.id


def test_statuses_endpoint(client: TestClient) -> None:
    resp = client.get("/api/promotion-checks/statuses")
    assert resp.status_code == 200
    body = resp.json()
    assert body["statuses"] == [
        "draft",
        "pass_paper",
        "research_only",
        "killed",
        "archived",
    ]


def test_create_then_get_minimal(client: TestClient) -> None:
    resp = client.post(
        "/api/promotion-checks",
        json={"candidate_name": "Pre10 v04"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["candidate_name"] == "Pre10 v04"
    assert body["status"] == "draft"
    assert body["strategy_id"] is None
    assert body["fail_reasons"] is None
    assert body["updated_at"] is None

    check_id = body["id"]
    get_resp = client.get(f"/api/promotion-checks/{check_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["candidate_name"] == "Pre10 v04"


def test_create_with_full_payload_round_trips_json(
    client: TestClient,
) -> None:
    payload = {
        "candidate_name": "Full payload",
        "candidate_config_id": "full_v1",
        "status": "pass_paper",
        "source_repo": "FractalAMD",
        "source_dir": r"C:\fake\path",
        "findings_path": r"D:\notes.md",
        "final_verdict": "ship to paper",
        "notes": "long form commentary",
        "fail_reasons": ["a", "b"],
        "pass_reasons": ["c"],
        "metrics_json": {"topstep_pass_pct": 76.47, "n": 17},
        "robustness_json": {"loo_min": 0.0},
        "evidence_paths_json": {"trades_csv": "x.csv"},
        "next_actions": ["paper", "monitor 4 weeks"],
    }
    resp = client.post("/api/promotion-checks", json=payload)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    for key, value in payload.items():
        assert body[key] == value


def test_create_invalid_status_422(client: TestClient) -> None:
    resp = client.post(
        "/api/promotion-checks",
        json={"candidate_name": "x", "status": "promote"},
    )
    assert resp.status_code == 422


def test_create_unknown_strategy_fk_422(client: TestClient) -> None:
    resp = client.post(
        "/api/promotion-checks",
        json={"candidate_name": "x", "strategy_id": 999_999},
    )
    assert resp.status_code == 422
    assert "strategy_id" in resp.text


def test_create_version_must_belong_to_strategy_422(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    sid_a, vid_a, _ = _seed_strategy_with_version_and_run(session_factory)
    # Different strategy entirely
    with session_factory() as session:
        other = models.Strategy(name="Other", slug="other", status="research")
        other_v = models.StrategyVersion(strategy=other, version="v1")
        session.add_all([other, other_v])
        session.commit()
        sid_b = other.id

    resp = client.post(
        "/api/promotion-checks",
        json={
            "candidate_name": "wrong combo",
            "strategy_id": sid_b,
            "strategy_version_id": vid_a,
        },
    )
    assert resp.status_code == 422
    assert "doesn't belong" in resp.text
    assert sid_a != sid_b


def test_create_extra_field_forbidden(client: TestClient) -> None:
    resp = client.post(
        "/api/promotion-checks",
        json={"candidate_name": "x", "bogus": "field"},
    )
    assert resp.status_code == 422


def test_list_filters(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    sid, vid, _run_id = _seed_strategy_with_version_and_run(session_factory)
    client.post(
        "/api/promotion-checks",
        json={
            "candidate_name": "A",
            "candidate_config_id": "cfg_a",
            "status": "pass_paper",
            "strategy_id": sid,
            "strategy_version_id": vid,
        },
    )
    client.post(
        "/api/promotion-checks",
        json={
            "candidate_name": "B",
            "candidate_config_id": "cfg_b",
            "status": "killed",
        },
    )
    client.post(
        "/api/promotion-checks",
        json={"candidate_name": "C", "status": "research_only"},
    )

    all_resp = client.get("/api/promotion-checks")
    assert all_resp.status_code == 200
    assert len(all_resp.json()) == 3

    by_status = client.get("/api/promotion-checks?status=killed")
    assert {row["candidate_name"] for row in by_status.json()} == {"B"}

    by_strategy = client.get(f"/api/promotion-checks?strategy_id={sid}")
    assert {row["candidate_name"] for row in by_strategy.json()} == {"A"}

    by_version = client.get(
        f"/api/promotion-checks?strategy_version_id={vid}"
    )
    assert {row["candidate_name"] for row in by_version.json()} == {"A"}

    by_config = client.get(
        "/api/promotion-checks?candidate_config_id=cfg_b"
    )
    assert {row["candidate_name"] for row in by_config.json()} == {"B"}


def test_list_invalid_status_filter_422(client: TestClient) -> None:
    resp = client.get("/api/promotion-checks?status=promote")
    assert resp.status_code == 422


def test_get_missing_returns_404(client: TestClient) -> None:
    resp = client.get("/api/promotion-checks/9999")
    assert resp.status_code == 404


def test_patch_updates_fields_and_bumps_updated_at(
    client: TestClient,
) -> None:
    create = client.post(
        "/api/promotion-checks",
        json={"candidate_name": "Patch me"},
    ).json()
    check_id = create["id"]
    assert create["updated_at"] is None

    patch = client.patch(
        f"/api/promotion-checks/{check_id}",
        json={
            "status": "pass_paper",
            "final_verdict": "go",
            "fail_reasons": ["one reason"],
        },
    )
    assert patch.status_code == 200, patch.text
    body = patch.json()
    assert body["status"] == "pass_paper"
    assert body["final_verdict"] == "go"
    assert body["fail_reasons"] == ["one reason"]
    assert body["updated_at"] is not None


def test_patch_invalid_status_422(client: TestClient) -> None:
    create = client.post(
        "/api/promotion-checks", json={"candidate_name": "x"}
    ).json()
    resp = client.patch(
        f"/api/promotion-checks/{create['id']}",
        json={"status": "wat"},
    )
    assert resp.status_code == 422


def test_patch_can_clear_optional_fk_to_null(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    sid, _vid, _rid = _seed_strategy_with_version_and_run(session_factory)
    create = client.post(
        "/api/promotion-checks",
        json={"candidate_name": "x", "strategy_id": sid},
    ).json()
    patched = client.patch(
        f"/api/promotion-checks/{create['id']}",
        json={"strategy_id": None},
    )
    assert patched.status_code == 200
    assert patched.json()["strategy_id"] is None


def test_delete_returns_204_then_404(client: TestClient) -> None:
    create = client.post(
        "/api/promotion-checks",
        json={"candidate_name": "kill me"},
    ).json()
    check_id = create["id"]
    delete = client.delete(f"/api/promotion-checks/{check_id}")
    assert delete.status_code == 204
    assert client.get(f"/api/promotion-checks/{check_id}").status_code == 404


def test_seed_script_idempotent(
    session_factory: sessionmaker[Session],
) -> None:
    inserted_1, updated_1 = seed.upsert_rows(session_factory)
    assert inserted_1 == 3
    assert updated_1 == 0

    with session_factory() as session:
        rows = session.query(models.StrategyPromotionCheck).all()
        assert len(rows) == 3
        names = {row.candidate_name for row in rows}
        assert names == {
            "Pre10 VP Continuation + XGB Router v04",
            "Fractal Regime v05 HTF Composite",
            "Midday Continuation v06-v08",
        }

    inserted_2, updated_2 = seed.upsert_rows(session_factory)
    assert inserted_2 == 0
    assert updated_2 == 3

    with session_factory() as session:
        rows = session.query(models.StrategyPromotionCheck).all()
        assert len(rows) == 3


def test_seed_script_picks_up_edits(
    session_factory: sessionmaker[Session],
) -> None:
    seed.upsert_rows(session_factory)
    edited = [dict(row) for row in seed.ROWS]
    edited[0]["final_verdict"] = "edited verdict"
    inserted, updated = seed.upsert_rows(session_factory, rows=edited)
    assert inserted == 0
    assert updated == 3
    with session_factory() as session:
        target = (
            session.query(models.StrategyPromotionCheck)
            .filter_by(
                candidate_config_id=edited[0]["candidate_config_id"]
            )
            .one()
        )
        assert target.final_verdict == "edited verdict"


def test_seed_script_dedups_on_name_when_no_config_id(
    session_factory: sessionmaker[Session],
) -> None:
    rows = [
        {"candidate_name": "Name only", "status": "draft"},
    ]
    inserted_1, updated_1 = seed.upsert_rows(session_factory, rows=rows)
    inserted_2, updated_2 = seed.upsert_rows(session_factory, rows=rows)
    assert (inserted_1, updated_1) == (1, 0)
    assert (inserted_2, updated_2) == (0, 1)
    with session_factory() as session:
        assert session.query(models.StrategyPromotionCheck).count() == 1
