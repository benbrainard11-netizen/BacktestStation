"""Tests for the read-only Memory Health endpoint."""

from collections.abc import Generator
from datetime import datetime, timedelta, timezone
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
    engine = make_engine(f"sqlite:///{tmp_path / 'health.sqlite'}")
    create_all(engine)
    # Seed defaults pollute the population — wipe so each test starts
    # from a known empty knowledge_cards table.
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


def _seed_strategy_with_run_and_entry(
    factory: sessionmaker[Session],
) -> tuple[int, int, int, int]:
    """Return (strategy_id, version_id, run_id, entry_id)."""
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


def _add_card(
    factory: sessionmaker[Session],
    *,
    name: str,
    status: str = "draft",
    kind: str = "market_concept",
    strategy_id: int | None = None,
    linked_run_id: int | None = None,
    linked_version_id: int | None = None,
    linked_research_entry_id: int | None = None,
    created_at: datetime | None = None,
) -> int:
    with factory() as session:
        card = models.KnowledgeCard(
            kind=kind,
            name=name,
            status=status,
            strategy_id=strategy_id,
            linked_run_id=linked_run_id,
            linked_version_id=linked_version_id,
            linked_research_entry_id=linked_research_entry_id,
        )
        session.add(card)
        session.commit()
        if created_at is not None:
            # Override the server-default timestamp for stale-draft
            # tests. Naive UTC matches the rest of the codebase.
            card.created_at = created_at
            session.commit()
        return card.id


def test_health_empty_db_returns_zero_counts_and_no_issues(
    client: TestClient,
) -> None:
    response = client.get("/api/knowledge/health")
    assert response.status_code == 200, response.text
    body = response.json()
    counts = body["counts"]
    assert counts["total_cards"] == 0
    assert counts["trusted_cards"] == 0
    assert counts["needs_testing_cards"] == 0
    assert counts["draft_cards"] == 0
    assert counts["rejected_cards"] == 0
    assert counts["archived_cards"] == 0
    assert counts["trusted_without_evidence"] == 0
    assert counts["needs_testing_without_run"] == 0
    assert counts["stale_drafts"] == 0
    assert counts["promoted_entries_with_multiple_cards"] == 0
    assert body["issues"] == []
    assert "generated_at" in body


