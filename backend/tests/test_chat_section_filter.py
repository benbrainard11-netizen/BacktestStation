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
