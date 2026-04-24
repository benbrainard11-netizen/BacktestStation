"""AI Prompt Generator endpoint tests.

Verifies the modes vocabulary endpoint, the request validation, and
that the bundled prompt actually contains the strategy/version/note/
experiment/run/metrics sections when the underlying data exists.
"""

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
    engine = make_engine(f"sqlite:///{tmp_path / 'prompts.sqlite'}")
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


def _seed_strategy(
    factory: sessionmaker[Session],
    *,
    with_version: bool = True,
    description: str | None = "Trade NQ ORB on the 5-min open",
) -> tuple[int, int | None]:
    with factory() as session:
        strategy = models.Strategy(
            name="ORB Fade",
            slug="orb-fade",
            description=description,
            tags=["intraday", "nq"],
        )
        version_id: int | None = None
        if with_version:
            version = models.StrategyVersion(
                strategy=strategy,
                version="v1",
                entry_md="Enter on opening-range break.",
                exit_md="Stop at low, target 3R.",
                risk_md="Max 1% per trade.",
            )
            session.add(strategy)
            session.commit()
            version_id = version.id
        else:
            session.add(strategy)
            session.commit()
        return strategy.id, version_id


def _seed_run_with_metrics(
    factory: sessionmaker[Session], version_id: int
) -> int:
    with factory() as session:
        run = models.BacktestRun(
            strategy_version_id=version_id,
            symbol="NQ",
            name="2026-Q1 baseline",
        )
        session.add(run)
        session.commit()
        metrics = models.RunMetrics(
            backtest_run_id=run.id,
            net_pnl=12500.0,
            net_r=18.4,
            win_rate=0.42,
            profit_factor=1.8,
            max_drawdown=-6.2,
            avg_r=0.31,
            trade_count=58,
        )
        session.add(metrics)
        session.commit()
        return run.id


def test_modes_endpoint(client: TestClient) -> None:
    response = client.get("/api/prompts/modes")
    assert response.status_code == 200
    modes = response.json()["modes"]
    for expected in [
        "researcher",
        "critic",
        "statistician",
        "risk_manager",
        "engineer",
        "live_monitor",
    ]:
        assert expected in modes


