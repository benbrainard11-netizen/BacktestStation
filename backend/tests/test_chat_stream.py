"""POST /api/strategies/{id}/chat-stream — NDJSON streaming endpoint tests.

Mocks run_claude_turn_streaming() so the tests don't actually invoke the
Claude CLI subprocess. Asserts:
  • each yielded StreamEvent renders as one NDJSON line
  • user message persists before the stream starts
  • assistant message persists on a successful "done" event
  • error event from the stream short-circuits assistant persistence
  • compose mode passes a read-only allowed_tools list
  • author mode passes add_dirs scoped to features + tests
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.db import models
from app.db.session import create_all, get_session, make_engine, make_session_factory
from app.main import app
from app.services.cli_chat import StreamEvent


@pytest.fixture
def session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = make_engine(f"sqlite:///{tmp_path / 'chat_stream.sqlite'}")
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
    with TestClient(app) as tc:
        yield tc
    app.dependency_overrides.clear()


def _seed_strategy(factory: sessionmaker[Session]) -> int:
    with factory() as session:
        strategy = models.Strategy(name="StreamTest", slug="stream-test")
        session.add(strategy)
        session.commit()
        return strategy.id


def _capture_invocation_args() -> dict:
    """Module-level dict the patched fn writes its kwargs into for assert."""
    return {}


def _make_streaming_mock(
    events: list[StreamEvent],
    captured_args: dict,
):
    async def mock_streaming(
        prompt: str,
        *,
        system: str,
        prior_session_id: str | None = None,
        cwd: str | None = None,
        add_dirs: list[str] | None = None,
        allowed_tools: list[str] | None = None,
    ) -> AsyncIterator[StreamEvent]:
        captured_args["prompt"] = prompt
        captured_args["system"] = system
        captured_args["prior_session_id"] = prior_session_id
        captured_args["cwd"] = cwd
        captured_args["add_dirs"] = add_dirs
        captured_args["allowed_tools"] = allowed_tools
        for evt in events:
            yield evt

    return mock_streaming


def test_stream_emits_ndjson_and_persists_assistant(
    client: TestClient,
    session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sid = _seed_strategy(session_factory)
    captured: dict = {}
    canned = [
        StreamEvent(type="text", payload={"delta": "Hello, "}),
        StreamEvent(type="text", payload={"delta": "world."}),
        StreamEvent(
            type="tool_use",
            payload={"name": "Read", "input": {"file_path": "/x"}},
        ),
        StreamEvent(
            type="done",
            payload={
                "text": "Hello, world.",
                "session_id": "session-abc-123",
                "cost_usd": 0.0042,
            },
        ),
    ]
    monkeypatch.setattr(
        "app.api.chat.run_claude_turn_streaming",
        _make_streaming_mock(canned, captured),
    )

    with client.stream(
        "POST",
        f"/api/strategies/{sid}/chat-stream",
        json={
            "prompt": "say hi",
            "model": "claude",
            "section": "build",
            "mode": "compose",
        },
    ) as response:
        assert response.status_code == 200
        assert "application/x-ndjson" in response.headers.get("content-type", "")
        lines = [
            json.loads(line)
            for line in response.iter_lines()
            if line.strip()
        ]

    assert len(lines) == 4
    assert lines[0] == {"type": "text", "payload": {"delta": "Hello, "}}
    assert lines[1] == {"type": "text", "payload": {"delta": "world."}}
    assert lines[2]["type"] == "tool_use"
    assert lines[3]["type"] == "done"
    assert lines[3]["payload"]["session_id"] == "session-abc-123"

    # Compose mode passes read-only tool whitelist; no add_dirs.
    assert captured["allowed_tools"] == ["Read", "Glob", "Grep"]
    assert captured["add_dirs"] is None
    assert captured["cwd"] is not None

    # User msg persisted before stream; assistant persisted on done.
    with session_factory() as s:
        msgs = list(
            s.query(models.ChatMessage)
            .filter_by(strategy_id=sid)
            .order_by(models.ChatMessage.id.asc())
            .all()
        )
    assert len(msgs) == 2
    assert msgs[0].role == "user"
    assert msgs[0].content == "say hi"
    assert msgs[0].section == "build"
    assert msgs[1].role == "assistant"
    assert msgs[1].content == "Hello, world."
    assert msgs[1].cli_session_id == "session-abc-123"
    assert msgs[1].cost_usd == pytest.approx(0.0042)


def test_stream_error_event_keeps_user_skips_assistant(
    client: TestClient,
    session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sid = _seed_strategy(session_factory)
    captured: dict = {}
    canned = [
        StreamEvent(type="text", payload={"delta": "starting…"}),
        StreamEvent(type="error", payload={"message": "claude blew up"}),
    ]
    monkeypatch.setattr(
        "app.api.chat.run_claude_turn_streaming",
        _make_streaming_mock(canned, captured),
    )

    with client.stream(
        "POST",
        f"/api/strategies/{sid}/chat-stream",
        json={"prompt": "explode pls", "model": "claude", "mode": "compose"},
    ) as response:
        assert response.status_code == 200
        lines = [
            json.loads(line)
            for line in response.iter_lines()
            if line.strip()
        ]

    assert lines[-1]["type"] == "error"

    with session_factory() as s:
        msgs = list(
            s.query(models.ChatMessage).filter_by(strategy_id=sid).all()
        )
    # User msg persisted (even though stream errored). Assistant did not.
    assert [m.role for m in msgs] == ["user"]


def test_author_mode_passes_features_and_tests_dirs(
    client: TestClient,
    session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sid = _seed_strategy(session_factory)
    captured: dict = {}
    monkeypatch.setattr(
        "app.api.chat.run_claude_turn_streaming",
        _make_streaming_mock(
            [
                StreamEvent(
                    type="done",
                    payload={"text": "ok", "session_id": "x", "cost_usd": 0.01},
                )
            ],
            captured,
        ),
    )

    with client.stream(
        "POST",
        f"/api/strategies/{sid}/chat-stream",
        json={
            "prompt": "make a feature",
            "model": "claude",
            "mode": "author",
        },
    ) as response:
        assert response.status_code == 200
        list(response.iter_lines())  # drain

    # Author mode: no tool whitelist (default toolset including Write/Bash),
    # add_dirs scoped to features + tests.
    assert captured["allowed_tools"] is None
    assert captured["add_dirs"] is not None
    assert len(captured["add_dirs"]) == 2
    assert any("features" in d for d in captured["add_dirs"])
    assert any("tests" in d for d in captured["add_dirs"])


def test_stream_invalid_strategy_returns_404(client: TestClient) -> None:
    response = client.post(
        "/api/strategies/99999/chat-stream",
        json={"prompt": "hello", "model": "claude"},
    )
    assert response.status_code == 404
