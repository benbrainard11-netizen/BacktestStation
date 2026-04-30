from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app.db import models
from app.db.session import create_all, make_engine, make_session_factory

EXPECTED_TABLES = {
    "strategies",
    "strategy_versions",
    "backtest_runs",
    "trades",
    "equity_points",
    "run_metrics",
    "config_snapshots",
    "live_signals",
    "live_heartbeats",
    "notes",
    "knowledge_cards",
}


def test_create_all_creates_required_tables(tmp_path: Path) -> None:
    db_file = tmp_path / "phase1.sqlite"
    engine = make_engine(f"sqlite:///{db_file}")

    create_all(engine)

    tables = set(inspect(engine).get_table_names())
    missing = EXPECTED_TABLES - tables
    assert not missing, f"missing tables: {sorted(missing)}"
    assert db_file.exists()


def test_strategy_chain_roundtrip(tmp_path: Path) -> None:
    """Insert a strategy + version + run + trade + metrics + config + equity
    point, then read it back. Exercises FK relationships and JSON columns
    end-to-end on the same SQLite engine the importer will use."""
    engine = make_engine(f"sqlite:///{tmp_path / 'roundtrip.sqlite'}")
    create_all(engine)
    SessionLocal = make_session_factory(engine)

    with SessionLocal() as session:
        strategy = models.Strategy(
            name="Opening Range Breakout",
            slug="orb",
            status="testing",
            tags=["intraday", "futures"],
        )
        version = models.StrategyVersion(version="1.0", strategy=strategy)
        run = models.BacktestRun(
            symbol="NQ",
            timeframe="1m",
            import_source="trades.csv",
            strategy_version=version,
        )
        run.metrics = models.RunMetrics(net_pnl=1234.5, trade_count=10, win_rate=0.6)
        run.config_snapshot = models.ConfigSnapshot(
            payload={"slippage": 0.25, "commission": 1.5}
        )
        run.equity_points.append(
            models.EquityPoint(ts=datetime(2026, 1, 2, 13, 30), equity=100_000.0)
        )
        run.trades.append(
            models.Trade(
                entry_ts=datetime(2026, 1, 2, 13, 30),
                symbol="NQ",
                side="long",
                entry_price=21000.0,
                size=1.0,
                tags=["breakout"],
            )
        )
        session.add(strategy)
        session.commit()
        run_id = run.id

    with SessionLocal() as session:
        loaded = session.get(models.BacktestRun, run_id)
        assert loaded is not None
        assert loaded.strategy_version.strategy.slug == "orb"
        assert loaded.strategy_version.strategy.tags == ["intraday", "futures"]
        assert loaded.metrics is not None
        assert loaded.metrics.net_pnl == 1234.5
        assert loaded.config_snapshot is not None
        assert loaded.config_snapshot.payload["slippage"] == 0.25
        assert len(loaded.equity_points) == 1
        assert len(loaded.trades) == 1
        assert loaded.trades[0].tags == ["breakout"]


def test_backtest_runs_has_tags_column(tmp_path: Path) -> None:
    """Regression: PUT /api/backtests/{id}/tags writes to BacktestRun.tags
    but the column was missing in the schema for a long stretch, silently
    dropping values on commit. Lock the column in."""
    engine = make_engine(f"sqlite:///{tmp_path / 'tags.sqlite'}")
    create_all(engine)
    columns = {c["name"] for c in inspect(engine).get_columns("backtest_runs")}
    assert "tags" in columns

    SessionLocal = make_session_factory(engine)
    with SessionLocal() as session:
        strategy = models.Strategy(name="T", slug="t")
        version = models.StrategyVersion(version="v1", strategy=strategy)
        run = models.BacktestRun(
            symbol="NQ",
            import_source="t",
            strategy_version=version,
            tags=["validated", "live-candidate"],
        )
        session.add(strategy)
        session.commit()
        run_id = run.id

    with SessionLocal() as session:
        loaded = session.get(models.BacktestRun, run_id)
        assert loaded is not None
        assert loaded.tags == ["validated", "live-candidate"]


def test_chat_messages_has_section_column(tmp_path: Path) -> None:
    """Stage-3 prep (2026-04-30): ChatMessage.section exists on fresh DBs
    so per-section AI agents can attach their threads. Nullable; legacy
    rows backfill to NULL."""
    engine = make_engine(f"sqlite:///{tmp_path / 'chat_section.sqlite'}")
    create_all(engine)
    columns = {c["name"] for c in inspect(engine).get_columns("chat_messages")}
    assert "section" in columns

    SessionLocal = make_session_factory(engine)
    with SessionLocal() as session:
        strategy = models.Strategy(name="X", slug="x")
        session.add(strategy)
        session.commit()
        msg = models.ChatMessage(
            strategy_id=strategy.id,
            role="user",
            content="hello build agent",
            model="claude",
            section="build",
        )
        session.add(msg)
        session.commit()
        msg_id = msg.id

    with SessionLocal() as session:
        loaded = session.get(models.ChatMessage, msg_id)
        assert loaded is not None
        assert loaded.section == "build"