def test_generate_minimal_strategy(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    sid, _ = _seed_strategy(session_factory)
    response = client.post(
        "/api/prompts/generate",
        json={"strategy_id": sid, "mode": "researcher"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["strategy_id"] == sid
    assert body["mode"] == "researcher"
    text = body["prompt_text"]
    # Preamble + strategy + versions sections always present
    assert "# Mode: researcher" in text
    assert "## Strategy" in text
    assert "ORB Fade" in text
    assert "## Versions" in text
    assert "Enter on opening-range break." in text
    # Task section always closes the prompt
    assert "## Your task" in text
    assert body["char_count"] == len(text)


def test_generate_includes_focus_question(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    sid, _ = _seed_strategy(session_factory)
    response = client.post(
        "/api/prompts/generate",
        json={
            "strategy_id": sid,
            "mode": "critic",
            "focus_question": "Why does Friday underperform?",
        },
    )
    assert response.status_code == 200
    text = response.json()["prompt_text"]
    assert "## Focus question" in text
    assert "Why does Friday underperform?" in text
    assert "focus question" in response.json()["bundled_context_summary"]


def test_generate_critic_mode_changes_preamble(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    sid, _ = _seed_strategy(session_factory)
    response = client.post(
        "/api/prompts/generate",
        json={"strategy_id": sid, "mode": "critic"},
    )
    text = response.json()["prompt_text"]
    assert "# Mode: critic" in text
    assert "skeptical" in text.lower()


def test_generate_includes_recent_notes(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    sid, vid = _seed_strategy(session_factory)
    # Add notes attached to the strategy and to the version
    client.post(
        "/api/notes",
        json={
            "body": "Friday gap-down regime broke entry signal",
            "note_type": "observation",
            "strategy_id": sid,
        },
    )
    client.post(
        "/api/notes",
        json={
            "body": "Hypothesis: tighter stop on Mondays",
            "note_type": "hypothesis",
            "strategy_version_id": vid,
        },
    )
    response = client.post(
        "/api/prompts/generate",
        json={"strategy_id": sid, "mode": "researcher"},
    )
    text = response.json()["prompt_text"]
    assert "## Recent notes" in text
    assert "Friday gap-down regime broke entry signal" in text
    assert "Hypothesis: tighter stop on Mondays" in text
    summary = response.json()["bundled_context_summary"]
    assert any("note" in s for s in summary)


def test_generate_includes_recent_experiments(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    sid, vid = _seed_strategy(session_factory)
    client.post(
        "/api/experiments",
        json={
            "strategy_version_id": vid,
            "hypothesis": "Tighter stops reduce avg loss without killing WR",
            "decision": "pending",
        },
    )
    response = client.post(
        "/api/prompts/generate",
        json={"strategy_id": sid, "mode": "researcher"},
    )
    text = response.json()["prompt_text"]
    assert "## Recent experiments" in text
    assert "Tighter stops reduce avg loss" in text


def test_generate_includes_latest_run_and_metrics(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    sid, vid = _seed_strategy(session_factory)
    assert vid is not None
    _seed_run_with_metrics(session_factory, vid)
    response = client.post(
        "/api/prompts/generate",
        json={"strategy_id": sid, "mode": "statistician"},
    )
    text = response.json()["prompt_text"]
    assert "## Latest run" in text
    assert "2026-Q1 baseline" in text
    assert "**Metrics**" in text
    assert "Net R" in text
    assert "18.4" in text
    summary = response.json()["bundled_context_summary"]
    assert "latest run" in summary
    assert "latest metrics" in summary


def test_generate_includes_autopsy_when_enough_trades(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    sid, vid = _seed_strategy(session_factory)
    assert vid is not None
    run_id = _seed_run_with_metrics(session_factory, vid)
    # autopsy requires at least 20 trades — seed 20 with mixed outcomes
    with session_factory() as session:
        for i in range(20):
            t = models.Trade(
                backtest_run_id=run_id,
                entry_ts=datetime(2026, 1, 5 + i, 10, 0),
                symbol="NQ",
                side="long",
                entry_price=21000.0 + i,
                exit_price=21010.0 + i if i % 2 == 0 else 20990.0 + i,
                size=1.0,
                r_multiple=1.5 if i % 2 == 0 else -1.0,
                pnl=15.0 if i % 2 == 0 else -10.0,
                exit_reason="target" if i % 2 == 0 else "stop",
            )
            session.add(t)
        session.commit()

    response = client.post(
        "/api/prompts/generate",
        json={"strategy_id": sid, "mode": "engineer"},
    )
    text = response.json()["prompt_text"]
    assert "## Autopsy" in text
    assert "Verdict" in text or "verdict" in text.lower()
    assert "autopsy" in response.json()["bundled_context_summary"]


def test_generate_skips_autopsy_when_too_few_trades(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    sid, vid = _seed_strategy(session_factory)
    assert vid is not None
    _seed_run_with_metrics(session_factory, vid)
    response = client.post(
        "/api/prompts/generate",
        json={"strategy_id": sid, "mode": "researcher"},
    )
    text = response.json()["prompt_text"]
    assert "## Autopsy" not in text


def test_generate_rejects_invalid_mode(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    sid, _ = _seed_strategy(session_factory)
    response = client.post(
        "/api/prompts/generate",
        json={"strategy_id": sid, "mode": "yolo"},
    )
    assert response.status_code == 422


def test_generate_missing_strategy_returns_404(client: TestClient) -> None:
    response = client.post(
        "/api/prompts/generate",
        json={"strategy_id": 9999, "mode": "researcher"},
    )
    assert response.status_code == 404


def test_generate_handles_strategy_with_no_versions(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    sid, _ = _seed_strategy(session_factory, with_version=False)
    response = client.post(
        "/api/prompts/generate",
        json={"strategy_id": sid, "mode": "researcher"},
    )
    assert response.status_code == 200
    text = response.json()["prompt_text"]
    assert "## Strategy" in text
    # No versions, no notes, no experiments, no runs — but still produces a prompt
    assert "## Versions" not in text
    assert "## Latest run" not in text
    assert "## Your task" in text


def test_generate_skips_archived_versions(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    sid, vid = _seed_strategy(session_factory)
    assert vid is not None
    # Archive the only version
    client.patch(f"/api/strategy-versions/{vid}/archive")

    response = client.post(
        "/api/prompts/generate",
        json={"strategy_id": sid, "mode": "researcher"},
    )
    text = response.json()["prompt_text"]
    # Versions section should not appear since the only version is archived
    assert "## Versions" not in text


def test_generate_truncates_oversized_description(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """A strategy description over FIELD_CAP_CHARS must be soft-capped in the
    prompt with a visible truncation marker, not dumped verbatim."""
    sid, _ = _seed_strategy(
        session_factory, description="X" * 5000
    )
    response = client.post(
        "/api/prompts/generate",
        json={"strategy_id": sid, "mode": "researcher"},
    )
    text = response.json()["prompt_text"]
    assert "truncated" in text
    assert "chars omitted" in text
    # Full 5000-char field should not be present verbatim.
    assert "X" * 5000 not in text
