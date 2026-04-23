from datetime import datetime
from pathlib import Path

from sqlalchemy import inspect

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