def test_knowledge_cards_roundtrip(tmp_path: Path) -> None:
    engine = make_engine(f"sqlite:///{tmp_path / 'knowledge_card.sqlite'}")
    create_all(engine)
    columns = {c["name"] for c in inspect(engine).get_columns("knowledge_cards")}
    for expected in [
        "strategy_id",
        "kind",
        "name",
        "summary",
        "body",
        "formula",
        "inputs",
        "use_cases",
        "failure_modes",
        "status",
        "source",
        "tags",
    ]:
        assert expected in columns

    SessionLocal = make_session_factory(engine)
    with SessionLocal() as session:
        strategy = models.Strategy(name="T", slug="t")
        session.add(strategy)
        session.commit()
        card = models.KnowledgeCard(
            strategy_id=strategy.id,
            kind="orderflow_formula",
            name="Aggressor Imbalance",
            formula="(ask_volume - bid_volume) / total_volume",
            inputs=["ask_volume", "bid_volume"],
            status="draft",
            tags=["orderflow"],
        )
        session.add(card)
        session.commit()
        card_id = card.id

    with SessionLocal() as session:
        loaded = session.get(models.KnowledgeCard, card_id)
        assert loaded is not None
        assert loaded.name == "Aggressor Imbalance"
        assert loaded.inputs == ["ask_volume", "bid_volume"]
        assert loaded.tags == ["orderflow"]


def test_legacy_chat_table_missing_section_is_migrated(tmp_path: Path) -> None:
    """An older DB created before the section column should pick it up
    via the guarded ALTER. Idempotent across re-runs."""
    db_path = tmp_path / "legacy_chat.sqlite"
    engine = make_engine(f"sqlite:///{db_path}")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE chat_messages ("
                " id INTEGER PRIMARY KEY,"
                " strategy_id INTEGER NOT NULL,"
                " role VARCHAR(16) NOT NULL,"
                " content TEXT NOT NULL,"
                " model VARCHAR(16) NOT NULL DEFAULT 'claude',"
                " cli_session_id VARCHAR(64),"
                " cost_usd FLOAT,"
                " created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP"
                ")"
            )
        )

    create_all(engine)  # triggers _run_data_migrations
    columns = {c["name"] for c in inspect(engine).get_columns("chat_messages")}
    assert "section" in columns

    # Re-running is a no-op.
    create_all(engine)
    columns = {c["name"] for c in inspect(engine).get_columns("chat_messages")}
    assert "section" in columns


def test_legacy_db_missing_tags_column_is_migrated(tmp_path: Path) -> None:
    """An older `data/meta.sqlite` may have backtest_runs WITHOUT the tags
    column. _run_data_migrations should add it idempotently."""
    db_path = tmp_path / "legacy.sqlite"
    engine = make_engine(f"sqlite:///{db_path}")

    # Build the legacy schema by hand — same shape as the model minus
    # the columns added in subsequent migrations.
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE backtest_runs ("
                " id INTEGER PRIMARY KEY,"
                " strategy_version_id INTEGER NOT NULL,"
                " name VARCHAR(200),"
                " symbol VARCHAR(40) NOT NULL,"
                " timeframe VARCHAR(20),"
                " session_label VARCHAR(40),"
                " start_ts DATETIME,"
                " end_ts DATETIME,"
                " import_source TEXT,"
                " status VARCHAR(20) NOT NULL DEFAULT 'imported',"
                " created_at DATETIME"
                ")"
            )
        )

    create_all(engine)  # triggers _run_data_migrations

    columns = {c["name"] for c in inspect(engine).get_columns("backtest_runs")}
    assert "tags" in columns

    # Re-running the migration is a no-op (idempotent).
    create_all(engine)
    columns = {c["name"] for c in inspect(engine).get_columns("backtest_runs")}
    assert "tags" in columns


def test_sqlite_foreign_keys_enforced(tmp_path: Path) -> None:
    """SQLite ships with FK enforcement OFF — the engine factory enables it
    so declared relationships actually prevent orphan rows. Inserting a
    Trade with a bogus backtest_run_id should raise IntegrityError."""
    engine = make_engine(f"sqlite:///{tmp_path / 'fk.sqlite'}")
    create_all(engine)

    # Confirm the pragma is on at the connection level.
    with engine.connect() as connection:
        result = connection.execute(text("PRAGMA foreign_keys")).scalar()
        assert result == 1, f"expected foreign_keys=1, got {result}"

    SessionLocal = make_session_factory(engine)
    with SessionLocal() as session:
        # backtest_run_id 9999 does not exist — FK should reject the trade.
        bad_trade = models.Trade(
            backtest_run_id=9999,
            entry_ts=datetime(2026, 1, 2, 13, 30),
            symbol="NQ",
            side="long",
            entry_price=21000.0,
            size=1.0,
        )
        session.add(bad_trade)
        with pytest.raises(IntegrityError):
            session.commit()
