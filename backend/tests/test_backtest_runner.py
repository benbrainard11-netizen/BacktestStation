"""Tests for the runner: file outputs + DB row insertion + bar loading."""

from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.backtest.engine import RunConfig
from app.backtest.runner import (
    load_aux_bars,
    load_bars,
    make_run_dir,
    run_backtest,
    write_run,
)
from app.data.schema import BARS_1M_SCHEMA
from app.db import models
from app.db.session import create_all, make_engine, make_session_factory


# --- Bar loading -------------------------------------------------------


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


@pytest.fixture
def warehouse(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "data"
    root.mkdir()
    monkeypatch.setenv("BS_DATA_ROOT", str(root))
    return root


def test_load_bars_returns_dataclasses(warehouse: Path) -> None:
    _seed_bars(warehouse, "NQ.c.0", dt.date(2026, 4, 24), minutes=10)
    config = RunConfig(
        strategy_name="moving_average_crossover",
        symbol="NQ.c.0",
        timeframe="1m",
        start="2026-04-24",
        end="2026-04-25",
        params={"fast_period": 2, "slow_period": 4},
    )
    bars = load_bars(config)
    assert len(bars) == 10
    assert bars[0].symbol == "NQ.c.0"
    assert isinstance(bars[0].ts_event, dt.datetime)
    assert bars[0].ts_event.tzinfo is not None


def test_load_aux_bars_indexes_by_ts(warehouse: Path) -> None:
    """Runner reads aux symbols and returns {symbol: {ts: Bar}}."""
    _seed_bars(warehouse, "NQ.c.0", dt.date(2026, 4, 24), minutes=10)
    _seed_bars(warehouse, "ES.c.0", dt.date(2026, 4, 24), minutes=10)
    config = RunConfig(
        strategy_name="moving_average_crossover",
        symbol="NQ.c.0",
        timeframe="1m",
        start="2026-04-24",
        end="2026-04-25",
        aux_symbols=["ES.c.0"],
        params={"fast_period": 2, "slow_period": 4},
    )
    aux = load_aux_bars(config)
    assert "ES.c.0" in aux
    assert len(aux["ES.c.0"]) == 10
    # Each value is a Bar keyed by its ts_event.
    sample_ts, sample_bar = next(iter(aux["ES.c.0"].items()))
    assert sample_bar.ts_event == sample_ts
    assert sample_bar.symbol == "ES.c.0"


def test_load_aux_bars_handles_missing_symbol(warehouse: Path) -> None:
    """Aux symbol with no warehouse data -> empty inner dict."""
    _seed_bars(warehouse, "NQ.c.0", dt.date(2026, 4, 24), minutes=5)
    config = RunConfig(
        strategy_name="moving_average_crossover",
        symbol="NQ.c.0",
        timeframe="1m",
        start="2026-04-24",
        end="2026-04-25",
        aux_symbols=["RTY.c.0"],
        params={"fast_period": 2, "slow_period": 4},
    )
    aux = load_aux_bars(config)
    assert aux == {"RTY.c.0": {}}


# --- Output file structure ---------------------------------------------


def test_make_run_dir_creates_hive_style_path(tmp_path: Path) -> None:
    started = dt.datetime(2026, 4, 24, 15, 30, 0, tzinfo=dt.timezone.utc)
    out, run_id = make_run_dir(tmp_path, "moving_average_crossover", started)
    assert out.exists()
    assert "strategy=moving_average_crossover" in str(out)
    assert "run=" in str(out)
    assert run_id


def test_run_writes_all_five_outputs(warehouse: Path) -> None:
    _seed_bars(warehouse, "NQ.c.0", dt.date(2026, 4, 24), minutes=15)
    config = RunConfig(
        strategy_name="moving_average_crossover",
        symbol="NQ.c.0",
        timeframe="1m",
        start="2026-04-24",
        end="2026-04-25",
        params={"fast_period": 2, "slow_period": 4},
    )
    result, out_dir, run_id = run_backtest(config, persist=True)
    assert out_dir is not None
    assert (out_dir / "config.json").exists()
    assert (out_dir / "trades.parquet").exists()
    assert (out_dir / "equity.parquet").exists()
    assert (out_dir / "events.parquet").exists()
    assert (out_dir / "metrics.json").exists()

    # config.json contains engine_version + git_sha + start/end timestamps
    config_payload = json.loads((out_dir / "config.json").read_text("utf-8"))
    assert config_payload["engine_version"] == "1"
    assert "started_at" in config_payload
    assert "completed_at" in config_payload
    assert config_payload["strategy_name"] == "moving_average_crossover"

    # metrics.json round-trips correctly
    metrics = json.loads((out_dir / "metrics.json").read_text("utf-8"))
    assert metrics["trade_count"] == result.metrics["trade_count"]


def test_persist_false_writes_nothing(warehouse: Path) -> None:
    _seed_bars(warehouse, "NQ.c.0", dt.date(2026, 4, 24), minutes=10)
    config = RunConfig(
        strategy_name="moving_average_crossover",
        symbol="NQ.c.0",
        timeframe="1m",
        start="2026-04-24",
        end="2026-04-25",
        params={"fast_period": 2, "slow_period": 4},
    )
    _, out_dir, run_id = run_backtest(config, persist=False)
    assert out_dir is None
    assert run_id is None


# --- DB integration ----------------------------------------------------


def test_run_inserts_db_row_with_source_engine(
    warehouse: Path, tmp_path: Path
) -> None:
    """The run inserts a BacktestRun row tagged source='engine'."""
    _seed_bars(warehouse, "NQ.c.0", dt.date(2026, 4, 24), minutes=15)

    # Use a temp SQLite DB so we don't touch the dev one.
    db_path = tmp_path / "meta.sqlite"
    db_url = f"sqlite:///{db_path}"
    engine = make_engine(db_url)
    create_all(engine)
    factory = make_session_factory(engine)

    # Seed a strategy version so we have an FK target.
    with factory() as session:
        strat = models.Strategy(name="ORB", slug="orb", status="research")
        ver = models.StrategyVersion(strategy=strat, version="v1")
        session.add(strat)
        session.commit()
        version_id = ver.id

    config = RunConfig(
        strategy_name="moving_average_crossover",
        symbol="NQ.c.0",
        timeframe="1m",
        start="2026-04-24",
        end="2026-04-25",
        params={"fast_period": 2, "slow_period": 4},
    )
    _, _, run_id = run_backtest(
        config, strategy_version_id=version_id, db_url=db_url
    )
    assert run_id is not None

    with factory() as session:
        run_row = session.get(models.BacktestRun, run_id)
        assert run_row is not None
        assert run_row.source == "engine"
        assert run_row.symbol == "NQ.c.0"
        assert run_row.timeframe == "1m"
        # Trades + equity + metrics + config rows were inserted.
        config_snap = session.scalars(
            select(models.ConfigSnapshot).where(
                models.ConfigSnapshot.backtest_run_id == run_id
            )
        ).first()
        assert config_snap is not None
        assert config_snap.payload["engine_version"] == "1"