def test_health_counts_each_status(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    sid, _, run_id, _ = _seed_strategy_with_run_and_entry(session_factory)
    # Trusted with evidence so it doesn't trip the no-evidence rule.
    _add_card(
        session_factory,
        name="trusted",
        status="trusted",
        strategy_id=sid,
        linked_run_id=run_id,
    )
    # needs_testing with a run so it doesn't trip the no-run rule.
    _add_card(
        session_factory,
        name="needs",
        status="needs_testing",
        strategy_id=sid,
        linked_run_id=run_id,
    )
    _add_card(session_factory, name="draft", status="draft")
    _add_card(session_factory, name="rejected", status="rejected")
    _add_card(session_factory, name="archived", status="archived")

    body = client.get("/api/knowledge/health").json()
    counts = body["counts"]
    assert counts["total_cards"] == 5
    assert counts["trusted_cards"] == 1
    assert counts["needs_testing_cards"] == 1
    assert counts["draft_cards"] == 1
    assert counts["rejected_cards"] == 1
    assert counts["archived_cards"] == 1
    assert body["issues"] == []


def test_health_flags_trusted_without_evidence(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    card_id = _add_card(session_factory, name="naked trust", status="trusted")
    body = client.get("/api/knowledge/health").json()
    assert body["counts"]["trusted_without_evidence"] == 1
    issues = [i for i in body["issues"] if i["code"] == "trusted_without_evidence"]
    assert len(issues) == 1
    issue = issues[0]
    assert issue["severity"] == "warn"
    assert issue["card_id"] == card_id
    assert issue["research_entry_id"] is None


@pytest.mark.parametrize(
    "link_field",
    ["linked_run_id", "linked_version_id", "linked_research_entry_id"],
)
def test_health_trusted_with_any_link_is_ok(
    client: TestClient,
    session_factory: sessionmaker[Session],
    link_field: str,
) -> None:
    """Any one of the three link fields satisfies the evidence
    requirement — trusted cards aren't required to fill all three."""
    sid, version_id, run_id, entry_id = _seed_strategy_with_run_and_entry(
        session_factory
    )
    kwargs = {
        "linked_run_id": run_id,
        "linked_version_id": version_id,
        "linked_research_entry_id": entry_id,
    }
    only_kwargs = {link_field: kwargs[link_field]}
    _add_card(
        session_factory,
        name=f"linked via {link_field}",
        status="trusted",
        strategy_id=sid,
        **only_kwargs,
    )
    body = client.get("/api/knowledge/health").json()
    assert body["counts"]["trusted_without_evidence"] == 0
    assert not any(
        i["code"] == "trusted_without_evidence" for i in body["issues"]
    )


def test_health_flags_needs_testing_without_run(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    card_id = _add_card(
        session_factory, name="awaiting test", status="needs_testing"
    )
    body = client.get("/api/knowledge/health").json()
    assert body["counts"]["needs_testing_without_run"] == 1
    issues = [
        i for i in body["issues"] if i["code"] == "needs_testing_without_run"
    ]
    assert len(issues) == 1
    assert issues[0]["severity"] == "info"
    assert issues[0]["card_id"] == card_id


def test_health_needs_testing_with_run_is_ok(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """A run alone is enough — version and entry links are not required
    to clear the needs_testing rule."""
    sid, _, run_id, _ = _seed_strategy_with_run_and_entry(session_factory)
    _add_card(
        session_factory,
        name="has run",
        status="needs_testing",
        strategy_id=sid,
        linked_run_id=run_id,
    )
    body = client.get("/api/knowledge/health").json()
    assert body["counts"]["needs_testing_without_run"] == 0
    assert not any(
        i["code"] == "needs_testing_without_run" for i in body["issues"]
    )


def test_health_flags_stale_drafts(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    # 31 days old → stale; 5 days old → fresh.
    stale_id = _add_card(
        session_factory,
        name="forgotten",
        status="draft",
        created_at=now - timedelta(days=31),
    )
    _add_card(
        session_factory,
        name="recent",
        status="draft",
        created_at=now - timedelta(days=5),
    )
    body = client.get("/api/knowledge/health").json()
    assert body["counts"]["stale_drafts"] == 1
    issues = [i for i in body["issues"] if i["code"] == "stale_draft"]
    assert len(issues) == 1
    assert issues[0]["severity"] == "info"
    assert issues[0]["card_id"] == stale_id


def test_health_archived_and_rejected_are_not_flagged_for_evidence(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """An archived card with a 'trusted' status pre-archive shape, and a
    rejected card with no links, must not generate evidence issues —
    the user has explicitly de-staged them."""
    _add_card(session_factory, name="dead and gone", status="archived")
    _add_card(session_factory, name="killed", status="rejected")
    body = client.get("/api/knowledge/health").json()
    assert body["counts"]["trusted_without_evidence"] == 0
    assert body["counts"]["needs_testing_without_run"] == 0
    assert body["issues"] == []


def test_health_flags_promoted_entries_with_multiple_cards(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    sid, _, _, entry_id = _seed_strategy_with_run_and_entry(session_factory)
    # Seed two cards and link both ids onto the entry. The cards
    # themselves don't need to be evidence-flagged for this rule.
    card_a = _add_card(
        session_factory, name="A", status="archived", strategy_id=sid
    )
    card_b = _add_card(
        session_factory, name="B", status="archived", strategy_id=sid
    )
    with session_factory() as session:
        entry = session.get(models.ResearchEntry, entry_id)
        assert entry is not None
        entry.knowledge_card_ids = [card_a, card_b]
        session.commit()

    body = client.get("/api/knowledge/health").json()
    assert body["counts"]["promoted_entries_with_multiple_cards"] == 1
    issues = [
        i
        for i in body["issues"]
        if i["code"] == "promoted_entry_with_multiple_cards"
    ]
    assert len(issues) == 1
    assert issues[0]["research_entry_id"] == entry_id
    assert issues[0]["strategy_id"] == sid


def test_health_issues_sorted_deterministically(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """Severity ranks first (warn before info), then by code, then by id.
    The panel needs a stable order so the user's eye can scan."""
    sid, _, _, entry_id = _seed_strategy_with_run_and_entry(session_factory)
    # Mix of issues across severities and codes
    _add_card(
        session_factory, name="needs", status="needs_testing"
    )  # info / needs_testing_without_run
    _add_card(
        session_factory, name="trusted-bare", status="trusted"
    )  # warn / trusted_without_evidence
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    _add_card(
        session_factory,
        name="stale",
        status="draft",
        created_at=now - timedelta(days=60),
    )  # info / stale_draft
    # Trigger the multi-card rule so we have an entry-level info issue
    card_x = _add_card(
        session_factory, name="X", status="archived", strategy_id=sid
    )
    card_y = _add_card(
        session_factory, name="Y", status="archived", strategy_id=sid
    )
    with session_factory() as session:
        entry = session.get(models.ResearchEntry, entry_id)
        assert entry is not None
        entry.knowledge_card_ids = [card_x, card_y]
        session.commit()

    body = client.get("/api/knowledge/health").json()
    issues = body["issues"]
    severities = [i["severity"] for i in issues]
    # All warns must precede all infos.
    first_info = severities.index("info")
    assert all(s == "warn" for s in severities[:first_info])
    assert all(s == "info" for s in severities[first_info:])
    # Within infos, code ordering is alphabetic.
    info_codes = [i["code"] for i in issues if i["severity"] == "info"]
    assert info_codes == sorted(info_codes)
