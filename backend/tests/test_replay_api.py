"""Tests for GET /api/replay/{symbol}/{date}."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from fastapi.testclient import TestClient

from app.data.schema import BARS_1M_SCHEMA
from app.db import models
from app.db.session import (
    create_all,
    get_session,
    make_engine,
    make_session_factory,
)
from app.main import app


def _seed_bars(
    data_root: Path, symbol: str, date: dt.date, minutes: int = 5
) -> None:
    """Write a tiny per-day partition so read_bars can find it."""
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


@pytest.fixture
def api_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    data_root = tmp_path / "data"
    data_root.mkdir()
    monkeypatch.setenv("BS_DATA_ROOT", str(data_root))

    engine = make_engine(f"sqlite:///{tmp_path / 'replay.sqlite'}")
    create_all(engine)
    SessionLocal = make_session_factory(engine)

    def _override():
        s = SessionLocal()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_session] = _override
    try:
        with TestClient(app) as client:
            yield client, SessionLocal, data_root
    finally:
        app.dependency_overrides.pop(get_session, None)


def _seed_strategy_with_run(SessionLocal, with_trades: list[dict]) -> int:
    with SessionLocal() as session:
        strategy = models.Strategy(name="Replay test", slug="replay-test")
        version = models.StrategyVersion(version="v1", strategy=strategy)
        run = models.BacktestRun(
            symbol="NQ.c.0",
            timeframe="1m",
            strategy_version=version,
            source="engine",
            status="completed",
        )
        for spec in with_trades:
            run.trades.append(
                models.Trade(
                    entry_ts=spec["entry_ts"],
                    exit_ts=spec.get("exit_ts"),
                    symbol="NQ.c.0",
                    side=spec["side"],
                    entry_price=spec["entry_price"],
                    exit_price=spec.get("exit_price"),
                    stop_price=spec.get("stop_price"),
                    target_price=spec.get("target_price"),
                    size=1.0,
                    pnl=spec.get("pnl"),
                    r_multiple=spec.get("r_multiple"),
                    exit_reason=spec.get("exit_reason"),
                )
            )
        session.add(strategy)
        session.commit()
        return run.id


def test_replay_returns_bars_for_seeded_day(api_client) -> None:
    client, _SessionLocal, data_root = api_client
    _seed_bars(data_root, "NQ.c.0", dt.date(2026, 4, 22), minutes=5)

    response = client.get("/api/replay/NQ.c.0/2026-04-22")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["symbol"] == "NQ.c.0"
    assert body["date"] == "2026-04-22"
    assert len(body["bars"]) == 5
    first = body["bars"][0]
    assert first["open"] == 21000.0
    assert first["volume"] == 100
    assert body["entries"] == []


def test_replay_returns_empty_bars_for_unseeded_day(api_client) -> None:
    client, _SessionLocal, _root = api_client
    response = client.get("/api/replay/NQ.c.0/2030-01-01")
    assert response.status_code == 200
    assert response.json()["bars"] == []


def test_replay_attaches_run_entries_filtered_by_date(api_client) -> None:
    client, SessionLocal, data_root = api_client
    _seed_bars(data_root, "NQ.c.0", dt.date(2026, 4, 22), minutes=5)
    _seed_bars(data_root, "NQ.c.0", dt.date(2026, 4, 23), minutes=5)

    run_id = _seed_strategy_with_run(
        SessionLocal,
        with_trades=[
            {
                "entry_ts": dt.datetime(2026, 4, 22, 13, 31),
                "exit_ts": dt.datetime(2026, 4, 22, 13, 35),
                "side": "short",
                "entry_price": 21000.5,
                "exit_price": 20990.0,
                "stop_price": 21010.0,
                "target_price": 20970.0,
                "pnl": 210.0,
                "r_multiple": 2.0,
                "exit_reason": "target",
            },
            # On a different day — should NOT come back for 04-22.
            {
                "entry_ts": dt.datetime(2026, 4, 23, 13, 31),
                "side": "long",
                "entry_price": 21100.0,
            },
        ],
    )

    response = client.get(
        f"/api/replay/NQ.c.0/2026-04-22?backtest_run_id={run_id}"
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["backtest_run_id"] == run_id
    assert len(body["entries"]) == 1
    e = body["entries"][0]
    assert e["side"] == "short"
    assert e["entry_price"] == 21000.5
    assert e["pnl"] == 210.0


def test_replay_404_for_missing_run(api_client) -> None:
    client, _SessionLocal, _root = api_client
    response = client.get("/api/replay/NQ.c.0/2026-04-22?backtest_run_id=999")
    assert response.status_code == 404
