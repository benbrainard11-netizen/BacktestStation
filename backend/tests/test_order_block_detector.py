"""Tests for the order_block detector."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import create_all, make_engine, make_session_factory
from app.research.detectors import DetectorContext, get
from app.research.detectors.order_block import (
    MAX_LOOKBACK_BARS,
    _find_confirmation,
    _find_ob_candle,
)
from app.research.scan import run_scan

UTC = timezone.utc
NQ = "NQ.c.0"


@pytest.fixture
def session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = make_engine(f"sqlite:///{tmp_path / 'ob.sqlite'}")
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


def _utc(year, month, day, hour=12, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=UTC)


def _ohlc_frame(rows):
    return pd.DataFrame(
        [{"open": o, "high": h, "low": low, "close": c, "volume": 100}
         for _, o, h, low, c in rows],
        index=pd.DatetimeIndex([r[0] for r in rows], tz=UTC),
    )


# ---------- unit tests for helpers ----------


def test_find_ob_candle_bullish_returns_most_recent_down_close():
    """Bullish setup: walk back from manipulation, find most recent down-close."""
    bars = pd.DataFrame([
        {"open": 100, "high": 105, "low": 95, "close": 102},   # idx 0: up-close
        {"open": 102, "high": 108, "low": 100, "close": 99},   # idx 1: DOWN-close ← expected
        {"open": 99, "high": 103, "low": 97, "close": 101},    # idx 2: up-close
        {"open": 101, "high": 105, "low": 96, "close": 102},   # idx 3: up-close = manipulation
    ])
    ob_iloc = _find_ob_candle(
        bars, manip_iloc=3, max_lookback=10, ob_side="bullish",
    )
    assert ob_iloc == 1


def test_find_ob_candle_bullish_returns_manipulation_if_down_close():
    """If the manipulation candle itself is down-close, return it."""
    bars = pd.DataFrame([
        {"open": 100, "high": 105, "low": 95, "close": 102},
        {"open": 102, "high": 105, "low": 96, "close": 99},  # manip + down-close
    ])
    ob_iloc = _find_ob_candle(
        bars, manip_iloc=1, max_lookback=10, ob_side="bullish",
    )
    assert ob_iloc == 1


def test_find_ob_candle_respects_lookback_cap():
    """Only walks back max_lookback bars; returns None if no down-close in window."""
    bars = pd.DataFrame([
        {"open": 100, "high": 105, "low": 95, "close": 99},   # idx 0: down-close (out of range)
        *[
            {"open": 100, "high": 105, "low": 95, "close": 102}  # idx 1-15: all up-closes
            for _ in range(15)
        ],
    ])
    # Lookback 10: from idx 15 we walk back to idx 5, no down-close → None.
    ob_iloc = _find_ob_candle(
        bars, manip_iloc=15, max_lookback=10, ob_side="bullish",
    )
    assert ob_iloc is None


def test_find_ob_candle_bearish_returns_most_recent_up_close():
    bars = pd.DataFrame([
        {"open": 100, "high": 105, "low": 95, "close": 99},   # down
        {"open": 99, "high": 102, "low": 98, "close": 101},   # UP-close ← expected
        {"open": 101, "high": 105, "low": 100, "close": 99},  # down
        {"open": 99, "high": 110, "low": 98, "close": 97},    # down (= manipulation)
    ])
    ob_iloc = _find_ob_candle(
        bars, manip_iloc=3, max_lookback=10, ob_side="bearish",
    )
    assert ob_iloc == 1


def test_find_confirmation_bullish_returns_first_close_above():
    """First bar whose close > confirmation_level (= body_bottom for bullish)."""
    bars = pd.DataFrame([
        {"open": 100, "high": 102, "low": 98, "close": 99},   # idx 0: close 99
        {"open": 99, "high": 101, "low": 97, "close": 100},   # idx 1: close 100 > 99 ✓
        {"open": 100, "high": 105, "low": 99, "close": 104},  # idx 2: also above
    ])
    iloc = _find_confirmation(
        bars, start_iloc=0, max_forward=10, confirmation_level=99.5,
        side="bullish",
    )
    assert iloc == 1


def test_find_confirmation_returns_none_if_no_close_passes():
    bars = pd.DataFrame([
        {"open": 100, "high": 102, "low": 98, "close": 99},
        {"open": 99, "high": 100, "low": 97, "close": 98},
    ])
    iloc = _find_confirmation(
        bars, start_iloc=0, max_forward=10, confirmation_level=99.5,
        side="bullish",
    )
    assert iloc is None


# ---------- end-to-end detector test ----------


def test_swept_pdl_1h_emits_event(
    fake_reader: FakeBarReader,
    session_factory: sessionmaker[Session],
):
    """Day N: PDL set in 1m bars. Day N+1: 1h candle wicks below PDL,
    OB is the down-close before, then a forward 1h candle closes above
    the OB body bottom → event fires.
    """
    # ---- prior period (day before scan range) — sets PDL ----
    # Globex day for 2026-05-05 = 2026-05-04 22:00 UTC → 2026-05-05 21:00 UTC
    # (18:00 ET = 22:00 UTC during DST). Prior day = 2026-05-04 day = 2026-05-03 22:00 → 2026-05-04 21:00.
    # We need 1m bars in the PRIOR Globex day with a known low.
    prior_start = datetime(2026, 5, 3, 22, 0, tzinfo=UTC)
    prior_low_ts = prior_start + timedelta(hours=2)
    one_min_bars = []
    # Fill with bars at price 21100 except one bar at 21050 (the low).
    cur = prior_start
    end_prior = datetime(2026, 5, 4, 21, 0, tzinfo=UTC)
    while cur < end_prior:
        if cur == prior_low_ts:
            one_min_bars.append((cur, 21100, 21105, 21050, 21100))  # low here
        else:
            one_min_bars.append((cur, 21100, 21105, 21099, 21100))
        cur += timedelta(minutes=1)
    fake_reader.set(symbol=NQ, timeframe="1m", df=_ohlc_frame(one_min_bars))

    # ---- current Globex day (2026-05-05) on 1h bars ----
    # Globex day for 2026-05-05 = 2026-05-04 22:00 UTC → 2026-05-05 21:00 UTC
    one_h_rows = []
    cur = datetime(2026, 5, 4, 22, 0, tzinfo=UTC)  # day start
    # Hours 0-2: above PDL, no sweep.
    one_h_rows.append((cur, 21100, 21110, 21080, 21105))           # bar 0
    cur += timedelta(hours=1)
    one_h_rows.append((cur, 21105, 21110, 21090, 21100))           # bar 1
    cur += timedelta(hours=1)
    # Bar 2: DOWN-CLOSE (the OB candidate).
    one_h_rows.append((cur, 21100, 21105, 21080, 21075))           # bar 2: down-close
    cur += timedelta(hours=1)
    # Bar 3: manipulation — wicks below PDL=21050.
    one_h_rows.append((cur, 21075, 21080, 21040, 21070))           # bar 3: sweep, up-close
    cur += timedelta(hours=1)
    # Bar 4: closes above OB body bottom (75) → laxest confirmation.
    one_h_rows.append((cur, 21070, 21090, 21060, 21085))           # bar 4: confirm
    cur += timedelta(hours=1)
    # Padding bars to satisfy buffer load.
    for _ in range(20):
        one_h_rows.append((cur, 21085, 21090, 21080, 21086))
        cur += timedelta(hours=1)

    fake_reader.set(symbol=NQ, timeframe="1h", df=_ohlc_frame(one_h_rows))

    with session_factory() as db:
        result = run_scan(
            detector_name="order_block",
            symbols=[NQ],
            start=date(2026, 5, 5), end=date(2026, 5, 6),
            bar_reader=fake_reader, db=db, mode="swept_pdl_1h",
        )
        db.commit()
    assert result.n_errors == 0, result.error_messages
    assert result.n_inserted == 1


def test_no_event_when_no_sweep(
    fake_reader: FakeBarReader,
    session_factory: sessionmaker[Session],
):
    """If no 1h candle wicks below PDL, no event."""
    prior_start = datetime(2026, 5, 3, 22, 0, tzinfo=UTC)
    one_min_bars = []
    cur = prior_start
    end_prior = datetime(2026, 5, 4, 21, 0, tzinfo=UTC)
    while cur < end_prior:
        one_min_bars.append((cur, 21100, 21105, 21050, 21100))
        cur += timedelta(minutes=1)
    fake_reader.set(symbol=NQ, timeframe="1m", df=_ohlc_frame(one_min_bars))

    one_h_rows = []
    cur = datetime(2026, 5, 4, 22, 0, tzinfo=UTC)
    for _ in range(24):
        # Always stay above PDL = 21050
        one_h_rows.append((cur, 21100, 21110, 21080, 21105))
        cur += timedelta(hours=1)
    fake_reader.set(symbol=NQ, timeframe="1h", df=_ohlc_frame(one_h_rows))

    with session_factory() as db:
        result = run_scan(
            detector_name="order_block",
            symbols=[NQ],
            start=date(2026, 5, 5), end=date(2026, 5, 6),
            bar_reader=fake_reader, db=db, mode="swept_pdl_1h",
        )
        db.commit()
    assert result.n_errors == 0
    assert result.n_inserted == 0


def test_detector_is_registered():
    d = get("order_block")
    assert d.feature_name == "order_block"
    assert "swept_pdl_1h" in d.supported_modes
    assert "swept_pwh_4h" in d.supported_modes
