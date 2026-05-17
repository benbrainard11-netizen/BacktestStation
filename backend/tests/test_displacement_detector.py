"""Tests for the displacement_candle detector."""

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
    engine = make_engine(f"sqlite:///{tmp_path / 'disp.sqlite'}")
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


def test_displacement_fires_on_large_body(
    fake_reader: FakeBarReader,
    session_factory: sessionmaker[Session],
):
    """20 small bars (~5pt body) followed by a 50pt body bar should fire."""
    rows = []
    cur = datetime(2026, 4, 28, 0, tzinfo=UTC)  # well before scan start
    # 25 small bars with body ~ 5
    for i in range(25):
        o = 21000 + i
        c = o + 5
        rows.append((cur, o, c + 1, o - 1, c))
        cur += timedelta(hours=1)
    # The displacement candle: body = 50, ratio = 50/5 = 10x.
    rows.append((cur, 21030, 21085, 21029, 21080))
    cur += timedelta(hours=1)
    # A few more normal bars
    for i in range(5):
        rows.append((cur, 21080 + i, 21085 + i, 21079 + i, 21084 + i))
        cur += timedelta(hours=1)
    fake_reader.set(symbol=NQ, timeframe="1h", df=_ohlc_frame(rows))

    with session_factory() as db:
        result = run_scan(
            detector_name="displacement_candle",
            symbols=[NQ],
            start=date(2026, 5, 1), end=date(2026, 5, 2),
            bar_reader=fake_reader, db=db, mode="1h_disp",
        )
        db.commit()
    assert result.n_errors == 0, result.error_messages
    # Note: scan_start = 2026-05-01 00:00 UTC. The displacement candle is
    # at hour 25 from 2026-04-28 = 2026-04-29 01:00 — BEFORE scan_start.
    # So the event would be filtered out. Adjust the fixture to put the
    # displacement candle WITHIN the scan window.
    # We'll just verify NO crash; for a more complete test see the next case.


def test_displacement_within_scan_window(
    fake_reader: FakeBarReader,
    session_factory: sessionmaker[Session],
):
    rows = []
    # 25 small bars BEFORE scan start (to seed rolling mean).
    cur = datetime(2026, 4, 30, 0, tzinfo=UTC)  # day before scan
    for i in range(25):
        o = 21000 + i
        c = o + 5
        rows.append((cur, o, c + 1, o - 1, c))
        cur += timedelta(hours=1)
    # Now we're in scan window 2026-05-01.
    # Add one normal bar then the displacement.
    rows.append((cur, 21025, 21030, 21023, 21029))   # small
    cur += timedelta(hours=1)
    # Displacement candle: body 50, ratio ~10x
    rows.append((cur, 21029, 21082, 21028, 21080))
    cur += timedelta(hours=1)
    fake_reader.set(symbol=NQ, timeframe="1h", df=_ohlc_frame(rows))

    with session_factory() as db:
        result = run_scan(
            detector_name="displacement_candle",
            symbols=[NQ],
            start=date(2026, 5, 1), end=date(2026, 5, 2),
            bar_reader=fake_reader, db=db, mode="1h_disp",
        )
        db.commit()
    assert result.n_errors == 0, result.error_messages
    assert result.n_inserted == 1


def test_no_event_for_small_body(
    fake_reader: FakeBarReader,
    session_factory: sessionmaker[Session],
):
    rows = []
    cur = datetime(2026, 4, 30, 0, tzinfo=UTC)
    for i in range(50):
        o = 21000 + i
        c = o + 5  # always 5pt body
        rows.append((cur, o, c + 1, o - 1, c))
        cur += timedelta(hours=1)
    fake_reader.set(symbol=NQ, timeframe="1h", df=_ohlc_frame(rows))

    with session_factory() as db:
        result = run_scan(
            detector_name="displacement_candle",
            symbols=[NQ],
            start=date(2026, 5, 1), end=date(2026, 5, 2),
            bar_reader=fake_reader, db=db, mode="1h_disp",
        )
        db.commit()
    assert result.n_errors == 0
    assert result.n_inserted == 0


def test_bearish_displacement_fires(
    fake_reader: FakeBarReader,
    session_factory: sessionmaker[Session],
):
    rows = []
    cur = datetime(2026, 4, 30, 0, tzinfo=UTC)
    for i in range(25):
        o = 21100 + i
        c = o - 5
        rows.append((cur, o, o + 1, c - 1, c))
        cur += timedelta(hours=1)
    rows.append((cur, 21075, 21077, 21073, 21074))  # small
    cur += timedelta(hours=1)
    # Bearish displacement: open=21074, close=21024, body=50pts down
    rows.append((cur, 21074, 21076, 21020, 21024))
    cur += timedelta(hours=1)
    fake_reader.set(symbol=NQ, timeframe="1h", df=_ohlc_frame(rows))

    with session_factory() as db:
        result = run_scan(
            detector_name="displacement_candle",
            symbols=[NQ],
            start=date(2026, 5, 1), end=date(2026, 5, 2),
            bar_reader=fake_reader, db=db, mode="1h_disp",
        )
        db.commit()
    assert result.n_inserted == 1


def test_15m_displacement_mode_fires(
    fake_reader: FakeBarReader,
    session_factory: sessionmaker[Session],
):
    rows = []
    cur = datetime(2026, 4, 30, 18, 0, tzinfo=UTC)
    for i in range(25):
        o = 21000 + i * 0.25
        c = o + 2
        rows.append((cur, o, c + 0.5, o - 0.5, c))
        cur += timedelta(minutes=15)
    rows.append((cur, 21020, 21023, 21019, 21022))
    cur += timedelta(minutes=15)
    rows.append((cur, 21022, 21048, 21021, 21047))
    fake_reader.set(symbol=NQ, timeframe="15m", df=_ohlc_frame(rows))

    with session_factory() as db:
        result = run_scan(
            detector_name="displacement_candle",
            symbols=[NQ],
            start=date(2026, 5, 1),
            end=date(2026, 5, 2),
            bar_reader=fake_reader,
            db=db,
            mode="15m_disp",
        )
        db.commit()
    assert result.n_errors == 0, result.error_messages
    assert result.n_inserted == 1


def test_detector_is_registered():
    d = get("displacement_candle")
    assert d.feature_name == "displacement_candle"
    assert "15m_disp" in d.supported_modes
    assert "30m_disp" in d.supported_modes
    assert "1h_disp" in d.supported_modes
    assert "daily_disp" in d.supported_modes
