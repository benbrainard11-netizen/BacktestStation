"""Data quality endpoint tests.

Uses synthetic parquet fixtures so tests don't depend on the
C:\\Fractal-AMD data archive being present in CI or other machines.
"""

from collections.abc import Generator
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.db import models
from app.db.session import create_all, get_session, make_engine, make_session_factory
from app.main import app


@pytest.fixture
def session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = make_engine(f"sqlite:///{tmp_path / 'dq.sqlite'}")
    create_all(engine)
    return make_session_factory(engine)


@pytest.fixture
def client(session_factory: sessionmaker[Session]) -> Generator[TestClient, None, None]:
    def override_get_session() -> Generator[Session, None, None]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def fake_fractal_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Path:
    """Point the backend at a tmp dir mimicking C:\\Fractal-AMD\\data\\."""
    root = tmp_path / "fractal"
    (root / "raw").mkdir(parents=True)
    (root / "l2").mkdir(parents=True)
    monkeypatch.setenv("FRACTAL_DATA_ROOT", str(root))
    return root


def _write_synthetic_ohlcv(
    root: Path,
    symbol: str,
    start: datetime,
    end: datetime,
    minute_step: int = 1,
    skip_ranges: list[tuple[datetime, datetime]] | None = None,
) -> None:
    """Write a fake 2022-2025 parquet with clean 1-min bars."""
    skip_ranges = skip_ranges or []
    index = pd.date_range(
        start=pd.Timestamp(start, tz="America/New_York"),
        end=pd.Timestamp(end, tz="America/New_York"),
        freq=f"{minute_step}min",
        inclusive="left",
    )
    # Apply skip ranges.
    keep_mask = pd.Series(True, index=index)
    for s, e in skip_ranges:
        keep_mask &= ~(
            (index >= pd.Timestamp(s, tz="America/New_York"))
            & (index < pd.Timestamp(e, tz="America/New_York"))
        )
    index = index[keep_mask]

    df = pd.DataFrame(
        {
            "open": 21000.0,
            "high": 21001.0,
            "low": 20999.0,
            "close": 21000.5,
            "volume": 100,
        },
        index=index,
    )
    path = root / "raw" / f"{symbol}.c.0_ohlcv-1m_2022_2025.parquet"
    df.to_parquet(path)


def _seed_run(
    factory: sessionmaker[Session],
    symbol: str = "NQ",
    start: datetime = datetime(2024, 3, 1, 10, 0),
    end: datetime = datetime(2024, 3, 1, 16, 0),
    trades: list[datetime] | None = None,
) -> int:
    with factory() as session:
        strategy = models.Strategy(name="T", slug="t")
        version = models.StrategyVersion(strategy=strategy, version="v1")
        run = models.BacktestRun(
            strategy_version=version,
            symbol=symbol,
            import_source="test",
            start_ts=start,
            end_ts=end,
        )
        for ts in trades or []:
            run.trades.append(
                models.Trade(
                    entry_ts=ts,
                    symbol=symbol,
                    side="long",
                    entry_price=21000.0,
                    size=1.0,
                )
            )
        session.add(strategy)
        session.commit()
        return run.id


def test_data_quality_clean_dataset_high_score(
    client: TestClient,
    session_factory: sessionmaker[Session],
    fake_fractal_root: Path,
) -> None:
    _write_synthetic_ohlcv(
        fake_fractal_root,
        "NQ",
        start=datetime(2024, 2, 28, 0, 0),
        end=datetime(2024, 3, 2, 0, 0),
    )
    run_id = _seed_run(
        session_factory,
        trades=[datetime(2024, 3, 1, 10, 30), datetime(2024, 3, 1, 14, 0)],
    )

    response = client.get(f"/api/backtests/{run_id}/data-quality")
    assert response.status_code == 200
    body = response.json()
    assert body["backtest_run_id"] == run_id
    assert body["symbol"] == "NQ"
    assert body["dataset_status"] == "ok"
    assert body["total_bars"] > 0
    assert body["reliability_score"] >= 90
    assert body["issues"] == []
    assert len(body["deferred_checks"]) == 3


def test_data_quality_missing_candles_near_entries(
    client: TestClient,
    session_factory: sessionmaker[Session],
    fake_fractal_root: Path,
) -> None:
    # Build a dataset with a gap around 10:30.
    _write_synthetic_ohlcv(
        fake_fractal_root,
        "NQ",
        start=datetime(2024, 2, 28, 0, 0),
        end=datetime(2024, 3, 2, 0, 0),
        skip_ranges=[(datetime(2024, 3, 1, 10, 15), datetime(2024, 3, 1, 10, 45))],
    )
    run_id = _seed_run(
        session_factory, trades=[datetime(2024, 3, 1, 10, 30)]
    )

    body = client.get(f"/api/backtests/{run_id}/data-quality").json()
    assert body["reliability_score"] < 100
    cats = [i["category"] for i in body["issues"]]
    assert "missing_bars_near_entry" in cats
    # The "missing bars" issue should be counted at least once.
    missing = next(
        i for i in body["issues"] if i["category"] == "missing_bars_near_entry"
    )
    assert missing["count"] >= 1


def test_data_quality_missing_symbol_returns_high_severity(
    client: TestClient,
    session_factory: sessionmaker[Session],
    fake_fractal_root: Path,
) -> None:
    # Don't write any parquet files.
    run_id = _seed_run(session_factory, symbol="MISSING")

    body = client.get(f"/api/backtests/{run_id}/data-quality").json()
    assert body["dataset_status"] == "missing"
    assert body["reliability_score"] == 0
    assert any(i["category"] == "candles_missing" for i in body["issues"])


def test_data_quality_404_for_missing_run(client: TestClient) -> None:
    response = client.get("/api/backtests/9999/data-quality")
    assert response.status_code == 404
