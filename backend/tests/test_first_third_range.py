"""Tests for first_third_range detector."""

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
    engine = make_engine(f"sqlite:///{tmp_path / 'ft.sqlite'}")
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


def test_first_third_daily_fires(
    fake_reader: FakeBarReader,
    session_factory: sessionmaker[Session],
):
    """A full Globex day of 1m bars → daily first-third event fires."""
    # Globex day starts 18:00 ET (22:00 UTC during DST) and is 23h long.
    day_start = datetime(2026, 5, 4, 22, 0, tzinfo=UTC)
    rows = []
    cur = day_start
    # 23 hours of 1m bars.
    for _ in range(23 * 60):
        rows.append((cur, 21000, 21010, 20990, 21005))
        cur += timedelta(minutes=1)
    fake_reader.set(symbol=NQ, timeframe="1m", df=_ohlc_frame(rows))

    with session_factory() as db:
        result = run_scan(
            detector_name="first_third_range",
            symbols=[NQ],
            start=date(2026, 5, 5), end=date(2026, 5, 6),
            bar_reader=fake_reader, db=db, mode="first_third_daily",
        )
        db.commit()
    assert result.n_errors == 0, result.error_messages
    assert result.n_inserted >= 1


def test_detector_is_registered():
    d = get("first_third_range")
    assert d.feature_name == "first_third_range"
    assert "first_third_daily" in d.supported_modes
    assert "first_third_weekly" in d.supported_modes
