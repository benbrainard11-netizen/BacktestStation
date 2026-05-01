"""AI context preview API tests."""

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
    engine = make_engine(f"sqlite:///{tmp_path / 'ai_context.sqlite'}")
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


def test_ai_context_preview_includes_research_and_knowledge(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    with session_factory() as session:
        strategy = models.Strategy(name="Fractal AMD", slug="fractal-amd")
        session.add(strategy)
        session.commit()
        session.add_all(
            [
                models.ResearchEntry(
                    strategy_id=strategy.id,
                    kind="hypothesis",
                    title="Opening imbalance improves long entries",
                    body="Needs an A/B test against baseline.",
                    status="open",
                    tags=["orderflow"],
                ),
                models.KnowledgeCard(
                    strategy_id=strategy.id,
                    kind="orderflow_formula",
                    name="Opening Imbalance Formula",
                    summary="Tracks aggressive pressure near the open.",
                    formula="(ask_volume - bid_volume) / total_volume",
                    status="needs_testing",
                    tags=["formula"],
                ),
                models.KnowledgeCard(
                    kind="market_concept",
                    name="Archived idea",
                    status="archived",
                ),
            ]
        )
        session.commit()
        strategy_id = strategy.id

    response = client.get(f"/api/strategies/{strategy_id}/ai-context")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["strategy_id"] == strategy_id
    assert body["research_entry_count"] == 1
    assert body["knowledge_card_count"] >= 1
    titles = {item["title"] for item in body["items"]}
    assert "Opening imbalance improves long entries" in titles
    assert "Opening Imbalance Formula" in titles
    assert "Archived idea" not in titles
    assert "## Retrieved memory" in body["prompt_preview"]


def test_ai_context_preview_404s_missing_strategy(client: TestClient) -> None:
    response = client.get("/api/strategies/999999/ai-context")
    assert response.status_code == 404
