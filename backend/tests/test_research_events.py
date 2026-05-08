"""Tests for the Research Event Store.

Covers:
  - make_event_id determinism + collision-resistance + tz normalization
  - record_event insert + idempotence
  - GET /api/research/events filters (feature_name, primary_symbol,
    bar_end range, knowledge_card_id, source_run_id)
  - POST /api/research/events insert + idempotent re-post
  - POST validates knowledge_card_id FK
"""

from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.db import models
from app.db.session import (
    create_all,
    get_session,
    make_engine,
    make_session_factory,
)
from app.main import app
from app.schemas.research_events import ResearchEventCreate
from app.services import research_events as service

UTC = timezone.utc


# ---------- fixtures ----------


@pytest.fixture
def session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = make_engine(f"sqlite:///{tmp_path / 'research_events.sqlite'}")
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


def _seed_knowledge_card(factory: sessionmaker[Session], name: str = "SMT") -> int:
    with factory() as session:
        card = models.KnowledgeCard(
            kind="market_concept",
            name=name,
            summary="Smart Money Technique — divergent highs/lows.",
            status="draft",
        )
        session.add(card)
        session.commit()
        return card.id


def _seed_run(factory: sessionmaker[Session]) -> int:
    with factory() as session:
        strategy = models.Strategy(name="Test", slug="test", status="testing")
        version = models.StrategyVersion(strategy=strategy, version="v1")
        run = models.BacktestRun(
            strategy_version=version,
            symbol="NQ",
            import_source="test-fixture",
        )
        session.add(strategy)
        session.commit()
        return run.id


def _payload(
    *,
    feature_name: str = "smt_at_level",
    primary_symbol: str = "NQ",
    bar_end_utc: datetime | None = None,
    event_type: str = "smt_high",
    **overrides,
) -> dict:
    base = {
        "feature_name": feature_name,
        "event_type": event_type,
        "bar_end_utc": (
            bar_end_utc or datetime(2026, 5, 8, 13, 48, tzinfo=UTC)
        ).isoformat(),
        "primary_symbol": primary_symbol,
        "symbols": ["NQ", "ES", "YM"],
        "timeframe": "1m",
        "side": "high",
        "event_data": {
            "first_break_symbol": "NQ",
            "lagging_symbols": ["ES", "YM"],
            "reference_mode": "prev_30m_high",
        },
    }
    base.update(overrides)
    return base


# ---------- make_event_id ----------


def test_make_event_id_is_deterministic():
    bar_end = datetime(2026, 5, 8, 13, 48, tzinfo=UTC)
    a = service.make_event_id("smt_at_level", "NQ", bar_end, "smt_high")
    b = service.make_event_id("smt_at_level", "NQ", bar_end, "smt_high")
    assert a == b


def test_make_event_id_changes_with_each_input():
    bar_end = datetime(2026, 5, 8, 13, 48, tzinfo=UTC)
    base = service.make_event_id("smt_at_level", "NQ", bar_end, "smt_high")

    other_feature = service.make_event_id("fvg_touch_recent", "NQ", bar_end, "smt_high")
    other_symbol = service.make_event_id("smt_at_level", "ES", bar_end, "smt_high")
    other_bar = service.make_event_id(
        "smt_at_level", "NQ",
        bar_end + timedelta(minutes=1),
        "smt_high",
    )
    other_type = service.make_event_id("smt_at_level", "NQ", bar_end, "smt_low")

    assert len({base, other_feature, other_symbol, other_bar, other_type}) == 5


def test_make_event_id_normalizes_timezone():
    """ET-tagged datetime equal to a UTC instant produces the same id."""
    et_bar = datetime(2026, 5, 8, 9, 48, tzinfo=ZoneInfo("America/New_York"))
    utc_equiv = datetime(2026, 5, 8, 13, 48, tzinfo=UTC)
    assert et_bar.astimezone(UTC) == utc_equiv

    a = service.make_event_id("smt_at_level", "NQ", et_bar, "smt_high")
    b = service.make_event_id("smt_at_level", "NQ", utc_equiv, "smt_high")
    assert a == b


