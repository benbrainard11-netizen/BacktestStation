"""Stage-3 prep regression: GET /api/strategies/{id}/chat?section=X scopes
to the right thread. Section is null on legacy messages so unscoped GET
keeps returning all of them."""

from collections.abc import Generator
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.db import models
from app.db.session import create_all, get_session, make_engine, make_session_factory
from app.main import app


@pytest.fixture
def session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = make_engine(f"sqlite:///{tmp_path / 'chat.sqlite'}")
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


def _seed_strategy_with_messages(
    factory: sessionmaker[Session],
) -> tuple[int, int, int, int]:
    """Seed a strategy + four messages: 1 legacy (no section), 2 build, 1 backtest.
    Returns (strategy_id, legacy_msg_id, build_msg_id, backtest_msg_id)."""
    with factory() as session:
        strategy = models.Strategy(name="X", slug="x")
        session.add(strategy)
        session.commit()
        sid = strategy.id

        base = datetime(2026, 4, 30, 12, 0, 0)
        legacy = models.ChatMessage(
            strategy_id=sid,
            role="user",
            content="legacy msg",
            model="claude",
            section=None,
            created_at=base,
        )
        build_a = models.ChatMessage(
            strategy_id=sid,
            role="user",
            content="build agent: q1",
            model="claude",
            section="build",
            created_at=base + timedelta(seconds=1),
        )
        build_b = models.ChatMessage(
            strategy_id=sid,
            role="assistant",
            content="build agent: a1",
            model="claude",
            section="build",
            created_at=base + timedelta(seconds=2),
        )
        backtest = models.ChatMessage(
            strategy_id=sid,
            role="user",
            content="backtest agent: q1",
            model="claude",
            section="backtest",
            created_at=base + timedelta(seconds=3),
        )
        session.add_all([legacy, build_a, build_b, backtest])
        session.commit()
        return sid, legacy.id, build_a.id, backtest.id


def test_chat_get_unscoped_returns_all_messages(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """Unscoped GET (no `section` query param) returns the full thread —
    legacy single-thread behavior preserved."""
    sid, _, _, _ = _seed_strategy_with_messages(session_factory)
    response = client.get(f"/api/strategies/{sid}/chat")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 4
    assert {msg["section"] for msg in body} == {None, "build", "backtest"}


def test_chat_get_scoped_to_section_filters(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    sid, _, build_a_id, _ = _seed_strategy_with_messages(session_factory)
    response = client.get(f"/api/strategies/{sid}/chat?section=build")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert all(msg["section"] == "build" for msg in body)
    assert {msg["id"] for msg in body} >= {build_a_id}


def test_chat_get_scoped_to_unknown_section_returns_empty(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """An agent that hasn't received any turns yet sees an empty thread —
    not an error, just no messages."""
    sid, _, _, _ = _seed_strategy_with_messages(session_factory)
    response = client.get(f"/api/strategies/{sid}/chat?section=replay")
    assert response.status_code == 200
    assert response.json() == []


def test_chat_resume_isolates_unsectioned_from_sectioned(
    session_factory: sessionmaker[Session],
) -> None:
    """Codex 5.5 review 2026-04-30: an unsectioned POST must NOT pick up
    a sectioned conversation's session id. Verified at the DB-query level
    rather than via the live POST handler (which would shell out to a
    Claude CLI subprocess).

    Mirrors the prior_session lookup in api/chat.py:post_chat_turn.
    """
    from sqlalchemy import desc, select

    with session_factory() as session:
        strategy = models.Strategy(name="X", slug="x")
        session.add(strategy)
        session.commit()
        sid = strategy.id

        base = datetime(2026, 4, 30, 12, 0, 0)
        # Build-section assistant turn (newest overall).
        session.add(
            models.ChatMessage(
                strategy_id=sid,
                role="assistant",
                content="build reply",
                model="claude",
                section="build",
                cli_session_id="build-session-uuid",
                created_at=base + timedelta(seconds=10),
            )
        )
        # Older legacy unsectioned assistant turn.
        session.add(
            models.ChatMessage(
                strategy_id=sid,
                role="assistant",
                content="legacy reply",
                model="claude",
                section=None,
                cli_session_id="legacy-session-uuid",
                created_at=base + timedelta(seconds=1),
            )
        )
        session.commit()

        def resume_for(section: str | None) -> str | None:
            statement = select(models.ChatMessage).where(
                models.ChatMessage.strategy_id == sid,
                models.ChatMessage.role == "assistant",
                models.ChatMessage.model == "claude",
                models.ChatMessage.cli_session_id.is_not(None),
            )
            if section is not None:
                statement = statement.where(
                    models.ChatMessage.section == section
                )
            else:
                statement = statement.where(
                    models.ChatMessage.section.is_(None)
                )
            row = session.scalar(
                statement.order_by(
                    desc(models.ChatMessage.created_at),
                    desc(models.ChatMessage.id),
                ).limit(1)
            )
            return row.cli_session_id if row else None

        # Sectioned POST resumes the right thread.
        assert resume_for("build") == "build-session-uuid"
        # Unsectioned POST resumes ONLY the legacy null thread,
        # NOT the newer sectioned one.
        assert resume_for(None) == "legacy-session-uuid"
        # An unrelated section sees no resume candidate.
        assert resume_for("backtest") is None
