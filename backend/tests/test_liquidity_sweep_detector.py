"""Tests for the liquidity_sweep detector."""

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
    engine = make_engine(f"sqlite:///{tmp_path / 'sweep.sqlite'}")
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


def test_pdl_sweep_fires_event(
    fake_reader: FakeBarReader,
    session_factory: sessionmaker[Session],
):
    """Day N has a low; day N+1 wicks below it → sweep fires."""
    # Prior Globex day = 2026-05-04 22:00 → 2026-05-05 21:00 UTC.
    # Set a clear low at 21050 in 1m bars.
    prior_start = datetime(2026, 5, 3, 22, 0, tzinfo=UTC)
    end_prior = datetime(2026, 5, 4, 21, 0, tzinfo=UTC)
    bars_1m = []
    cur = prior_start
    while cur < end_prior:
        if cur == prior_start + timedelta(hours=2):
            bars_1m.append((cur, 21100, 21105, 21050, 21100))
        else:
            bars_1m.append((cur, 21100, 21105, 21099, 21100))
        cur += timedelta(minutes=1)
    fake_reader.set(symbol=NQ, timeframe="1m", df=_ohlc_frame(bars_1m))

    # Current Globex day on 1h: bar 3 wicks below 21050.
    one_h = []
    cur = datetime(2026, 5, 4, 22, 0, tzinfo=UTC)
    one_h.append((cur, 21100, 21110, 21080, 21105)); cur += timedelta(hours=1)
    one_h.append((cur, 21105, 21110, 21090, 21100)); cur += timedelta(hours=1)
    one_h.append((cur, 21100, 21105, 21080, 21075)); cur += timedelta(hours=1)
    one_h.append((cur, 21075, 21080, 21040, 21070)); cur += timedelta(hours=1)  # sweep
    one_h.append((cur, 21070, 21090, 21060, 21085)); cur += timedelta(hours=1)
    fake_reader.set(symbol=NQ, timeframe="1h", df=_ohlc_frame(one_h))

    with session_factory() as db:
        result = run_scan(
            detector_name="liquidity_sweep",
            symbols=[NQ],
            start=date(2026, 5, 5), end=date(2026, 5, 6),
            bar_reader=fake_reader, db=db, mode="pdl_1h",
        )
        db.commit()
    assert result.n_errors == 0, result.error_messages
    assert result.n_inserted == 1


def test_no_sweep_no_event(
    fake_reader: FakeBarReader,
    session_factory: sessionmaker[Session],
):
    """If no candle wicks below PDL, no event fires."""
    prior_start = datetime(2026, 5, 3, 22, 0, tzinfo=UTC)
    end_prior = datetime(2026, 5, 4, 21, 0, tzinfo=UTC)
    bars_1m = []
    cur = prior_start
    while cur < end_prior:
        bars_1m.append((cur, 21100, 21105, 21050, 21100))
        cur += timedelta(minutes=1)
    fake_reader.set(symbol=NQ, timeframe="1m", df=_ohlc_frame(bars_1m))

    one_h = []
    cur = datetime(2026, 5, 4, 22, 0, tzinfo=UTC)
    for _ in range(24):
        one_h.append((cur, 21100, 21110, 21080, 21105))
        cur += timedelta(hours=1)
    fake_reader.set(symbol=NQ, timeframe="1h", df=_ohlc_frame(one_h))

    with session_factory() as db:
        result = run_scan(
            detector_name="liquidity_sweep",
            symbols=[NQ],
            start=date(2026, 5, 5), end=date(2026, 5, 6),
            bar_reader=fake_reader, db=db, mode="pdl_1h",
        )
        db.commit()
    assert result.n_errors == 0
    assert result.n_inserted == 0


def test_pdh_sweep_fires(
    fake_reader: FakeBarReader,
    session_factory: sessionmaker[Session],
):
    """Bearish-side: high gets taken."""
    prior_start = datetime(2026, 5, 3, 22, 0, tzinfo=UTC)
    end_prior = datetime(2026, 5, 4, 21, 0, tzinfo=UTC)
    bars_1m = []
    cur = prior_start
    while cur < end_prior:
        # Set high=21150 at hour 2.
        if cur == prior_start + timedelta(hours=2):
            bars_1m.append((cur, 21100, 21150, 21099, 21100))
        else:
            bars_1m.append((cur, 21100, 21105, 21099, 21100))
        cur += timedelta(minutes=1)
    fake_reader.set(symbol=NQ, timeframe="1m", df=_ohlc_frame(bars_1m))

    one_h = []
    cur = datetime(2026, 5, 4, 22, 0, tzinfo=UTC)
    one_h.append((cur, 21100, 21130, 21090, 21125)); cur += timedelta(hours=1)
    one_h.append((cur, 21125, 21165, 21110, 21130)); cur += timedelta(hours=1)  # sweep PDH=21150
    fake_reader.set(symbol=NQ, timeframe="1h", df=_ohlc_frame(one_h))

    with session_factory() as db:
        result = run_scan(
            detector_name="liquidity_sweep",
            symbols=[NQ],
            start=date(2026, 5, 5), end=date(2026, 5, 6),
            bar_reader=fake_reader, db=db, mode="pdh_1h",
        )
        db.commit()
    assert result.n_errors == 0
    assert result.n_inserted == 1


def test_detector_is_registered():
    d = get("liquidity_sweep")
    assert d.feature_name == "liquidity_sweep"
    assert "pdl_1h" in d.supported_modes
    assert "pwh_daily" in d.supported_modes
