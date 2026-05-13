"""Tests for time_profile detector."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import create_all, make_engine, make_session_factory
from app.research.detectors import get
from app.research.scan import run_scan

UTC = timezone.utc
NQ = "NQ.c.0"


@pytest.fixture
def session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = make_engine(f"sqlite:///{tmp_path / 'tp.sqlite'}")
    create_all(engine)
    return make_session_factory(engine)


class FakeBarReader:
    def __init__(self) -> None:
        self._frames: dict[tuple[str, str], pd.DataFrame] = {}

    def set(self, *, symbol: str, timeframe: str, df: pd.DataFrame) -> None:
        if df.index.tz is None:
            df = df.tz_localize(UTC)
        else:
            df = df.tz_convert(UTC)
        self._frames[(symbol, timeframe)] = df.sort_index()

    def __call__(self, *, symbol, timeframe, start, end, **kw):
        key = (symbol, timeframe)
        if key not in self._frames:
            raise FileNotFoundError(f"no bars for {symbol} {timeframe}")
        df = self._frames[key]
        s = pd.Timestamp(start)
        e = pd.Timestamp(end)
        if s.tz is None:
            s = s.tz_localize(UTC)
        if e.tz is None:
            e = e.tz_localize(UTC)
        return df.loc[(df.index >= s) & (df.index < e)].copy()


@pytest.fixture
def fake_reader() -> FakeBarReader:
    return FakeBarReader()


def _ohlc_frame(rows):
    return pd.DataFrame(
        [{"open": o, "high": h, "low": low, "close": c, "volume": 100}
         for _, o, h, low, c in rows],
        index=pd.DatetimeIndex([r[0] for r in rows], tz=UTC),
    )


def test_daily_3session_fires_with_full_day_data(
    fake_reader: FakeBarReader,
    session_factory: sessionmaker[Session],
):
    """Full Globex day of 1m bars → daily_3session event fires once."""
    day_start = datetime(2026, 5, 4, 22, 0, tzinfo=UTC)
    rows = []
    cur = day_start
    # 23 hours of 1m bars; vary the price to give the period a range.
    for i in range(23 * 60):
        # Make a low early, high late, so we get low_first.
        price = 21000 + i * 0.1
        rows.append((cur, price, price + 5, price - 5, price + 2))
        cur += timedelta(minutes=1)
    fake_reader.set(symbol=NQ, timeframe="1m", df=_ohlc_frame(rows))

    with session_factory() as db:
        result = run_scan(
            detector_name="time_profile",
            symbols=[NQ],
            start=date(2026, 5, 5), end=date(2026, 5, 6),
            bar_reader=fake_reader, db=db, mode="daily_3session",
        )
        db.commit()
    assert result.n_errors == 0, result.error_messages
    assert result.n_inserted >= 1


def test_detector_is_registered():
    d = get("time_profile")
    assert d.feature_name == "time_profile"
    assert "daily_3session" in d.supported_modes
    assert "daily_4session" in d.supported_modes
    assert "weekly" in d.supported_modes
    assert "monthly" in d.supported_modes


def test_4session_has_more_sub_periods_than_3session():
    """daily_4session subdivides NY into AM/PM, so it has more sub-periods."""
    from app.research.detectors.time_profile import _build_sub_periods
    from app.research.sessions import GlobexPeriod

    parent = GlobexPeriod(
        start_utc=datetime(2026, 5, 4, 22, 0, tzinfo=UTC),
        end_utc=datetime(2026, 5, 5, 21, 0, tzinfo=UTC),
        label="globex_day",
    )
    sub_3 = _build_sub_periods(parent, "daily_3session")
    sub_4 = _build_sub_periods(parent, "daily_4session")
    assert len(sub_3) == 3
    assert len(sub_4) == 4
    labels_3 = [s.label for s in sub_3]
    labels_4 = [s.label for s in sub_4]
    assert labels_3 == ["asia", "london", "ny"]
    assert labels_4 == ["asia", "london", "ny_am", "ny_pm"]
