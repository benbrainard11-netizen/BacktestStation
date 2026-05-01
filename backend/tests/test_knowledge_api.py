"""Knowledge Library API tests."""

from collections.abc import Generator
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from app.db import models
from app.db.session import create_all, get_session, make_engine, make_session_factory
from app.main import app


@pytest.fixture
def session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = make_engine(f"sqlite:///{tmp_path / 'knowledge.sqlite'}")
    create_all(engine)
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM knowledge_cards"))
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
        strategy = models.Strategy(name="Fractal AMD", slug="fractal-amd")
        session.add(strategy)
        session.commit()
        return strategy.id


def test_vocabulary_endpoints(client: TestClient) -> None:
    kinds = client.get("/api/knowledge/kinds")
    assert kinds.status_code == 200
    assert "orderflow_formula" in kinds.json()["kinds"]
    assert "research_playbook" in kinds.json()["kinds"]

    statuses = client.get("/api/knowledge/statuses")
    assert statuses.status_code == 200
    assert "draft" in statuses.json()["statuses"]
    assert "trusted" in statuses.json()["statuses"]
    assert "archived" in statuses.json()["statuses"]


def test_create_then_get_knowledge_card(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    strategy_id = _seed_strategy(session_factory)
    response = client.post(
        "/api/knowledge/cards",
        json={
            "kind": "orderflow_formula",
            "name": " Aggressor Imbalance ",
            "summary": "Measures aggressive buying/selling pressure.",
            "body": "Useful as an entry confirmation, not a standalone signal.",
            "formula": "(ask_volume - bid_volume) / total_volume",
            "inputs": ["ask_volume", "bid_volume", "ask_volume"],
            "use_cases": ["entry confirmation", ""],
            "failure_modes": ["low liquidity", "news spikes"],
            "status": "needs_testing",
            "source": "Ben notes",
            "tags": ["orderflow", " delta ", "orderflow"],
            "strategy_id": strategy_id,
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["id"] > 0
    assert body["name"] == "Aggressor Imbalance"
    assert body["kind"] == "orderflow_formula"
    assert body["status"] == "needs_testing"
    assert body["inputs"] == ["ask_volume", "bid_volume"]
    assert body["use_cases"] == ["entry confirmation"]
    assert body["tags"] == ["orderflow", "delta"]
    assert body["strategy_id"] == strategy_id

    fetched = client.get(f"/api/knowledge/cards/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["formula"] == "(ask_volume - bid_volume) / total_volume"


def test_list_filters_by_kind_status_strategy_tag_and_query(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    strategy_id = _seed_strategy(session_factory)
    client.post(
        "/api/knowledge/cards",
        json={
            "kind": "orderflow_formula",
            "name": "Aggressor Imbalance",
            "summary": "Delta pressure",
            "status": "trusted",
            "tags": ["orderflow", "delta"],
            "strategy_id": strategy_id,
        },
    )
    client.post(
        "/api/knowledge/cards",
        json={
            "kind": "research_playbook",
            "name": "Walk-forward sanity check",
            "summary": "Detects overfit parameter choices",
            "status": "draft",
            "tags": ["process"],
        },
    )
    client.post(
        "/api/knowledge/cards",
        json={
            "kind": "orderflow_formula",
            "name": "Cumulative delta trap",
            "summary": "Divergence idea",
            "status": "rejected",
            "tags": ["orderflow"],
        },
    )

    by_kind = client.get(
        "/api/knowledge/cards", params={"kind": "orderflow_formula"}
    ).json()
    assert {row["name"] for row in by_kind} == {
        "Aggressor Imbalance",
        "Cumulative delta trap",
    }

    trusted = client.get(
        "/api/knowledge/cards", params={"status": "trusted"}
    ).json()
    assert [row["name"] for row in trusted] == ["Aggressor Imbalance"]

    strategy_rows = client.get(
        "/api/knowledge/cards", params={"strategy_id": strategy_id}
    ).json()
    assert [row["name"] for row in strategy_rows] == ["Aggressor Imbalance"]

    tag_rows = client.get(
        "/api/knowledge/cards", params={"tag": "orderflow"}
    ).json()
    assert {row["name"] for row in tag_rows} == {
        "Aggressor Imbalance",
        "Cumulative delta trap",
    }

    search_rows = client.get(
        "/api/knowledge/cards", params={"q": "overfit"}
    ).json()
    assert [row["name"] for row in search_rows] == ["Walk-forward sanity check"]


def test_invalid_kind_or_status_returns_422(client: TestClient) -> None:
    bad_kind = client.post(
        "/api/knowledge/cards",
        json={"kind": "magic", "name": "X"},
    )
    assert bad_kind.status_code == 422

    bad_status = client.post(
        "/api/knowledge/cards",
        json={"kind": "market_concept", "name": "X", "status": "proven"},
    )
    assert bad_status.status_code == 422

    list_bad_kind = client.get("/api/knowledge/cards", params={"kind": "magic"})
    assert list_bad_kind.status_code == 422


def test_create_rejects_missing_strategy(client: TestClient) -> None:
    response = client.post(
        "/api/knowledge/cards",
        json={
            "kind": "market_concept",
            "name": "Liquidity sweep",
            "strategy_id": 9999,
        },
    )
    assert response.status_code == 422
    assert "strategy_id 9999 not found" in response.json()["detail"]


def test_patch_updates_partial_fields_and_can_clear_strategy(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    strategy_id = _seed_strategy(session_factory)
    created = client.post(
        "/api/knowledge/cards",
        json={
            "kind": "market_concept",
            "name": "Liquidity sweep",
            "status": "draft",
            "strategy_id": strategy_id,
        },
    ).json()

    response = client.patch(
        f"/api/knowledge/cards/{created['id']}",
        json={
            "status": "trusted",
            "summary": "Stop run through visible resting liquidity.",
            "strategy_id": None,
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["kind"] == "market_concept"
    assert body["name"] == "Liquidity sweep"
    assert body["status"] == "trusted"
    assert body["summary"] == "Stop run through visible resting liquidity."
    assert body["strategy_id"] is None
    assert body["updated_at"] is not None


def test_delete_card(client: TestClient) -> None:
    created = client.post(
        "/api/knowledge/cards",
        json={"kind": "execution_concept", "name": "Slippage"},
    ).json()
    assert client.delete(f"/api/knowledge/cards/{created['id']}").status_code == 204
    assert client.get(f"/api/knowledge/cards/{created['id']}").status_code == 404


def test_delete_card_clears_research_links(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    strategy_id = _seed_strategy(session_factory)
    card = client.post(
        "/api/knowledge/cards",
        json={"kind": "orderflow_formula", "name": "Imbalance"},
    ).json()
    entry = client.post(
        f"/api/strategies/{strategy_id}/research",
        json={
            "kind": "hypothesis",
            "title": "Imbalance helps",
            "knowledge_card_ids": [card["id"]],
        },
    ).json()

    assert client.delete(f"/api/knowledge/cards/{card['id']}").status_code == 204
    fetched = client.get(
        f"/api/strategies/{strategy_id}/research/{entry['id']}"
    )
    assert fetched.status_code == 200
    assert fetched.json()["knowledge_card_ids"] is None


def test_strategy_delete_nulls_knowledge_card_link(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    strategy_id = _seed_strategy(session_factory)
    created = client.post(
        "/api/knowledge/cards",
        json={
            "kind": "setup_archetype",
            "name": "FVG retrace after SMT",
            "strategy_id": strategy_id,
        },
    ).json()

    delete_response = client.delete(f"/api/strategies/{strategy_id}")
    assert delete_response.status_code == 204, delete_response.text

    fetched = client.get(f"/api/knowledge/cards/{created['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["strategy_id"] is None


# ---------------------------------------------------------------------------
# Evidence links
# ---------------------------------------------------------------------------


def _seed_strategy_with_run_and_entry(
    factory: sessionmaker[Session],
) -> tuple[int, int, int, int]:
    """Return (strategy_id, version_id, run_id, research_entry_id)."""
    with factory() as session:
        strategy = models.Strategy(name="A", slug="a", status="research")
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
        entry = models.ResearchEntry(
            strategy_id=strategy.id,
            kind="hypothesis",
            title="A's hypothesis",
            status="open",
        )
        session.add(entry)
        session.commit()
        return strategy.id, version.id, run.id, entry.id


def test_create_card_with_evidence_links_validates_existence(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    sid, version_id, run_id, entry_id = _seed_strategy_with_run_and_entry(
        session_factory
    )

    bad_run = client.post(
        "/api/knowledge/cards",
        json={
            "kind": "market_concept",
            "name": "X",
            "strategy_id": sid,
            "linked_run_id": 9999,
        },
    )
    assert bad_run.status_code == 422
    assert "9999" in bad_run.json()["detail"]

    bad_version = client.post(
        "/api/knowledge/cards",
        json={
            "kind": "market_concept",
            "name": "X",
            "strategy_id": sid,
            "linked_version_id": 9999,
        },
    )
    assert bad_version.status_code == 422

    bad_entry = client.post(
        "/api/knowledge/cards",
        json={
            "kind": "market_concept",
            "name": "X",
            "strategy_id": sid,
            "linked_research_entry_id": 9999,
        },
    )
    assert bad_entry.status_code == 422

    ok = client.post(
        "/api/knowledge/cards",
        json={
            "kind": "market_concept",
            "name": "Real evidence",
            "strategy_id": sid,
            "linked_run_id": run_id,
            "linked_version_id": version_id,
            "linked_research_entry_id": entry_id,
        },
    )
    assert ok.status_code == 201, ok.text
    body = ok.json()
    assert body["linked_run_id"] == run_id
    assert body["linked_version_id"] == version_id
    assert body["linked_research_entry_id"] == entry_id


def test_create_card_strategy_scoped_run_must_match_strategy(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    sid_a, _, run_a_id, _ = _seed_strategy_with_run_and_entry(session_factory)
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
        sid_b = strategy_b.id

    cross = client.post(
        "/api/knowledge/cards",
        json={
            "kind": "market_concept",
            "name": "wrong scope",
            "strategy_id": sid_b,
            "linked_run_id": run_a_id,
        },
    )
    assert cross.status_code == 422
    assert "different strategy" in cross.json()["detail"].lower()


def test_create_card_strategy_scoped_version_must_match_strategy(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    sid_a, version_a_id, _, _ = _seed_strategy_with_run_and_entry(
        session_factory
    )
    with session_factory() as session:
        strategy_b = models.Strategy(name="B", slug="b")
        session.add(strategy_b)
        session.commit()
        sid_b = strategy_b.id

    cross = client.post(
        "/api/knowledge/cards",
        json={
            "kind": "market_concept",
            "name": "wrong version",
            "strategy_id": sid_b,
            "linked_version_id": version_a_id,
        },
    )
    assert cross.status_code == 422
    assert "different strategy" in cross.json()["detail"].lower()


def test_create_card_strategy_scoped_entry_must_match_strategy(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    sid_a, _, _, entry_a_id = _seed_strategy_with_run_and_entry(session_factory)
    with session_factory() as session:
        strategy_b = models.Strategy(name="B", slug="b")
        session.add(strategy_b)
        session.commit()
        sid_b = strategy_b.id

    cross = client.post(
        "/api/knowledge/cards",
        json={
            "kind": "market_concept",
            "name": "wrong entry",
            "strategy_id": sid_b,
            "linked_research_entry_id": entry_a_id,
        },
    )
    assert cross.status_code == 422
    assert "different strategy" in cross.json()["detail"].lower()


def test_create_global_card_allows_any_strategy_evidence(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """Global cards (strategy_id=None) skip the same-strategy check —
    a cross-strategy concept can cite evidence from any strategy that
    tested it."""
    _, version_id, run_id, entry_id = _seed_strategy_with_run_and_entry(
        session_factory
    )

    ok = client.post(
        "/api/knowledge/cards",
        json={
            "kind": "market_concept",
            "name": "global with evidence",
            "linked_run_id": run_id,
            "linked_version_id": version_id,
            "linked_research_entry_id": entry_id,
        },
    )
    assert ok.status_code == 201, ok.text
    body = ok.json()
    assert body["strategy_id"] is None
    assert body["linked_run_id"] == run_id
    assert body["linked_version_id"] == version_id
    assert body["linked_research_entry_id"] == entry_id


def test_patch_card_can_set_and_clear_evidence_links(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    sid, version_id, run_id, entry_id = _seed_strategy_with_run_and_entry(
        session_factory
    )
    created = client.post(
        "/api/knowledge/cards",
        json={
            "kind": "market_concept",
            "name": "to be wired",
            "strategy_id": sid,
        },
    ).json()

    set_links = client.patch(
        f"/api/knowledge/cards/{created['id']}",
        json={
            "linked_run_id": run_id,
            "linked_version_id": version_id,
            "linked_research_entry_id": entry_id,
        },
    )
    assert set_links.status_code == 200, set_links.text
    body = set_links.json()
    assert body["linked_run_id"] == run_id
    assert body["linked_version_id"] == version_id
    assert body["linked_research_entry_id"] == entry_id

    cleared = client.patch(
        f"/api/knowledge/cards/{created['id']}",
        json={
            "linked_run_id": None,
            "linked_version_id": None,
            "linked_research_entry_id": None,
        },
    )
    assert cleared.status_code == 200
    body = cleared.json()
    assert body["linked_run_id"] is None
    assert body["linked_version_id"] is None
    assert body["linked_research_entry_id"] is None


def test_patch_card_changing_strategy_revalidates_existing_links(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """If a card has links pointing at strategy A and the user moves it
    to strategy B, validation must catch the now-stale links — not
    silently accept them."""
    sid_a, version_a_id, run_a_id, entry_a_id = _seed_strategy_with_run_and_entry(
        session_factory
    )
    with session_factory() as session:
        strategy_b = models.Strategy(name="B", slug="b")
        session.add(strategy_b)
        session.commit()
        sid_b = strategy_b.id

    created = client.post(
        "/api/knowledge/cards",
        json={
            "kind": "market_concept",
            "name": "strategy A evidence",
            "strategy_id": sid_a,
            "linked_run_id": run_a_id,
            "linked_version_id": version_a_id,
            "linked_research_entry_id": entry_a_id,
        },
    ).json()

    moved = client.patch(
        f"/api/knowledge/cards/{created['id']}",
        json={"strategy_id": sid_b},
    )
    assert moved.status_code == 422
    assert "different strategy" in moved.json()["detail"].lower()
