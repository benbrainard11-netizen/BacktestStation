"""Experiment Ledger CRUD tests."""

from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.db import models
from app.db.session import create_all, get_session, make_engine, make_session_factory
from app.main import app


@pytest.fixture
def session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = make_engine(f"sqlite:///{tmp_path / 'experiments.sqlite'}")
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


def _seed(
    factory: sessionmaker[Session], with_runs: int = 0
) -> tuple[int, int, list[int]]:
    """Insert strategy + version + N runs. Return (strategy_id, version_id, run_ids)."""
    with factory() as session:
        strategy = models.Strategy(name="ORB", slug="orb")
        version = models.StrategyVersion(strategy=strategy, version="v1")
        session.add(strategy)
        session.commit()
        run_ids: list[int] = []
        for _ in range(with_runs):
            run = models.BacktestRun(
                strategy_version_id=version.id, symbol="NQ"
            )
            session.add(run)
            session.commit()
            run_ids.append(run.id)
        return strategy.id, version.id, run_ids


def test_decisions_endpoint(client: TestClient) -> None:
    response = client.get("/api/experiments/decisions")
    assert response.status_code == 200
    decisions = response.json()["decisions"]
    assert "pending" in decisions
    assert "promote" in decisions
    assert "reject" in decisions
    assert "forward_test" in decisions