def test_make_event_id_includes_feature_prefix():
    bar_end = datetime(2026, 5, 8, 13, 48, tzinfo=UTC)
    sid = service.make_event_id("fvg_touch_recent", "NQ", bar_end, "fvg_creation")
    assert sid.startswith("fvg_touch_recent-")


# ---------- record_event (service layer) ----------


def test_record_event_inserts_new_row(session_factory: sessionmaker[Session]):
    payload = ResearchEventCreate(**_payload())
    with session_factory() as session:
        row, created = service.record_event(session, payload)
        session.commit()
        assert created is True
        assert row.id > 0
        assert row.event_id.startswith("smt_at_level-")
        assert row.feature_name == "smt_at_level"
        assert row.primary_symbol == "NQ"
        assert row.symbols == ["NQ", "ES", "YM"]
        assert row.event_data["first_break_symbol"] == "NQ"


def test_record_event_is_idempotent(session_factory: sessionmaker[Session]):
    payload = ResearchEventCreate(**_payload())
    with session_factory() as session:
        first, created_first = service.record_event(session, payload)
        session.commit()
        second, created_second = service.record_event(session, payload)
        session.commit()
        assert created_first is True
        assert created_second is False
        assert first.id == second.id
        assert first.event_id == second.event_id


def test_record_event_different_inputs_create_different_rows(
    session_factory: sessionmaker[Session],
):
    p1 = ResearchEventCreate(**_payload(event_type="smt_high"))
    p2 = ResearchEventCreate(**_payload(event_type="smt_low"))
    with session_factory() as session:
        r1, c1 = service.record_event(session, p1)
        r2, c2 = service.record_event(session, p2)
        session.commit()
        assert c1 is True and c2 is True
        assert r1.event_id != r2.event_id


# ---------- GET /api/research/events ----------


def test_get_events_empty(client: TestClient):
    r = client.get("/api/research/events")
    assert r.status_code == 200
    assert r.json() == []


def test_get_events_filters_by_feature_name(
    client: TestClient,
    session_factory: sessionmaker[Session],
):
    with session_factory() as session:
        for ftype, etype in [
            ("smt_at_level", "smt_high"),
            ("smt_at_level", "smt_low"),
            ("fvg_touch_recent", "fvg_creation"),
        ]:
            service.record_event(
                session,
                ResearchEventCreate(
                    **_payload(feature_name=ftype, event_type=etype)
                ),
            )
        session.commit()

    r = client.get("/api/research/events", params={"feature_name": "smt_at_level"})
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 2
    assert all(row["feature_name"] == "smt_at_level" for row in rows)


def test_get_events_filters_by_primary_symbol(
    client: TestClient,
    session_factory: sessionmaker[Session],
):
    with session_factory() as session:
        for sym, etype in [
            ("NQ", "smt_high"),
            ("ES", "smt_high"),
            ("NQ", "smt_low"),
        ]:
            service.record_event(
                session,
                ResearchEventCreate(
                    **_payload(primary_symbol=sym, event_type=etype)
                ),
            )
        session.commit()

    r = client.get("/api/research/events", params={"primary_symbol": "NQ"})
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 2
    assert all(row["primary_symbol"] == "NQ" for row in rows)


def test_get_events_filters_by_bar_end_range(
    client: TestClient,
    session_factory: sessionmaker[Session],
):
    base = datetime(2026, 5, 8, 13, 48, tzinfo=UTC)
    with session_factory() as session:
        for offset_min, etype in [(0, "a"), (5, "b"), (10, "c"), (60, "d")]:
            service.record_event(
                session,
                ResearchEventCreate(
                    **_payload(
                        bar_end_utc=base + timedelta(minutes=offset_min),
                        event_type=etype,
                    )
                ),
            )
        session.commit()

    r = client.get(
        "/api/research/events",
        params={
            "bar_end_from": (base + timedelta(minutes=5)).isoformat(),
            "bar_end_to": (base + timedelta(minutes=60)).isoformat(),
        },
    )
    assert r.status_code == 200
    rows = r.json()
    # bar_end_from inclusive, bar_end_to exclusive → minutes 5 and 10 only
    types = sorted(row["event_type"] for row in rows)
    assert types == ["b", "c"]


