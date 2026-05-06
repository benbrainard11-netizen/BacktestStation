"""POST /api/backtests/run — engine kickoff endpoint tests."""

from __future__ import annotations

import datetime as dt
import time
from collections.abc import Generator
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.data.schema import BARS_1M_SCHEMA
from app.db import models
from app.db.session import create_all, get_session, make_engine, make_session_factory
from app.main import app


@pytest.fixture
def warehouse(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Set BS_DATA_ROOT so the runner reads bars + writes outputs under tmp."""
    root = tmp_path / "data"
    root.mkdir()
    monkeypatch.setenv("BS_DATA_ROOT", str(root))
    return root


@pytest.fixture
def session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = make_engine(f"sqlite:///{tmp_path / 'run_api.sqlite'}")
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


def _seed_bars(data_root: Path, symbol: str, date: dt.date, minutes: int) -> None:
    out = (
        data_root
        / "processed"
        / "bars"
        / "timeframe=1m"
        / f"symbol={symbol}"
        / f"date={date.isoformat()}"
        / "part-000.parquet"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    start = pd.Timestamp(date, tz="UTC") + pd.Timedelta("13:30:00")
    rows = []
    for i in range(minutes):
        ts = start + pd.Timedelta(minutes=i)
        base = 21000.0 + i * 0.25
        rows.append(
            {
                "ts_event": ts,
                "symbol": symbol,
                "open": base,
                "high": base + 0.5,
                "low": base - 0.5,
                "close": base + 0.25,
                "volume": 100,
                "trade_count": 10,
                "vwap": base + 0.1,
            }
        )
    df = pd.DataFrame(rows)
    df["symbol"] = df["symbol"].astype("object")
    table = pa.Table.from_pandas(
        df, schema=BARS_1M_SCHEMA.pa_schema, preserve_index=False
    )
    pq.write_table(table, out)


def _seed_strategy(factory: sessionmaker[Session]) -> int:
    with factory() as session:
        strategy = models.Strategy(name="MA", slug="ma", status="research")
        version = models.StrategyVersion(strategy=strategy, version="v1")
        session.add_all([strategy, version])
        session.commit()
        return version.id


def _valid_payload(strategy_version_id: int) -> dict:
    return {
        "strategy_name": "moving_average_crossover",
        "strategy_version_id": strategy_version_id,
        "symbol": "NQ.c.0",
        "timeframe": "1m",
        "start": "2026-04-24",
        "end": "2026-04-25",
        "params": {"fast_period": 2, "slow_period": 4},
    }


def _wait_for_status(
    client: TestClient,
    run_id: int,
    statuses: set[str],
    *,
    timeout: float = 5.0,
) -> dict:
    deadline = time.monotonic() + timeout
    last_body: dict = {}
    while time.monotonic() < deadline:
        response = client.get(f"/api/backtests/{run_id}")
        assert response.status_code == 200, response.text
        last_body = response.json()
        if last_body["status"] in statuses:
            return last_body
        time.sleep(0.02)
    raise AssertionError(f"timed out waiting for {statuses}; last={last_body}")


def test_run_creates_backtest_row_end_to_end(
    client: TestClient,
    session_factory: sessionmaker[Session],
    warehouse: Path,
) -> None:
    _seed_bars(warehouse, "NQ.c.0", dt.date(2026, 4, 24), minutes=15)
    version_id = _seed_strategy(session_factory)

    response = client.post("/api/backtests/run", json=_valid_payload(version_id))

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["strategy_version_id"] == version_id
    assert body["symbol"] == "NQ.c.0"
    assert body["source"] == "engine"
    assert body["status"] == "complete"

    # File outputs landed under BS_DATA_ROOT/backtests/...
    run_dirs = list(
        (warehouse / "backtests" / "strategy=moving_average_crossover").glob("run=*")
    )
    assert len(run_dirs) == 1
    assert (run_dirs[0] / "metrics.json").exists()

    # Child rows persisted (equity at minimum — every bar gets a point).
    with session_factory() as session:
        equity_count = session.query(models.EquityPoint).count()
        assert equity_count == 15
        config_snap = session.query(models.ConfigSnapshot).first()
        assert config_snap is not None
        assert config_snap.payload["engine_version"] == "1"


def test_run_async_transitions_queued_running_complete(
    client: TestClient,
    session_factory: sessionmaker[Session],
    warehouse: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_bars(warehouse, "NQ.c.0", dt.date(2026, 4, 24), minutes=20)
    version_id = _seed_strategy(session_factory)

    import app.api.backtests as backtests_api

    original_engine_run = backtests_api.engine_run

    def slow_engine_run(*args, progress_callback=None, **kwargs):
        def wrapped_progress(done: int, total: int) -> None:
            if progress_callback is not None:
                progress_callback(done, total)
            time.sleep(0.005)

        return original_engine_run(
            *args, progress_callback=wrapped_progress, **kwargs
        )

    monkeypatch.setattr(backtests_api, "engine_run", slow_engine_run)

    response = client.post(
        "/api/backtests/run-async",
        json={**_valid_payload(version_id), "idea_id": 142},
    )

    assert response.status_code == 202, response.text
    queued = response.json()
    assert queued["status"] == "queued"
    run_id = queued["run_id"]

    first_read = client.get(f"/api/backtests/{run_id}").json()
    assert first_read["status"] in {"queued", "running", "complete"}

    running = _wait_for_status(client, run_id, {"running", "complete"})
    if running["status"] == "running":
        assert running["progress_pct"] is not None
        assert running["eta_seconds"] is None or running["eta_seconds"] >= 0

    complete = _wait_for_status(client, run_id, {"complete"})
    assert complete["progress_pct"] == 100.0
    assert complete["eta_seconds"] == 0

    with session_factory() as session:
        run = session.get(models.BacktestRun, run_id)
        assert run is not None
        assert run.status == "complete"
        assert run.tags == ["idea:142"]
        assert session.query(models.EquityPoint).count() == 20


def test_run_async_returns_immediately_for_slow_engine(
    client: TestClient,
    session_factory: sessionmaker[Session],
    warehouse: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_bars(warehouse, "NQ.c.0", dt.date(2026, 4, 24), minutes=10)
    version_id = _seed_strategy(session_factory)

    import app.api.backtests as backtests_api

    original_engine_run = backtests_api.engine_run

    def slow_engine_run(*args, **kwargs):
        time.sleep(0.25)
        return original_engine_run(*args, **kwargs)

    monkeypatch.setattr(backtests_api, "engine_run", slow_engine_run)

    started = time.monotonic()
    response = client.post("/api/backtests/run-async", json=_valid_payload(version_id))
    elapsed = time.monotonic() - started

    assert response.status_code == 202, response.text
    assert elapsed < 0.15
    _wait_for_status(client, response.json()["run_id"], {"complete"})


def test_run_async_marks_failed_when_background_run_errors(
    client: TestClient,
    session_factory: sessionmaker[Session],
    warehouse: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_bars(warehouse, "NQ.c.0", dt.date(2026, 4, 24), minutes=10)
    version_id = _seed_strategy(session_factory)

    import app.api.backtests as backtests_api

    def broken_engine_run(*args, **kwargs):
        raise RuntimeError("strategy exploded")

    monkeypatch.setattr(backtests_api, "engine_run", broken_engine_run)

    response = client.post("/api/backtests/run-async", json=_valid_payload(version_id))

    assert response.status_code == 202, response.text
    failed = _wait_for_status(client, response.json()["run_id"], {"failed"})
    assert failed["progress_pct"] is None
    assert failed["eta_seconds"] is None


def test_run_with_unknown_strategy_returns_422(
    client: TestClient,
    session_factory: sessionmaker[Session],
    warehouse: Path,
) -> None:
    _seed_bars(warehouse, "NQ.c.0", dt.date(2026, 4, 24), minutes=10)
    version_id = _seed_strategy(session_factory)

    payload = _valid_payload(version_id)
    payload["strategy_name"] = "no_such_strategy"

    response = client.post("/api/backtests/run", json=payload)
    assert response.status_code == 422
    assert "no_such_strategy" in response.text


def test_run_with_missing_strategy_version_returns_404(
    client: TestClient,
    warehouse: Path,
) -> None:
    _seed_bars(warehouse, "NQ.c.0", dt.date(2026, 4, 24), minutes=10)

    payload = _valid_payload(strategy_version_id=99999)
    response = client.post("/api/backtests/run", json=payload)
    assert response.status_code == 404


def test_run_with_start_after_end_returns_422(
    client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    version_id = _seed_strategy(session_factory)

    payload = _valid_payload(version_id)
    payload["start"] = "2026-04-25"
    payload["end"] = "2026-04-24"

    response = client.post("/api/backtests/run", json=payload)
    assert response.status_code == 422
    assert "start must be on or before end" in response.text


def test_run_with_no_bars_in_warehouse_returns_422(
    client: TestClient,
    session_factory: sessionmaker[Session],
    warehouse: Path,
) -> None:
    """Empty warehouse for the requested symbol -- explicit 422, not a silent
    successful empty run."""
    version_id = _seed_strategy(session_factory)

    response = client.post("/api/backtests/run", json=_valid_payload(version_id))
    assert response.status_code == 422
    assert "no bars found" in response.text
