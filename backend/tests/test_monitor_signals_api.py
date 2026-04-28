"""Tests for GET /api/monitor/signals — backs the live session journal."""

from collections.abc import Generator
from datetime import datetime, timedelta
from pathlib import Path

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


@pytest.fixture
def session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = make_engine(f"sqlite:///{tmp_path / 'monitor.sqlite'}")
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


def _seed_strategy_with_signals(
    factory: sessionmaker[Session],
    name: str,
    signals: list[tuple[datetime, str, float, str | None]],
) -> tuple[int, int]:
    """Returns (strategy_id, strategy_version_id)."""
    with factory() as session:
        strategy = models.Strategy(name=name, slug=name.lower())
        version = models.StrategyVersion(strategy=strategy, version="v1")
        session.add(strategy)
        session.flush()
        for ts, side, price, reason in signals:
            session.add(
                models.LiveSignal(
                    strategy_version_id=version.id,
                    ts=ts,
                    side=side,
                    price=price,
                    reason=reason,
                    executed=True,
                )
            )
        session.commit()
        return strategy.id, version.id


def test_no_signals_returns_empty_list(client: TestClient) -> None:
    response = client.get("/api/monitor/signals")
    assert response.status_code == 200
    assert response.json() == []


def test_returns_signals_newest_first(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    base = datetime(2026, 4, 27, 10, 0)
    _seed_strategy_with_signals(
        session_factory,
        "Fractal",
        [
            (base, "long", 21000.0, "first"),
            (base + timedelta(minutes=5), "short", 21010.0, "second"),
            (base + timedelta(minutes=10), "long", 21015.0, "third"),
        ],
    )
    response = client.get("/api/monitor/signals")
    body = response.json()
    assert [s["reason"] for s in body] == ["third", "second", "first"]


def test_filter_by_strategy_id(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    base = datetime(2026, 4, 27, 10, 0)
    fractal_id, _ = _seed_strategy_with_signals(
        session_factory,
        "Fractal",
        [(base, "long", 21000.0, "fractal-sig")],
    )
    _seed_strategy_with_signals(
        session_factory,
        "Other",
        [(base + timedelta(minutes=1), "short", 21000.0, "other-sig")],
    )
    response = client.get(f"/api/monitor/signals?strategy_id={fractal_id}")
    body = response.json()
    assert len(body) == 1
    assert body[0]["reason"] == "fractal-sig"


def test_filter_by_strategy_id_unknown_returns_empty(
    client: TestClient,
) -> None:
    response = client.get("/api/monitor/signals?strategy_id=9999")
    assert response.json() == []


def test_filter_by_since(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    base = datetime(2026, 4, 27, 10, 0)
    _seed_strategy_with_signals(
        session_factory,
        "Fractal",
        [
            (base, "long", 21000.0, "old"),
            (base + timedelta(hours=2), "short", 21010.0, "recent"),
        ],
    )
    cutoff = (base + timedelta(hours=1)).isoformat()
    response = client.get(f"/api/monitor/signals?since={cutoff}")
    body = response.json()
    assert [s["reason"] for s in body] == ["recent"]


def test_limit_parameter_caps_count(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    base = datetime(2026, 4, 27, 10, 0)
    _seed_strategy_with_signals(
        session_factory,
        "Fractal",
        [
            (base + timedelta(minutes=i), "long", 21000.0 + i, f"sig-{i}")
            for i in range(10)
        ],
    )
    response = client.get("/api/monitor/signals?limit=3")
    assert len(response.json()) == 3
