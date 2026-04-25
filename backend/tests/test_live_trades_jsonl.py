"""Tests for the live trades.jsonl one-shot importer."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest
from sqlalchemy import select

from app.db import models
from app.db.session import create_all, make_engine, make_session_factory
from app.ingest.live_trades_jsonl import (
    RUN_NAME_PREFIX,
    import_jsonl,
    parse_record,
    read_jsonl,
)


# A valid JSONL record matching live_bot.py's emitted shape.
VALID_RECORD = {
    "date": "2026-04-24",
    "entry_time": "10:15:00",
    "direction": "BULLISH",
    "symbol": "NQM6",
    "contracts": 1,
    "entry_price": 21000.0,
    "exit_price": 21030.0,
    "stop": 20990.0,
    "target": 21030.0,
    "risk": 10.0,
    "risk_dollars": 200.0,
    "rof_score": 0,
    "exit_reason": "TP",
    "pnl_r": 3.0,
    "pnl_dollars": 600.0,
    "order_id": "ord-1",
    "basket_id": "basket-1",
}


def _seed_strategy(factory):
    with factory() as session:
        strategy = models.Strategy(name="Fractal AMD", slug="fractal-amd", status="live")
        version = models.StrategyVersion(strategy=strategy, version="trusted_v1")
        session.add_all([strategy, version])
        session.commit()
        return version.id


@pytest.fixture
def db_url(tmp_path: Path) -> str:
    """Isolated SQLite DB per test."""
    return f"sqlite:///{tmp_path / 'live_jsonl.sqlite'}"


@pytest.fixture
def factory(db_url: str):
    engine = make_engine(db_url)
    create_all(engine)
    return make_session_factory(engine)


def _write_jsonl(path: Path, records: list[dict]) -> Path:
    with path.open("w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")
    return path


# --- parse_record ------------------------------------------------------


def test_parse_bullish_to_long():
    parsed = parse_record(VALID_RECORD)
    assert parsed is not None
    assert parsed.side == "long"


def test_parse_bearish_to_short():
    rec = {**VALID_RECORD, "direction": "BEARISH"}
    parsed = parse_record(rec)
    assert parsed is not None
    assert parsed.side == "short"


def test_parse_unknown_direction_returns_none():
    rec = {**VALID_RECORD, "direction": "SIDEWAYS"}
    assert parse_record(rec) is None


def test_parse_missing_required_field_returns_none():
    rec = {**VALID_RECORD}
    del rec["entry_price"]
    assert parse_record(rec) is None


def test_parse_missing_pnl_dollars_is_optional():
    """Older live-bot builds don't emit pnl_dollars; importer keeps the trade
    and leaves Trade.pnl as None."""
    rec = {**VALID_RECORD}
    del rec["pnl_dollars"]
    parsed = parse_record(rec)
    assert parsed is not None
    assert parsed.pnl_dollars is None
    assert parsed.pnl_r == pytest.approx(3.0)


def test_parse_v2_exit_time_populates_exit_ts():
    """live_bot v2+ records carry exit_time; importer should populate
    Trade.exit_ts (ET -> UTC, tz-naive)."""
    rec = {
        **VALID_RECORD,
        "exit_time": "2026-04-24T10:30:00",  # ET
        "session_label": "NY_AM",
        "schema_version": "live_bot_v2",
    }
    parsed = parse_record(rec)
    assert parsed is not None
    assert parsed.exit_ts is not None
    assert parsed.exit_ts.tzinfo is None
    # ET 10:30 -> UTC 14:30 during EDT.
    assert parsed.exit_ts.hour == 14
    assert parsed.exit_ts.minute == 30
    assert parsed.session_label == "NY_AM"


def test_parse_v1_record_has_null_exit_ts():
    """Existing v1 records without exit_time still parse; exit_ts None."""
    rec = {**VALID_RECORD}  # no exit_time field
    parsed = parse_record(rec)
    assert parsed is not None
    assert parsed.exit_ts is None
    assert parsed.session_label is None


def test_parse_v2_malformed_exit_time_does_not_drop_record():
    """A bad exit_time string shouldn't kill the whole record import."""
    rec = {**VALID_RECORD, "exit_time": "not-a-date"}
    parsed = parse_record(rec)
    assert parsed is not None
    assert parsed.exit_ts is None  # gracefully nulled


def test_parse_missing_symbol_and_contracts_uses_defaults():
    """symbol defaults to '', contracts to 1 when absent (older live builds)."""
    rec = {**VALID_RECORD}
    del rec["symbol"]
    del rec["contracts"]
    parsed = parse_record(rec)
    assert parsed is not None
    assert parsed.symbol == ""
    assert parsed.contracts == 1


