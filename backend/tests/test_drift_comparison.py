"""Tests for the Forward Drift Monitor service + API endpoints."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import models
from app.db.session import (
    create_all,
    get_session,
    make_engine,
    make_session_factory,
)
from app.main import app
from app.services.drift_comparison import (
    DEFAULT_WR_WINDOW,
    compute_drift_for_strategy,
    compute_entry_time_drift,
    compute_win_rate_drift,
)


# --- Fixtures ------------------------------------------------------------


@pytest.fixture
def session(tmp_path: Path) -> Session:
    engine = make_engine(f"sqlite:///{tmp_path / 'drift.sqlite'}")
    create_all(engine)
    SessionLocal = make_session_factory(engine)
    with SessionLocal() as s:
        yield s


def _make_strategy_and_version(session: Session) -> models.StrategyVersion:
    strategy = models.Strategy(name="Drift Test", slug="drift-test", status="testing")
    version = models.StrategyVersion(version="1.0", strategy=strategy)
    session.add(strategy)
    session.commit()
    session.refresh(version)
    return version


def _make_run(
    session: Session,
    version: models.StrategyVersion,
    *,
    source: str,
    name: str | None = None,
) -> models.BacktestRun:
    run = models.BacktestRun(
        strategy_version_id=version.id,
        symbol="NQ.c.0",
        name=name or f"{source}-run",
        source=source,
        status="completed",
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


def _add_trades(
    session: Session,
    run: models.BacktestRun,
    *,
    count: int,
    win_pct: float,
    base_hour_utc: int = 14,
    minute_step: int = 17,
    start_day: int = 1,
) -> list[models.Trade]:
    """Append `count` trades with the given win-rate.

    Wins get pnl=+100, losses get pnl=-50. Entry timestamps are spread
    across multiple days starting at `base_hour_utc` so that hour-of-day
    histograms are easy to control.
    """
    win_count = int(round(count * win_pct))
    trades: list[models.Trade] = []
    for i in range(count):
        is_win = i < win_count
        ts = datetime(2026, 4, start_day, base_hour_utc, 0, 0) + timedelta(
            minutes=minute_step * i
        )
        trade = models.Trade(
            backtest_run_id=run.id,
            entry_ts=ts,
            exit_ts=ts + timedelta(minutes=10),
            symbol="NQ.c.0",
            side="long",
            entry_price=21000.0,
            exit_price=21010.0 if is_win else 20995.0,
            size=1.0,
            pnl=100.0 if is_win else -50.0,
        )
        trades.append(trade)
        session.add(trade)
    session.commit()
    return trades


# --- baseline_run_id column migration ------------------------------------


def test_strategy_version_has_baseline_run_id_column(tmp_path: Path) -> None:
    """The ALTER in _run_data_migrations adds the column on existing DBs."""
    from sqlalchemy import inspect

    engine = make_engine(f"sqlite:///{tmp_path / 'cols.sqlite'}")
    create_all(engine)
    cols = {c["name"] for c in inspect(engine).get_columns("strategy_versions")}
    assert "baseline_run_id" in cols


def test_baseline_run_id_can_be_set_and_cleared(session: Session) -> None:
    version = _make_strategy_and_version(session)
    baseline = _make_run(session, version, source="imported")
    version.baseline_run_id = baseline.id
    session.commit()
    session.refresh(version)
    assert version.baseline_run_id == baseline.id

    version.baseline_run_id = None
    session.commit()
    session.refresh(version)
    assert version.baseline_run_id is None


# --- Win-rate drift ------------------------------------------------------


def test_wr_drift_matching_distributions_is_ok(session: Session) -> None:
    version = _make_strategy_and_version(session)
    baseline = _make_run(session, version, source="imported")
    live = _make_run(session, version, source="live")
    _add_trades(session, baseline, count=DEFAULT_WR_WINDOW, win_pct=0.55)
    _add_trades(session, live, count=DEFAULT_WR_WINDOW, win_pct=0.55)

    result = compute_win_rate_drift(session, live, baseline)
    assert result.signal_type == "win_rate"
    assert result.status == "OK"
    assert abs((result.deviation or 0.0)) < 1.0
    assert result.sample_size_live == DEFAULT_WR_WINDOW
    assert result.sample_size_baseline == DEFAULT_WR_WINDOW
    assert not result.incomplete


def test_wr_drift_warn_on_large_deviation(session: Session) -> None:
    version = _make_strategy_and_version(session)
    baseline = _make_run(session, version, source="imported")
    live = _make_run(session, version, source="live")
    _add_trades(session, baseline, count=DEFAULT_WR_WINDOW, win_pct=0.60)
    _add_trades(session, live, count=DEFAULT_WR_WINDOW, win_pct=0.30)

    result = compute_win_rate_drift(session, live, baseline)
    assert result.status == "WARN"
    assert result.deviation is not None
    assert result.deviation < 0  # live is below baseline


def test_wr_drift_watch_on_moderate_deviation(session: Session) -> None:
    version = _make_strategy_and_version(session)
    baseline = _make_run(session, version, source="imported")
    live = _make_run(session, version, source="live")
    _add_trades(session, baseline, count=DEFAULT_WR_WINDOW, win_pct=0.60)
    _add_trades(session, live, count=DEFAULT_WR_WINDOW, win_pct=0.50)

    result = compute_win_rate_drift(session, live, baseline)
    assert result.status == "WATCH"


def test_wr_drift_zero_live_trades_warns(session: Session) -> None:
    version = _make_strategy_and_version(session)
    baseline = _make_run(session, version, source="imported")
    live = _make_run(session, version, source="live")
    _add_trades(session, baseline, count=DEFAULT_WR_WINDOW, win_pct=0.55)
    # No trades on live.

    result = compute_win_rate_drift(session, live, baseline)
    assert result.status == "WARN"
    assert result.live_value is None
    assert result.sample_size_live == 0
    assert result.incomplete


def test_wr_drift_partial_window_marks_incomplete(session: Session) -> None:
    version = _make_strategy_and_version(session)
    baseline = _make_run(session, version, source="imported")
    live = _make_run(session, version, source="live")
    _add_trades(session, baseline, count=DEFAULT_WR_WINDOW, win_pct=0.55)
    # Only 5 live trades — well below the 20-trade window.
    _add_trades(session, live, count=5, win_pct=0.60)

    result = compute_win_rate_drift(session, live, baseline)
    assert result.incomplete is True
    # 5pp delta with incomplete sample → at minimum WATCH (never OK).
    assert result.status in {"WATCH", "WARN"}


# --- Entry-time drift ----------------------------------------------------


def test_entry_time_drift_matching_distributions_is_ok(session: Session) -> None:
    version = _make_strategy_and_version(session)
    baseline = _make_run(session, version, source="imported")
    live = _make_run(session, version, source="live")
    # Both at the same hour — distributions identical.
    _add_trades(session, baseline, count=10, win_pct=0.5, base_hour_utc=14)
    _add_trades(session, live, count=10, win_pct=0.5, base_hour_utc=14)

    result = compute_entry_time_drift(session, live, baseline)
    assert result.signal_type == "entry_time"
    assert result.status == "OK"


def test_entry_time_drift_divergent_distributions_warn(session: Session) -> None:
    version = _make_strategy_and_version(session)
    baseline = _make_run(session, version, source="imported")
    live = _make_run(session, version, source="live")
    # Baseline trades all at 14 UTC; live trades all at 02 UTC — totally
    # different distributions. minute_step kept inside one hour bucket.
    _add_trades(
        session, baseline, count=20, win_pct=0.5, base_hour_utc=14, minute_step=2
    )
    _add_trades(session, live, count=20, win_pct=0.5, base_hour_utc=2, minute_step=2)

    result = compute_entry_time_drift(session, live, baseline, recent_n=20)
    assert result.status == "WARN"
    assert result.deviation is not None
    assert result.deviation < 0.01


def test_entry_time_drift_small_sample_is_watch(session: Session) -> None:
    version = _make_strategy_and_version(session)
    baseline = _make_run(session, version, source="imported")
    live = _make_run(session, version, source="live")
    _add_trades(session, baseline, count=10, win_pct=0.5, base_hour_utc=14)
    _add_trades(session, live, count=2, win_pct=0.5, base_hour_utc=14)

    result = compute_entry_time_drift(session, live, baseline)
    assert result.status == "WATCH"
    assert result.incomplete is True
    assert "insufficient sample" in result.message.lower()


# --- Composite -----------------------------------------------------------


def test_compute_drift_for_strategy_resolves_baseline_and_live(
    session: Session,
) -> None:
    version = _make_strategy_and_version(session)
    baseline = _make_run(session, version, source="imported")
    live = _make_run(session, version, source="live")
    _add_trades(session, baseline, count=20, win_pct=0.6)
    _add_trades(session, live, count=20, win_pct=0.6)
    version.baseline_run_id = baseline.id
    session.commit()

    comparison = compute_drift_for_strategy(session, version.id)
    assert comparison.baseline_run_id == baseline.id
    assert comparison.live_run_id == live.id
    signals = {r.signal_type for r in comparison.results}
    assert signals == {"win_rate", "entry_time"}


def test_compute_drift_no_baseline_raises(session: Session) -> None:
    version = _make_strategy_and_version(session)
    with pytest.raises(LookupError):
        compute_drift_for_strategy(session, version.id)


def test_compute_drift_no_live_run_returns_warn_results(session: Session) -> None:
    version = _make_strategy_and_version(session)
    baseline = _make_run(session, version, source="imported")
    _add_trades(session, baseline, count=20, win_pct=0.6)
    version.baseline_run_id = baseline.id
    session.commit()

    comparison = compute_drift_for_strategy(session, version.id)
    assert comparison.live_run_id is None
    assert all(r.status == "WARN" for r in comparison.results)


# --- API endpoints -------------------------------------------------------


@pytest.fixture
def api_client(tmp_path: Path):
    """A FastAPI client wired to a fresh sqlite DB so endpoint tests don't
    leak state into the real meta DB."""
    engine = make_engine(f"sqlite:///{tmp_path / 'api.sqlite'}")
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
            yield client, SessionLocal
    finally:
        app.dependency_overrides.pop(get_session, None)


def test_set_baseline_endpoint_happy_path(api_client) -> None:
    client, SessionLocal = api_client
    with SessionLocal() as s:
        version = _make_strategy_and_version(s)
        baseline = _make_run(s, version, source="imported")
        version_id = version.id
        baseline_id = baseline.id

    response = client.patch(
        f"/api/strategy-versions/{version_id}/baseline",
        json={"run_id": baseline_id},
    )
    assert response.status_code == 200, response.text
    assert response.json()["baseline_run_id"] == baseline_id


def test_set_baseline_rejects_live_run(api_client) -> None:
    client, SessionLocal = api_client
    with SessionLocal() as s:
        version = _make_strategy_and_version(s)
        live = _make_run(s, version, source="live")
        version_id = version.id
        live_id = live.id

    response = client.patch(
        f"/api/strategy-versions/{version_id}/baseline",
        json={"run_id": live_id},
    )
    assert response.status_code == 422
    assert "live" in response.json()["detail"].lower()


def test_set_baseline_clears_when_null(api_client) -> None:
    client, SessionLocal = api_client
    with SessionLocal() as s:
        version = _make_strategy_and_version(s)
        baseline = _make_run(s, version, source="imported")
        version.baseline_run_id = baseline.id
        s.commit()
        version_id = version.id

    response = client.patch(
        f"/api/strategy-versions/{version_id}/baseline",
        json={"run_id": None},
    )
    assert response.status_code == 200
    assert response.json()["baseline_run_id"] is None


def test_drift_endpoint_returns_comparison(api_client) -> None:
    client, SessionLocal = api_client
    with SessionLocal() as s:
        version = _make_strategy_and_version(s)
        baseline = _make_run(s, version, source="imported")
        live = _make_run(s, version, source="live")
        _add_trades(s, baseline, count=20, win_pct=0.55)
        _add_trades(s, live, count=20, win_pct=0.55)
        version.baseline_run_id = baseline.id
        s.commit()
        version_id = version.id
        baseline_id = baseline.id
        live_id = live.id

    response = client.get(f"/api/monitor/drift/{version_id}")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["strategy_version_id"] == version_id
    assert body["baseline_run_id"] == baseline_id
    assert body["live_run_id"] == live_id
    signal_types = {r["signal_type"] for r in body["results"]}
    assert signal_types == {"win_rate", "entry_time"}


def test_drift_endpoint_404_when_no_baseline(api_client) -> None:
    client, SessionLocal = api_client
    with SessionLocal() as s:
        version = _make_strategy_and_version(s)
        version_id = version.id

    response = client.get(f"/api/monitor/drift/{version_id}")
    assert response.status_code == 404