def test_get_events_filters_by_knowledge_card_id(
    client: TestClient,
    session_factory: sessionmaker[Session],
):
    smt_id = _seed_knowledge_card(session_factory, "SMT")
    fvg_id = _seed_knowledge_card(session_factory, "FVG")
    with session_factory() as session:
        service.record_event(
            session,
            ResearchEventCreate(
                **_payload(event_type="smt_high", knowledge_card_id=smt_id)
            ),
        )
        service.record_event(
            session,
            ResearchEventCreate(
                **_payload(event_type="fvg_creation", knowledge_card_id=fvg_id)
            ),
        )
        session.commit()

    r = client.get(
        "/api/research/events", params={"knowledge_card_id": smt_id}
    )
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 1
    assert rows[0]["knowledge_card_id"] == smt_id
    assert rows[0]["event_type"] == "smt_high"


def test_get_events_filters_by_source_run_id(
    client: TestClient,
    session_factory: sessionmaker[Session],
):
    run_id = _seed_run(session_factory)
    with session_factory() as session:
        service.record_event(
            session,
            ResearchEventCreate(
                **_payload(event_type="with_run", source_run_id=run_id)
            ),
        )
        service.record_event(
            session,
            ResearchEventCreate(**_payload(event_type="without_run")),
        )
        session.commit()

    r = client.get(
        "/api/research/events", params={"source_run_id": run_id}
    )
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 1
    assert rows[0]["event_type"] == "with_run"
    assert rows[0]["source_run_id"] == run_id


def test_get_events_orders_by_bar_end_descending(
    client: TestClient,
    session_factory: sessionmaker[Session],
):
    base = datetime(2026, 5, 8, 13, 48, tzinfo=UTC)
    with session_factory() as session:
        for offset_min, etype in [(0, "earliest"), (5, "middle"), (10, "latest")]:
            service.record_event(
                session,
                ResearchEventCreate(
                    **_payload(
                        bar_end_utc=base + timedelta(minutes=offset_min),
                        event_type=etype,
                    )
                ),
            )
        session.commit()

    r = client.get("/api/research/events")
    assert r.status_code == 200
    rows = r.json()
    types = [row["event_type"] for row in rows]
    assert types == ["latest", "middle", "earliest"]


# ---------- POST /api/research/events ----------


def test_post_event_creates_new_row(client: TestClient):
    r = client.post("/api/research/events", json=_payload())
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["id"] > 0
    assert body["event_id"].startswith("smt_at_level-")
    assert body["feature_name"] == "smt_at_level"


def test_post_event_is_idempotent(client: TestClient):
    """Reposting the same payload returns the existing row with 200."""
    payload = _payload()
    first = client.post("/api/research/events", json=payload)
    assert first.status_code == 201
    second = client.post("/api/research/events", json=payload)
    assert second.status_code == 200
    assert first.json()["event_id"] == second.json()["event_id"]
    assert first.json()["id"] == second.json()["id"]


def test_post_event_validates_knowledge_card_id(client: TestClient):
    r = client.post(
        "/api/research/events",
        json=_payload(knowledge_card_id=99999),
    )
    assert r.status_code == 422
    assert "knowledge_card_id" in r.json()["detail"]


def test_post_event_rejects_empty_symbols(client: TestClient):
    r = client.post(
        "/api/research/events",
        json=_payload(symbols=[]),
    )
    assert r.status_code == 422


def test_post_event_rejects_unknown_field(client: TestClient):
    """extra='forbid' catches typos at the API boundary."""
    payload = _payload()
    payload["unknown_field"] = "x"
    r = client.post("/api/research/events", json=payload)
    assert r.status_code == 422
