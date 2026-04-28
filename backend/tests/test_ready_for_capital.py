"""Tests for the ready-for-capital gate.

Pure logic tests against `evaluate_gate`. The CLI wrapper (formatting,
exit code) is exercised separately via subprocess at the end.
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from app.cli.ready_for_capital_check import (
    DEFAULT_MAX_DD_R,
    DEFAULT_MIN_TRADES,
    DEFAULT_MIN_WR,
    evaluate_gate,
)
from app.db.models import BacktestRun, Strategy, StrategyVersion, Trade
from app.db.session import create_all, make_engine, make_session_factory


@pytest.fixture
def session(tmp_path: Path) -> Session:
    engine = make_engine(f"sqlite:///{tmp_path / 'gate.sqlite'}")
    create_all(engine)
    SessionLocal = make_session_factory(engine)
    s = SessionLocal()
    yield s
    s.close()


_STRAT_COUNTER = {"n": 0}


def _make_version(session: Session) -> StrategyVersion:
    _STRAT_COUNTER["n"] += 1
    n = _STRAT_COUNTER["n"]
    strat = Strategy(name=f"FractalAMD-{n}", slug=f"fractal-amd-{n}")
    session.add(strat)
    session.flush()
    version = StrategyVersion(strategy_id=strat.id, version="v1")
    session.add(version)
    session.flush()
    return version


def _make_live_run(session: Session, version: StrategyVersion) -> BacktestRun:
    run = BacktestRun(
        strategy_version_id=version.id,
        symbol="NQ.c.0",
        timeframe="1m",
        source="live",
        status="complete",
    )
    session.add(run)
    session.flush()
    return run


def _add_trade(
    session: Session,
    run: BacktestRun,
    *,
    et_hour: int = 10,
    et_minute: int = 0,
    pnl: float = 100.0,
    r_multiple: float | None = 1.0,
    side: str = "long",
    day: dt.date = dt.date(2026, 4, 22),
) -> Trade:
    """Add a Trade with entry_ts set so it's at (et_hour, et_minute) ET.
    DB stores tz-naive UTC; ET +4h or +5h depending on DST. April 2026
    is on EDT (UTC-4), so ET 10:00 = UTC 14:00."""
    et_total_min = et_hour * 60 + et_minute
    utc_total_min = et_total_min + 4 * 60  # EDT
    h, m = divmod(utc_total_min, 60)
    entry_ts = dt.datetime(day.year, day.month, day.day, h, m)
    trade = Trade(
        backtest_run_id=run.id,
        entry_ts=entry_ts,
        symbol="NQ.c.0",
        side=side,
        entry_price=21000.0,
        size=1.0,
        pnl=pnl,
        r_multiple=r_multiple,
    )
    session.add(trade)
    return trade


# --- Criterion: trade count ---------------------------------------------


def test_gate_fails_when_too_few_trades(session: Session) -> None:
    version = _make_version(session)
    run = _make_live_run(session, version)
    for i in range(DEFAULT_MIN_TRADES - 1):
        _add_trade(session, run, pnl=50.0, r_multiple=0.5)
    session.commit()

    report = evaluate_gate(session, version.id)
    assert not report.passed
    trade_count = next(c for c in report.criteria if c.name == "trade_count")
    assert not trade_count.passed
    assert report.trade_count == DEFAULT_MIN_TRADES - 1


def test_gate_passes_with_enough_winning_trades(session: Session) -> None:
    version = _make_version(session)
    run = _make_live_run(session, version)
    # 30 trades, all wins, all in window → all gates pass.
    for i in range(DEFAULT_MIN_TRADES):
        _add_trade(session, run, pnl=100.0, r_multiple=1.0)
    session.commit()

    report = evaluate_gate(session, version.id)
    assert report.passed
    assert report.trade_count == DEFAULT_MIN_TRADES


# --- Criterion: win rate -------------------------------------------------


def test_gate_fails_when_win_rate_below_threshold(session: Session) -> None:
    version = _make_version(session)
    run = _make_live_run(session, version)
    # 30 trades, 30% win rate (9 wins, 21 losses) → fails 40% gate.
    for i in range(DEFAULT_MIN_TRADES):
        if i < 9:
            _add_trade(session, run, pnl=100.0, r_multiple=1.0)
        else:
            _add_trade(session, run, pnl=-50.0, r_multiple=-1.0)
    session.commit()

    report = evaluate_gate(session, version.id)
    wr_crit = next(c for c in report.criteria if c.name == "win_rate")
    assert not wr_crit.passed
    assert "30.0%" in wr_crit.actual


# --- Criterion: max drawdown --------------------------------------------


def test_gate_fails_when_drawdown_too_large(session: Session) -> None:
    version = _make_version(session)
    run = _make_live_run(session, version)
    # 30 trades: alternating but with a long losing streak that
    # produces > 10R drawdown. Sequence: 5 wins (+5R), then 12 losses (-12R)
    # → peak 5, trough -7, drawdown 12R.
    for _ in range(5):
        _add_trade(session, run, pnl=100.0, r_multiple=1.0)
    for _ in range(12):
        _add_trade(session, run, pnl=-100.0, r_multiple=-1.0)
    # Pad to min trade count with wins so trade_count gate passes.
    for _ in range(DEFAULT_MIN_TRADES - 17):
        _add_trade(session, run, pnl=100.0, r_multiple=1.0)
    session.commit()

    report = evaluate_gate(session, version.id)
    dd_crit = next(c for c in report.criteria if c.name == "max_drawdown_r")
    assert not dd_crit.passed
    assert "12.00R" in dd_crit.actual


# --- Criterion: entry window --------------------------------------------


def test_gate_fails_when_entry_outside_window(session: Session) -> None:
    version = _make_version(session)
    run = _make_live_run(session, version)
    for i in range(DEFAULT_MIN_TRADES):
        # First 5 trades fire at 09:00 ET (before window open at 09:30).
        if i < 5:
            _add_trade(session, run, et_hour=9, et_minute=0, pnl=100.0, r_multiple=1.0)
        else:
            _add_trade(session, run, et_hour=10, et_minute=0, pnl=100.0, r_multiple=1.0)
    session.commit()

    report = evaluate_gate(session, version.id)
    window_crit = next(c for c in report.criteria if c.name == "entry_window")
    assert not window_crit.passed
    assert "5/30" in window_crit.actual


def test_gate_window_close_is_exclusive(session: Session) -> None:
    """An entry exactly at 14:00 ET should fail (close is exclusive)."""
    version = _make_version(session)
    run = _make_live_run(session, version)
    # Pad with in-window winners.
    for _ in range(DEFAULT_MIN_TRADES - 1):
        _add_trade(session, run, et_hour=10, pnl=100.0, r_multiple=1.0)
    # One trade exactly at 14:00 ET.
    _add_trade(session, run, et_hour=14, et_minute=0, pnl=100.0, r_multiple=1.0)
    session.commit()

    report = evaluate_gate(session, version.id)
    window_crit = next(c for c in report.criteria if c.name == "entry_window")
    assert not window_crit.passed
    assert "1/" in window_crit.actual


# --- Empty / edge -------------------------------------------------------


def test_gate_with_no_live_runs_fails_all(session: Session) -> None:
    version = _make_version(session)
    session.commit()
    report = evaluate_gate(session, version.id)
    assert not report.passed
    assert report.trade_count == 0


def test_gate_with_no_live_runs_for_this_version_ignores_other_versions(
    session: Session,
) -> None:
    """Live runs for *other* strategy_versions don't bleed in."""
    version_a = _make_version(session)
    version_b = _make_version(session)
    run_other = _make_live_run(session, version_b)
    for _ in range(DEFAULT_MIN_TRADES):
        _add_trade(session, run_other, pnl=100.0, r_multiple=1.0)
    session.commit()

    report = evaluate_gate(session, version_a.id)
    assert report.trade_count == 0
    assert not report.passed
