"""Knowledge Library API tests."""

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
    engine = make_engine(f"sqlite:///{tmp_path / 'knowledge.sqlite'}")
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
