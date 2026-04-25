"""POST /api/backtests/run — engine kickoff endpoint tests."""

from __future__ import annotations

import datetime as dt
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
