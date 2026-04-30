"""Per-strategy Research workspace CRUD tests."""

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
    engine = make_engine(f"sqlite:///{tmp_path / 'research.sqlite'}")
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


def _seed_strategy(factory: sessionmaker[Session]) -> int:
    with factory() as session:
        strategy = models.Strategy(name="Test", slug="test", status="research")
        session.add(strategy)
        session.commit()
        return strategy.id


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


def test_create_then_get_research_entry(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    sid = _seed_strategy(session_factory)
    response = client.post(
        f"/api/strategies/{sid}/research",
        json={
            "kind": "hypothesis",
            "title": "Long entries on Monday gap-ups outperform",
            "body": "Backed by intuition; needs a backtest.",
            "status": "open",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["kind"] == "hypothesis"
    assert body["title"] == "Long entries on Monday gap-ups outperform"
    assert body["status"] == "open"
    assert body["strategy_id"] == sid
    assert body["linked_run_id"] is None

    entry_id = body["id"]
    get_resp = client.get(f"/api/strategies/{sid}/research/{entry_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["title"] == body["title"]


def test_list_filters_by_kind_and_status(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    sid = _seed_strategy(session_factory)
    client.post(
        f"/api/strategies/{sid}/research",
        json={"kind": "hypothesis", "title": "H1", "status": "open"},
    )
    client.post(
        f"/api/strategies/{sid}/research",
        json={"kind": "hypothesis", "title": "H2", "status": "confirmed"},
    )
    client.post(
        f"/api/strategies/{sid}/research",
        json={"kind": "decision", "title": "D1", "status": "done"},
    )
    client.post(
        f"/api/strategies/{sid}/research",
        json={"kind": "question", "title": "Q1"},
    )

    # No filter — all 4
    all_resp = client.get(f"/api/strategies/{sid}/research")
    assert all_resp.status_code == 200
    assert len(all_resp.json()) == 4

    # Filter by kind
    hyp_resp = client.get(f"/api/strategies/{sid}/research?kind=hypothesis")
    assert {e["title"] for e in hyp_resp.json()} == {"H1", "H2"}

    # Filter by status
    open_resp = client.get(f"/api/strategies/{sid}/research?status=open")
    assert {e["title"] for e in open_resp.json()} == {"H1", "Q1"}

    # Combined filters
    confirmed = client.get(
        f"/api/strategies/{sid}/research?kind=hypothesis&status=confirmed"
    )
    assert [e["title"] for e in confirmed.json()] == ["H2"]


def test_invalid_kind_or_status_returns_422(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    sid = _seed_strategy(session_factory)
    bad_kind = client.get(f"/api/strategies/{sid}/research?kind=garbage")
    assert bad_kind.status_code == 422
    bad_status = client.get(f"/api/strategies/{sid}/research?status=in-progress")
    assert bad_status.status_code == 422


def test_create_with_linked_run_validates_same_strategy(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    sid_a, _, run_a_id = _seed_strategy_with_version_and_run(session_factory)
    # Seed a SECOND strategy + run; trying to link strategy A's entry to
    # strategy B's run must 422.
    with session_factory() as session:
        strategy_b = models.Strategy(name="B", slug="b")
        version_b = models.StrategyVersion(strategy=strategy_b, version="v1")
        run_b = models.BacktestRun(
            strategy_version=version_b,
            symbol="ES",
            import_source="t",
            start_ts=datetime(2026, 1, 2),
            end_ts=datetime(2026, 1, 3),
            source="engine",
        )
        session.add_all([strategy_b, version_b, run_b])
        session.commit()
        run_b_id = run_b.id

    cross = client.post(
        f"/api/strategies/{sid_a}/research",
        json={"kind": "hypothesis", "title": "X", "linked_run_id": run_b_id},
    )
    assert cross.status_code == 422
    assert "different strategy" in cross.json()["detail"].lower()

    # Same-strategy link succeeds.
    ok = client.post(
        f"/api/strategies/{sid_a}/research",
        json={"kind": "hypothesis", "title": "Y", "linked_run_id": run_a_id},
    )
    assert ok.status_code == 201, ok.text
    assert ok.json()["linked_run_id"] == run_a_id


def test_create_with_knowledge_cards_validates_scope(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    sid = _seed_strategy(session_factory)
    with session_factory() as session:
        global_card = models.KnowledgeCard(
            kind="orderflow_formula",
            name="Aggressor Imbalance",
            status="draft",
        )
        own_card = models.KnowledgeCard(
            strategy_id=sid,
            kind="setup_archetype",
            name="FVG after SMT",
            status="trusted",
        )
        other_strategy = models.Strategy(name="Other", slug="other")
        session.add_all([global_card, own_card, other_strategy])
        session.commit()
        other_card = models.KnowledgeCard(
            strategy_id=other_strategy.id,
            kind="market_concept",
            name="Other scoped card",
            status="draft",
        )
        session.add(other_card)
        session.commit()
        global_id = global_card.id
        own_id = own_card.id
        other_id = other_card.id

    ok = client.post(
        f"/api/strategies/{sid}/research",
        json={
            "kind": "hypothesis",
            "title": "Orderflow confirms SMT",
            "knowledge_card_ids": [global_id, own_id, own_id],
        },
    )
    assert ok.status_code == 201, ok.text
    assert ok.json()["knowledge_card_ids"] == [global_id, own_id]

    bad = client.post(
        f"/api/strategies/{sid}/research",
        json={
            "kind": "hypothesis",
            "title": "Wrong scope",
            "knowledge_card_ids": [other_id],
        },
    )
    assert bad.status_code == 422
    assert "wrong scope" in bad.json()["detail"]


def test_patch_updates_fields_and_sets_updated_at(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    sid = _seed_strategy(session_factory)
    create = client.post(
        f"/api/strategies/{sid}/research",
        json={"kind": "hypothesis", "title": "old", "status": "open"},
    )
    entry_id = create.json()["id"]
    assert create.json()["updated_at"] is None

    patch = client.patch(
        f"/api/strategies/{sid}/research/{entry_id}",
        json={"status": "running", "title": "new title"},
    )
    assert patch.status_code == 200
    body = patch.json()
    assert body["status"] == "running"
    assert body["title"] == "new title"
    assert body["updated_at"] is not None


def test_patch_updates_knowledge_cards(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    sid = _seed_strategy(session_factory)
    with session_factory() as session:
        card = models.KnowledgeCard(
            kind="market_concept", name="Liquidity sweep", status="trusted"
        )
        session.add(card)
        session.commit()
        card_id = card.id
    created = client.post(
        f"/api/strategies/{sid}/research",
        json={"kind": "question", "title": "Use sweeps?"},
    )
    eid = created.json()["id"]
    patch = client.patch(
        f"/api/strategies/{sid}/research/{eid}",
        json={"knowledge_card_ids": [card_id]},
    )
    assert patch.status_code == 200, patch.text
    assert patch.json()["knowledge_card_ids"] == [card_id]

    cleared = client.patch(
        f"/api/strategies/{sid}/research/{eid}",
        json={"knowledge_card_ids": None},
    )
    assert cleared.status_code == 200
    assert cleared.json()["knowledge_card_ids"] is None


def test_delete_removes_the_entry(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    sid = _seed_strategy(session_factory)
    create = client.post(
        f"/api/strategies/{sid}/research",
        json={"kind": "question", "title": "Q"},
    )
    entry_id = create.json()["id"]

    del_resp = client.delete(f"/api/strategies/{sid}/research/{entry_id}")
    assert del_resp.status_code == 204

    get_resp = client.get(f"/api/strategies/{sid}/research/{entry_id}")
    assert get_resp.status_code == 404


def test_hypothesis_can_create_experiment(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    sid, version_id, run_id = _seed_strategy_with_version_and_run(session_factory)
    create = client.post(
        f"/api/strategies/{sid}/research",
        json={
            "kind": "hypothesis",
            "title": "Aggressor imbalance improves long entries",
            "body": "Compare baseline against imbalance-filter variant.",
        },
    )
    eid = create.json()["id"]

    response = client.post(
        f"/api/strategies/{sid}/research/{eid}/experiment",
        json={
            "strategy_version_id": version_id,
            "baseline_run_id": run_id,
            "change_description": "Add imbalance filter to entries.",
        },
    )
    assert response.status_code == 201, response.text
    experiment = response.json()
    assert experiment["strategy_version_id"] == version_id
    assert experiment["hypothesis"] == "Aggressor imbalance improves long entries"
    assert experiment["baseline_run_id"] == run_id
    assert experiment["decision"] == "pending"

    updated = client.get(f"/api/strategies/{sid}/research/{eid}").json()
    assert updated["status"] == "running"
    assert updated["linked_version_id"] == version_id
    assert updated["linked_run_id"] == run_id


def test_only_hypothesis_can_create_experiment(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    sid = _seed_strategy(session_factory)
    create = client.post(
        f"/api/strategies/{sid}/research",
        json={"kind": "question", "title": "Should I test imbalance?"},
    )
    response = client.post(
        f"/api/strategies/{sid}/research/{create.json()['id']}/experiment",
        json={},
    )
    assert response.status_code == 422
    assert "only hypothesis" in response.json()["detail"]


def test_unknown_strategy_returns_404(client: TestClient) -> None:
    response = client.get("/api/strategies/9999/research")
    assert response.status_code == 404


def test_create_rejects_invalid_kind_status_pair(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """Codex 5.5 review 2026-04-30: status vocab is restricted by kind.
    decision=confirmed, question=running, hypothesis=done are nonsense
    and must 422."""
    sid = _seed_strategy(session_factory)
    bad = client.post(
        f"/api/strategies/{sid}/research",
        json={"kind": "decision", "title": "X", "status": "confirmed"},
    )
    assert bad.status_code == 422
    bad2 = client.post(
        f"/api/strategies/{sid}/research",
        json={"kind": "question", "title": "X", "status": "running"},
    )
    assert bad2.status_code == 422


def test_patch_rejects_kind_change_that_invalidates_status(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """If kind changes but status doesn't, the resulting pair must be
    valid. confirmed hypothesis → decision should 422 unless status
    also moves to "done"."""
    sid = _seed_strategy(session_factory)
    create = client.post(
        f"/api/strategies/{sid}/research",
        json={"kind": "hypothesis", "title": "H1", "status": "confirmed"},
    )
    eid = create.json()["id"]
    bad = client.patch(
        f"/api/strategies/{sid}/research/{eid}",
        json={"kind": "decision"},
    )
    assert bad.status_code == 422
    # Same patch with status change too is fine.
    ok = client.patch(
        f"/api/strategies/{sid}/research/{eid}",
        json={"kind": "decision", "status": "done"},
    )
    assert ok.status_code == 200


def test_strategy_delete_cascades_research_entries(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """Codex 5.5 review 2026-04-30: with FK enforcement on, deleting a
    strategy with research entries must clean them up first."""
    sid = _seed_strategy(session_factory)
    client.post(
        f"/api/strategies/{sid}/research",
        json={"kind": "hypothesis", "title": "to be cleaned"},
    )
    response = client.delete(f"/api/strategies/{sid}")
    assert response.status_code == 204, response.text


def test_patch_decision_with_linked_run_does_not_422(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """Codex 5.5 re-review (P1): PATCH on a decision entry that
    includes linked_run_id used to materialize a ResearchEntryCreate
    with default status='open', which 422'd because decision+open is
    invalid. Fix: validate link ids without re-running the kind/status
    validator."""
    sid, _, run_id = _seed_strategy_with_version_and_run(session_factory)
    create = client.post(
        f"/api/strategies/{sid}/research",
        json={"kind": "decision", "title": "Bumped FVG threshold", "status": "done"},
    )
    eid = create.json()["id"]
    response = client.patch(
        f"/api/strategies/{sid}/research/{eid}",
        json={"linked_run_id": run_id},
    )
    assert response.status_code == 200, response.text
    assert response.json()["linked_run_id"] == run_id
    assert response.json()["status"] == "done"


def test_run_delete_clears_research_link(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """Deleting a backtest run must NULL the linked_run_id on any
    research entry pointing at it — without this, FK enforcement
    rejects the run delete."""
    sid, _, run_id = _seed_strategy_with_version_and_run(session_factory)
    create = client.post(
        f"/api/strategies/{sid}/research",
        json={
            "kind": "hypothesis",
            "title": "tested by run",
            "linked_run_id": run_id,
        },
    )
    eid = create.json()["id"]

    del_resp = client.delete(f"/api/backtests/{run_id}")
    assert del_resp.status_code == 204, del_resp.text

    # Entry survives but link is null.
    get_resp = client.get(f"/api/strategies/{sid}/research/{eid}")
    assert get_resp.status_code == 200
    assert get_resp.json()["linked_run_id"] is None


def test_cross_strategy_entry_id_is_404(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """Two strategies, an entry created on A, getting it under B's id
    must 404. Prevents URL-tampering from leaking entries across
    strategies."""
    sid_a = _seed_strategy(session_factory)
    with session_factory() as session:
        strategy_b = models.Strategy(name="B", slug="b")
        session.add(strategy_b)
        session.commit()
        sid_b = strategy_b.id

    create = client.post(
        f"/api/strategies/{sid_a}/research",
        json={"kind": "hypothesis", "title": "A's hypothesis"},
    )
    entry_id = create.json()["id"]

    leaked = client.get(f"/api/strategies/{sid_b}/research/{entry_id}")
    assert leaked.status_code == 404