def test_parse_converts_et_to_utc_naive():
    """ET 10:15 -> UTC 14:15 (during EDT). Stored tz-naive."""
    parsed = parse_record(VALID_RECORD)
    assert parsed is not None
    assert parsed.entry_ts.tzinfo is None  # tz-naive UTC for SQLite
    # 2026-04-24 10:15 ET = 14:15 UTC during EDT
    assert parsed.entry_ts.hour == 14
    assert parsed.entry_ts.minute == 15


# --- read_jsonl --------------------------------------------------------


def test_read_jsonl_skips_blank_and_malformed_lines(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
):
    p = tmp_path / "trades.jsonl"
    with p.open("w", encoding="utf-8") as fh:
        fh.write(json.dumps(VALID_RECORD) + "\n")
        fh.write("\n")  # blank line ignored silently
        fh.write("not json at all\n")  # malformed -> warning
        fh.write(json.dumps({**VALID_RECORD, "direction": "??"}) + "\n")  # invalid

    caplog.set_level(logging.WARNING)
    log = logging.getLogger("test_live_trades_jsonl")
    trades = read_jsonl(p, log)

    assert len(trades) == 1
    # Two warnings: malformed line + bad direction
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 2


# --- import_jsonl (end to end) -----------------------------------------


def test_import_creates_run_with_trades_and_config_snapshot(
    tmp_path: Path, db_url: str, factory
):
    version_id = _seed_strategy(factory)
    p = _write_jsonl(tmp_path / "trades.jsonl", [VALID_RECORD])

    run_id, count = import_jsonl(
        p, strategy_version_id=version_id, symbol="NQ.c.0", db_url=db_url
    )

    assert run_id > 0
    assert count == 1

    with factory() as session:
        run = session.get(models.BacktestRun, run_id)
        assert run is not None
        assert run.source == "live"
        assert run.symbol == "NQ.c.0"
        assert run.name.startswith(RUN_NAME_PREFIX)

        trades = session.scalars(
            select(models.Trade).where(models.Trade.backtest_run_id == run_id)
        ).all()
        assert len(trades) == 1
        assert trades[0].side == "long"
        assert trades[0].pnl == pytest.approx(600.0)
        assert trades[0].r_multiple == pytest.approx(3.0)
        assert trades[0].exit_ts is None  # JSONL schema doesn't store exit_time

        snap = session.scalars(
            select(models.ConfigSnapshot).where(
                models.ConfigSnapshot.backtest_run_id == run_id
            )
        ).first()
        assert snap is not None
        assert snap.payload["import_kind"] == "live_trades_jsonl"
        assert snap.payload["trade_count"] == 1


def test_import_is_idempotent_replaces_prior_run(
    tmp_path: Path, db_url: str, factory
):
    """Re-running the importer leaves exactly one live run for that JSONL,
    not two."""
    version_id = _seed_strategy(factory)
    p = _write_jsonl(tmp_path / "trades.jsonl", [VALID_RECORD])

    first_run_id, _ = import_jsonl(
        p, strategy_version_id=version_id, symbol="NQ.c.0", db_url=db_url
    )

    # Bot adds a second trade.
    second = {
        **VALID_RECORD,
        "entry_time": "11:30:00",
        "direction": "BEARISH",
        "order_id": "ord-2",
        "basket_id": "basket-2",
        "pnl_dollars": -200.0,
        "pnl_r": -1.0,
    }
    _write_jsonl(p, [VALID_RECORD, second])

    second_run_id, second_count = import_jsonl(
        p, strategy_version_id=version_id, symbol="NQ.c.0", db_url=db_url
    )

    assert second_count == 2
    # The replacement may or may not reuse the prior id (SQLite's
    # autoincrement behavior depends on rowid). What matters is that
    # there is exactly ONE live run for this jsonl after the second
    # import.
    with factory() as session:
        live_runs = session.scalars(
            select(models.BacktestRun).where(models.BacktestRun.source == "live")
        ).all()
        assert len(live_runs) == 1
        assert live_runs[0].id == second_run_id

        trades = session.scalars(
            select(models.Trade).where(
                models.Trade.backtest_run_id == second_run_id
            )
        ).all()
        assert len(trades) == 2

    # And the original run+trades are gone (cascade).
    if first_run_id != second_run_id:
        with factory() as session:
            assert session.get(models.BacktestRun, first_run_id) is None


def test_import_empty_jsonl_creates_no_run(tmp_path: Path, db_url: str, factory):
    """An empty file imports cleanly without creating a run row."""
    version_id = _seed_strategy(factory)
    p = tmp_path / "trades.jsonl"
    p.write_text("", encoding="utf-8")

    run_id, count = import_jsonl(
        p, strategy_version_id=version_id, symbol="NQ.c.0", db_url=db_url
    )

    assert run_id == 0
    assert count == 0
    with factory() as session:
        assert (
            session.scalars(
                select(models.BacktestRun).where(models.BacktestRun.source == "live")
            ).first()
            is None
        )
