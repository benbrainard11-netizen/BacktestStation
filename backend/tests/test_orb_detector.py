"""Tests for opening_range_breakout detector."""

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
    engine = make_engine(f"sqlite:///{tmp_path / 'orb.sqlite'}")
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


def test_orb_ny_30m_fires(
    fake_reader: FakeBarReader,
    session_factory: sessionmaker[Session],
):
    """30 minutes of 1m bars at NY open → ORB event fires."""
    # 09:30 ET = 13:30 UTC (during DST)
    open_utc = datetime(2026, 5, 4, 13, 30, tzinfo=UTC)
    rows = []
    cur = open_utc
    for i in range(60):  # full hour
        rows.append((cur, 21000 + i * 0.1, 21010 + i * 0.1, 20990 + i * 0.1, 21005 + i * 0.1))
        cur += timedelta(minutes=1)
    fake_reader.set(symbol=NQ, timeframe="1m", df=_ohlc_frame(rows))

    with session_factory() as db:
        result = run_scan(
            detector_name="opening_range_breakout",
            symbols=[NQ],
            start=date(2026, 5, 4), end=date(2026, 5, 5),
            bar_reader=fake_reader, db=db, mode="ny_30m",
        )
        db.commit()
    assert result.n_errors == 0, result.error_messages
    assert result.n_inserted >= 1


def test_detector_is_registered():
    d = get("opening_range_breakout")
    assert d.feature_name == "opening_range_breakout"
    assert "ny_5m" in d.supported_modes
    assert "ny_15m" in d.supported_modes
    assert "ny_30m" in d.supported_modes
    assert "asia_60m" in d.supported_modes