def test_create_experiment_minimal(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    _, version_id, _ = _seed(session_factory)
    response = client.post(
        "/api/experiments",
        json={
            "strategy_version_id": version_id,
            "hypothesis": "Tighter stops reduce avg loss without killing WR",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["strategy_version_id"] == version_id
    assert body["decision"] == "pending"
    assert body["baseline_run_id"] is None
    assert body["variant_run_id"] is None


def test_create_experiment_with_runs(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    _, version_id, run_ids = _seed(session_factory, with_runs=2)
    baseline, variant = run_ids
    response = client.post(
        "/api/experiments",
        json={
            "strategy_version_id": version_id,
            "hypothesis": "Variant beats baseline on avg R",
            "baseline_run_id": baseline,
            "variant_run_id": variant,
            "change_description": "Stop = 0.6R instead of 1R",
            "decision": "pending",
            "notes": "watch for overfit on Q2",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["baseline_run_id"] == baseline
    assert body["variant_run_id"] == variant
    assert "0.6R" in body["change_description"]


def test_create_experiment_rejects_missing_version(client: TestClient) -> None:
    response = client.post(
        "/api/experiments",
        json={"strategy_version_id": 9999, "hypothesis": "x"},
    )
    assert response.status_code == 422
    assert "strategy_version_id 9999" in response.json()["detail"]


def test_create_experiment_rejects_missing_baseline(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    _, version_id, _ = _seed(session_factory)
    response = client.post(
        "/api/experiments",
        json={
            "strategy_version_id": version_id,
            "hypothesis": "x",
            "baseline_run_id": 9999,
        },
    )
    assert response.status_code == 422
    assert "baseline_run_id 9999" in response.json()["detail"]


def test_create_experiment_rejects_invalid_decision(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    _, version_id, _ = _seed(session_factory)
    response = client.post(
        "/api/experiments",
        json={
            "strategy_version_id": version_id,
            "hypothesis": "x",
            "decision": "yolo",
        },
    )
    assert response.status_code == 422


def test_create_experiment_rejects_empty_hypothesis(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    _, version_id, _ = _seed(session_factory)
    response = client.post(
        "/api/experiments",
        json={"strategy_version_id": version_id, "hypothesis": "   "},
    )
    assert response.status_code == 422


def test_list_experiments_filter_by_version(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    _, v1, _ = _seed(session_factory)
    # Add a second version on the same strategy
    with session_factory() as session:
        v2 = models.StrategyVersion(strategy_id=1, version="v2")
        session.add(v2)
        session.commit()
        v2_id = v2.id

    client.post(
        "/api/experiments",
        json={"strategy_version_id": v1, "hypothesis": "v1 a"},
    )
    client.post(
        "/api/experiments",
        json={"strategy_version_id": v1, "hypothesis": "v1 b"},
    )
    client.post(
        "/api/experiments",
        json={"strategy_version_id": v2_id, "hypothesis": "v2 a"},
    )

    rows = client.get(
        "/api/experiments", params={"strategy_version_id": v1}
    ).json()
    assert len(rows) == 2
    assert all(r["strategy_version_id"] == v1 for r in rows)


def test_list_experiments_filter_by_strategy(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    s1, v1, _ = _seed(session_factory)
    # Second strategy with its own version
    with session_factory() as session:
        s2 = models.Strategy(name="Other", slug="other")
        v2 = models.StrategyVersion(strategy=s2, version="v1")
        session.add(s2)
        session.commit()
        v2_id = v2.id

    client.post(
        "/api/experiments",
        json={"strategy_version_id": v1, "hypothesis": "s1"},
    )
    client.post(
        "/api/experiments",
        json={"strategy_version_id": v2_id, "hypothesis": "s2"},
    )

    rows = client.get("/api/experiments", params={"strategy_id": s1}).json()
    assert len(rows) == 1
    assert rows[0]["hypothesis"] == "s1"


def test_list_experiments_filter_by_decision(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    _, v1, _ = _seed(session_factory)
    client.post(
        "/api/experiments",
        json={"strategy_version_id": v1, "hypothesis": "a", "decision": "promote"},
    )
    client.post(
        "/api/experiments",
        json={"strategy_version_id": v1, "hypothesis": "b", "decision": "reject"},
    )
    client.post(
        "/api/experiments",
        json={"strategy_version_id": v1, "hypothesis": "c", "decision": "promote"},
    )

    rows = client.get(
        "/api/experiments", params={"decision": "promote"}
    ).json()
    assert len(rows) == 2
    assert all(r["decision"] == "promote" for r in rows)


def test_list_experiments_filter_by_decision_rejects_invalid(
    client: TestClient,
) -> None:
    response = client.get("/api/experiments", params={"decision": "bogus"})
    assert response.status_code == 422


def test_get_experiment(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    _, v1, _ = _seed(session_factory)
    created = client.post(
        "/api/experiments",
        json={"strategy_version_id": v1, "hypothesis": "x"},
    ).json()
    eid = created["id"]

    response = client.get(f"/api/experiments/{eid}")
    assert response.status_code == 200
    assert response.json()["id"] == eid


def test_patch_experiment_updates_decision_and_sets_updated_at(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    _, v1, _ = _seed(session_factory)
    created = client.post(
        "/api/experiments",
        json={"strategy_version_id": v1, "hypothesis": "test"},
    ).json()
    eid = created["id"]
    assert created["updated_at"] is None

    response = client.patch(
        f"/api/experiments/{eid}",
        json={"decision": "promote", "notes": "win"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "promote"
    assert body["notes"] == "win"
    assert body["updated_at"] is not None


def test_patch_experiment_can_link_runs_after_creation(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    _, v1, run_ids = _seed(session_factory, with_runs=2)
    baseline, variant = run_ids
    created = client.post(
        "/api/experiments",
        json={"strategy_version_id": v1, "hypothesis": "later"},
    ).json()
    eid = created["id"]

    response = client.patch(
        f"/api/experiments/{eid}",
        json={"baseline_run_id": baseline, "variant_run_id": variant},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["baseline_run_id"] == baseline
    assert body["variant_run_id"] == variant


def test_patch_experiment_rejects_missing_run(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    _, v1, _ = _seed(session_factory)
    created = client.post(
        "/api/experiments",
        json={"strategy_version_id": v1, "hypothesis": "x"},
    ).json()
    response = client.patch(
        f"/api/experiments/{created['id']}",
        json={"variant_run_id": 9999},
    )
    assert response.status_code == 422
    assert "variant_run_id 9999" in response.json()["detail"]


def test_patch_experiment_rejects_invalid_decision(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    _, v1, _ = _seed(session_factory)
    created = client.post(
        "/api/experiments",
        json={"strategy_version_id": v1, "hypothesis": "x"},
    ).json()
    response = client.patch(
        f"/api/experiments/{created['id']}", json={"decision": "yolo"}
    )
    assert response.status_code == 422


def test_delete_experiment(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    _, v1, _ = _seed(session_factory)
    created = client.post(
        "/api/experiments",
        json={"strategy_version_id": v1, "hypothesis": "x"},
    ).json()
    eid = created["id"]

    assert client.delete(f"/api/experiments/{eid}").status_code == 204
    assert client.get(f"/api/experiments/{eid}").status_code == 404


def test_missing_experiment_returns_404(client: TestClient) -> None:
    assert client.get("/api/experiments/9999").status_code == 404
    assert client.patch("/api/experiments/9999", json={"notes": "x"}).status_code == 404
    assert client.delete("/api/experiments/9999").status_code == 404


def _seed_second_strategy_with_run(
    factory: sessionmaker[Session],
) -> tuple[int, int]:
    """Insert a second strategy + version + run. Returns (version_id, run_id)."""
    with factory() as session:
        strategy = models.Strategy(name="Other", slug="other")
        version = models.StrategyVersion(strategy=strategy, version="v1")
        session.add(strategy)
        session.commit()
        run = models.BacktestRun(
            strategy_version_id=version.id, symbol="ES"
        )
        session.add(run)
        session.commit()
        return version.id, run.id


def test_create_experiment_rejects_cross_strategy_baseline(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """An experiment on strategy A must not link a run from strategy B."""
    _, version_id, _ = _seed(session_factory, with_runs=0)
    _, other_run_id = _seed_second_strategy_with_run(session_factory)

    response = client.post(
        "/api/experiments",
        json={
            "strategy_version_id": version_id,
            "hypothesis": "cross-strategy check",
            "baseline_run_id": other_run_id,
        },
    )
    assert response.status_code == 422
    assert "different strategy" in response.json()["detail"]


def test_create_experiment_rejects_cross_strategy_variant(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    _, version_id, _ = _seed(session_factory, with_runs=0)
    _, other_run_id = _seed_second_strategy_with_run(session_factory)

    response = client.post(
        "/api/experiments",
        json={
            "strategy_version_id": version_id,
            "hypothesis": "cross-strategy variant",
            "variant_run_id": other_run_id,
        },
    )
    assert response.status_code == 422


def test_patch_experiment_rejects_cross_strategy_run(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    _, version_id, _ = _seed(session_factory, with_runs=0)
    created = client.post(
        "/api/experiments",
        json={"strategy_version_id": version_id, "hypothesis": "x"},
    ).json()
    _, other_run_id = _seed_second_strategy_with_run(session_factory)

    response = client.patch(
        f"/api/experiments/{created['id']}",
        json={"baseline_run_id": other_run_id},
    )
    assert response.status_code == 422
    assert "different strategy" in response.json()["detail"]
