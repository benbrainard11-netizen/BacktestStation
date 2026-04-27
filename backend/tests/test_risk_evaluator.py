"""Tests for app.services.risk_evaluator.evaluate_profile."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from app.db import models
from app.db.session import create_all, make_engine, make_session_factory
from app.schemas.risk_profile import serialize_allowed_hours
from app.services.risk_evaluator import evaluate_profile


_COUNTER = [0]


@pytest.fixture
def session(tmp_path: Path):
    engine = make_engine(f"sqlite:///{tmp_path / 'rev.sqlite'}")
    create_all(engine)
    SessionLocal = make_session_factory(engine)
    with SessionLocal() as s:
        yield s


def _make_strategy_version(session) -> int:
    _COUNTER[0] += 1
    n = _COUNTER[0]
    strategy = models.Strategy(
        name=f"E{n}", slug=f"e-{n}", status="testing"
    )
    version = models.StrategyVersion(version="1.0", strategy=strategy)
    session.add(strategy)
    session.commit()
    return version.id


def _make_run(session, version_id: int) -> int:
    run = models.BacktestRun(
        strategy_version_id=version_id,
        symbol="NQ.c.0",
        name="evalrun",
        source="imported",
        status="completed",
    )
    session.add(run)
    session.commit()
    return run.id


def _add_trade(
    session,
    run_id: int,
    *,
    entry_ts: datetime,
    r: float,
    size: float = 1.0,
) -> int:
    trade = models.Trade(
        backtest_run_id=run_id,
        entry_ts=entry_ts,
        exit_ts=entry_ts + timedelta(minutes=10),
        symbol="NQ.c.0",
        side="long",
        entry_price=21000.0,
        exit_price=21010.0 if r > 0 else 20995.0,
        size=size,
        pnl=r * 10.0,  # arbitrary; not checked by evaluator
        r_multiple=r,
    )
    session.add(trade)
    session.commit()
    return trade.id


def _make_profile(
    session,
    *,
    name: str,
    max_daily_loss_r: float | None = None,
    max_drawdown_r: float | None = None,
    max_consecutive_losses: int | None = None,
    max_position_size: int | None = None,
    allowed_hours: list[int] | None = None,
) -> int:
    profile = models.RiskProfile(
        name=name,
        max_daily_loss_r=max_daily_loss_r,
        max_drawdown_r=max_drawdown_r,
        max_consecutive_losses=max_consecutive_losses,
        max_position_size=max_position_size,
        allowed_hours_json=serialize_allowed_hours(allowed_hours),
    )
    session.add(profile)
    session.commit()
    return profile.id


# --- happy paths ----------------------------------------------------------


def test_profile_with_no_caps_records_zero_violations(session) -> None:
    v_id = _make_strategy_version(session)
    run_id = _make_run(session, v_id)
    for r in (-1.0, -1.0, -1.0):
        _add_trade(session, run_id, entry_ts=datetime(2026, 4, 1, 14), r=r)
    p_id = _make_profile(session, name="None")

    evaluation = evaluate_profile(session, p_id, run_id)
    assert evaluation.total_trades_evaluated == 3
    assert evaluation.violations == []


def test_evaluation_handles_zero_trade_run(session) -> None:
    v_id = _make_strategy_version(session)
    run_id = _make_run(session, v_id)
    p_id = _make_profile(session, name="ZeroTrades", max_daily_loss_r=5.0)

    evaluation = evaluate_profile(session, p_id, run_id)
    assert evaluation.total_trades_evaluated == 0
    assert evaluation.violations == []


def test_missing_profile_raises_lookup_error(session) -> None:
    v_id = _make_strategy_version(session)
    run_id = _make_run(session, v_id)
    with pytest.raises(LookupError):
        evaluate_profile(session, 99999, run_id)


def test_missing_run_raises_lookup_error(session) -> None:
    p_id = _make_profile(session, name="X")
    with pytest.raises(LookupError):
        evaluate_profile(session, p_id, 99999)


# --- daily-loss cap -------------------------------------------------------


def test_daily_loss_cap_detected_at_breach_trade(session) -> None:
    v_id = _make_strategy_version(session)
    run_id = _make_run(session, v_id)
    # 3 losers on the same day (-1, -1, -3) — daily R reaches -5 on the
    # third trade; cap is 5 so only that trade triggers.
    base = datetime(2026, 4, 1, 14)
    _add_trade(session, run_id, entry_ts=base, r=-1.0)
    _add_trade(session, run_id, entry_ts=base + timedelta(hours=1), r=-1.0)
    third_id = _add_trade(
        session, run_id, entry_ts=base + timedelta(hours=2), r=-3.0
    )
    p_id = _make_profile(session, name="DL", max_daily_loss_r=5.0)

    evaluation = evaluate_profile(session, p_id, run_id)
    daily = [v for v in evaluation.violations if v.kind == "daily_loss"]
    assert len(daily) == 1
    assert daily[0].at_trade_id == third_id


def test_daily_loss_cap_resets_per_day(session) -> None:
    v_id = _make_strategy_version(session)
    run_id = _make_run(session, v_id)
    # Two days, each with a -5R day. Both should fire.
    for day in (1, 2):
        base = datetime(2026, 4, day, 14)
        _add_trade(session, run_id, entry_ts=base, r=-5.0)
    p_id = _make_profile(session, name="DL2", max_daily_loss_r=5.0)

    evaluation = evaluate_profile(session, p_id, run_id)
    daily = [v for v in evaluation.violations if v.kind == "daily_loss"]
    assert len(daily) == 2


# --- drawdown cap ---------------------------------------------------------


def test_drawdown_cap_detected(session) -> None:
    v_id = _make_strategy_version(session)
    run_id = _make_run(session, v_id)
    # Build 5R, then lose 6R -> drawdown 6R, cap is 5.
    base = datetime(2026, 4, 1, 14)
    _add_trade(session, run_id, entry_ts=base, r=5.0)
    bad_id = _add_trade(
        session, run_id, entry_ts=base + timedelta(hours=1), r=-6.0
    )
    p_id = _make_profile(session, name="DD", max_drawdown_r=5.0)

    evaluation = evaluate_profile(session, p_id, run_id)
    dd = [v for v in evaluation.violations if v.kind == "drawdown"]
    assert len(dd) >= 1
    assert dd[0].at_trade_id == bad_id


# --- consecutive losses ---------------------------------------------------


def test_consecutive_losses_cap_detected(session) -> None:
    v_id = _make_strategy_version(session)
    run_id = _make_run(session, v_id)
    base = datetime(2026, 4, 1, 14)
    # 4 losers in a row, cap is 3.
    last_id = None
    for i in range(4):
        last_id = _add_trade(
            session, run_id, entry_ts=base + timedelta(hours=i), r=-1.0
        )
    p_id = _make_profile(session, name="CL", max_consecutive_losses=3)

    evaluation = evaluate_profile(session, p_id, run_id)
    cl = [v for v in evaluation.violations if v.kind == "consecutive_losses"]
    assert len(cl) == 1  # fires on the 4th trade
    assert cl[0].at_trade_id == last_id


def test_consecutive_losses_resets_on_win(session) -> None:
    v_id = _make_strategy_version(session)
    run_id = _make_run(session, v_id)
    base = datetime(2026, 4, 1, 14)
    # 2 losers, win, 2 losers — cap=3 should NOT fire.
    for r in (-1.0, -1.0, +1.0, -1.0, -1.0):
        _add_trade(session, run_id, entry_ts=base, r=r)
        base += timedelta(hours=1)
    p_id = _make_profile(session, name="CL2", max_consecutive_losses=3)

    evaluation = evaluate_profile(session, p_id, run_id)
    cl = [v for v in evaluation.violations if v.kind == "consecutive_losses"]
    assert cl == []


# --- allowed hours --------------------------------------------------------


def test_allowed_hours_filter_flags_out_of_window_entries(session) -> None:
    v_id = _make_strategy_version(session)
    run_id = _make_run(session, v_id)
    # One trade at hour 10 (allowed), one at hour 18 (not).
    base = datetime(2026, 4, 1, 10)
    _add_trade(session, run_id, entry_ts=base, r=1.0)
    bad_id = _add_trade(
        session, run_id, entry_ts=base.replace(hour=18), r=1.0
    )
    p_id = _make_profile(session, name="HR", allowed_hours=[10, 11, 12])

    evaluation = evaluate_profile(session, p_id, run_id)
    hours = [v for v in evaluation.violations if v.kind == "hour_window"]
    assert len(hours) == 1
    assert hours[0].at_trade_id == bad_id


# --- position size --------------------------------------------------------


def test_position_size_cap_detected(session) -> None:
    v_id = _make_strategy_version(session)
    run_id = _make_run(session, v_id)
    base = datetime(2026, 4, 1, 14)
    _add_trade(session, run_id, entry_ts=base, r=1.0, size=1.0)
    bad_id = _add_trade(
        session, run_id, entry_ts=base + timedelta(hours=1), r=1.0, size=5.0
    )
    p_id = _make_profile(session, name="PS", max_position_size=2)

    evaluation = evaluate_profile(session, p_id, run_id)
    ps = [v for v in evaluation.violations if v.kind == "position_size"]
    assert len(ps) == 1
    assert ps[0].at_trade_id == bad_id
