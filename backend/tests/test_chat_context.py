"""Tests for the per-strategy chat system prompt context."""

from pathlib import Path

from sqlalchemy.orm import Session, sessionmaker

from app.api.chat import _build_system_prompt
from app.db import models
from app.db.session import create_all, make_engine, make_session_factory


def test_chat_system_prompt_includes_research_entries(tmp_path: Path) -> None:
    engine = make_engine(f"sqlite:///{tmp_path / 'chat_context.sqlite'}")
    create_all(engine)
    factory: sessionmaker[Session] = make_session_factory(engine)

    with factory() as session:
        strategy = models.Strategy(name="Fractal AMD", slug="fractal-amd")
        session.add(strategy)
        session.commit()
        session.refresh(strategy)

        session.add(
            models.ResearchEntry(
                strategy_id=strategy.id,
                kind="hypothesis",
                title="Opening imbalance improves long entries",
                body="Test as an entry filter before changing exits.",
                status="open",
                tags=["orderflow", "entry-filter"],
            )
        )
        session.commit()

        system = _build_system_prompt(strategy, session)

    assert "## Research workspace" in system
    assert "hypothesis/open" in system
    assert "Opening imbalance improves long entries" in system
    assert "Test as an entry filter" in system
    assert "tags=orderflow, entry-filter" in system
    assert "saved research memory" in system


def test_chat_system_prompt_includes_knowledge_cards(tmp_path: Path) -> None:
    engine = make_engine(f"sqlite:///{tmp_path / 'chat_knowledge.sqlite'}")
    create_all(engine)
    factory: sessionmaker[Session] = make_session_factory(engine)

    with factory() as session:
        strategy = models.Strategy(name="Fractal AMD", slug="fractal-amd")
        session.add(strategy)
        session.commit()
        session.refresh(strategy)

        session.add(
            models.KnowledgeCard(
                strategy_id=strategy.id,
                kind="orderflow_formula",
                name="Opening Imbalance Formula",
                summary="Tracks aggressive pressure near the open.",
                body="Use as confirmation only.",
                formula="(ask_volume - bid_volume) / total_volume",
                status="needs_testing",
                tags=["orderflow", "open"],
            )
        )
        session.commit()

        system = _build_system_prompt(strategy, session)

    assert "## Knowledge library" in system
    assert "[orderflow_formula/needs_testing] Opening Imbalance Formula" in system
    assert "Formula: (ask_volume - bid_volume) / total_volume" in system
    assert "tags=orderflow, open" in system
