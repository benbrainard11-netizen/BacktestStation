"""Tests for swing_pivot detector + reactions."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.db import models
from app.db.session import create_all, make_engine, make_session_factory
from app.research.detectors import get
from app.research.outcomes.swing_pivot_reactions import SwingPivotReactionsComputer
from app.research.scan import run_scan
from app.services.research_events import make_event_id

UTC = timezone.utc
NQ = "NQ.c.0"


@pytest.fixture
def session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = make_engine(f"sqlite:///{tmp_path / 'swing.sqlite'}")
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
        sliced = df.loc[(df.index >= s) & (df.index < e)].copy()
        if sliced.empty:
            return sliced
        return sliced.reset_index().rename(columns={"index": "ts_event"})


@pytest.fixture
def fake_reader() -> FakeBarReader:
    return FakeBarReader()


def _ohlc_frame(rows):
    return pd.DataFrame(
        [{"open": o, "high": h, "low": low, "close": c, "volume": 100}
         for _, o, h, low, c in rows],
        index=pd.DatetimeIndex([r[0] for r in rows], tz=UTC),
    )


def test_swing_high_pivot_fires(
    fake_reader: FakeBarReader,
    session_factory: sessionmaker[Session],
):
    """Bar with strict-max high in 7-bar window (3 left, 3 right) fires swing_high."""
    rows = []
    cur = datetime(2026, 5, 1, 0, tzinfo=UTC)
    # 3 left bars (lower highs), pivot bar (highest), 3 right bars (lower)
    pattern = [
        (100, 105, 99, 102),   # idx 0
        (102, 107, 101, 105),  # idx 1
        (105, 110, 103, 108),  # idx 2
        (108, 120, 107, 115),  # idx 3 — PIVOT (high=120)
        (115, 118, 113, 117),  # idx 4
        (117, 119, 115, 118),  # idx 5
        (118, 119, 116, 117),  # idx 6
        (117, 119, 115, 118),  # idx 7 — for outcomes lookforward
    ]
    for o, h, low_v, c in pattern:
        rows.append((cur, o, h, low_v, c))
        cur += timedelta(hours=1)
    fake_reader.set(symbol=NQ, timeframe="1h", df=_ohlc_frame(rows))

    with session_factory() as db:
        result = run_scan(
            detector_name="swing_pivot",
            symbols=[NQ],
            start=date(2026, 5, 1), end=date(2026, 5, 2),
            bar_reader=fake_reader, db=db, mode="pivot_3_1h",
        )
        db.commit()
    assert result.n_errors == 0, result.error_messages
    assert result.n_inserted >= 1


def test_no_pivot_fires_in_monotonic_uptrend(
    fake_reader: FakeBarReader,
    session_factory: sessionmaker[Session],
):
    rows = []
    cur = datetime(2026, 5, 1, 0, tzinfo=UTC)
    for i in range(15):
        rows.append((cur, 100 + i, 105 + i, 99 + i, 104 + i))
        cur += timedelta(hours=1)
    fake_reader.set(symbol=NQ, timeframe="1h", df=_ohlc_frame(rows))
    with session_factory() as db:
        result = run_scan(
            detector_name="swing_pivot",
            symbols=[NQ],
            start=date(2026, 5, 1), end=date(2026, 5, 2),
            bar_reader=fake_reader, db=db, mode="pivot_3_1h",
        )
        db.commit()
    assert result.n_errors == 0
    assert result.n_inserted == 0


def test_swing_pivot_reactions_breakout_and_thesis(fake_reader: FakeBarReader):
    """Synthetic swing high; forward bars break above the pivot."""
    pivot_ts = datetime(2026, 5, 4, 12, tzinfo=UTC)
    # Forward bars start at pivot_ts + (n+1)*tf_min = pivot_ts + 4h.
    forward_start = pivot_ts + timedelta(hours=4)
    bars = _ohlc_frame([
        (forward_start, 100, 105, 99, 103),
        (forward_start + timedelta(hours=1), 103, 108, 102, 107),
        (forward_start + timedelta(hours=2), 107, 112, 106, 110),  # wicks above pivot=110
        (forward_start + timedelta(hours=3), 110, 115, 109, 113),
    ])
    fake_reader.set(symbol=NQ, timeframe="1h", df=bars)
    event = models.ResearchEvent(
        event_id=make_event_id("swing_pivot", NQ, pivot_ts, "pivot_3_1h"),
        feature_name="swing_pivot",
        event_type="pivot_3_1h",
        bar_end_utc=pivot_ts.replace(tzinfo=None),
        primary_symbol=NQ, symbols=[NQ], timeframe="1H",
        side="high",
        event_data={
            "schema_version": 1, "detector_version": "v1",
            "n": 3, "tracking_timeframe": "1h", "side": "high",
            "pivot_price": 110.0,
            "pivot_bar": {"open": 105, "high": 110, "low": 104, "close": 108},
        },
        detector_version="v1",
    )
    out = SwingPivotReactionsComputer().compute(event, fake_reader)
    assert out is not None
    assert out["thesis_direction"] == "down"  # swing high → expect down
    bk = out["breakout"]
    # bar 3 (idx 3) high=112 > pivot 110 → wick taken at idx 3.
    assert bk["wick_taken"] is True
    # bar 3 close=110 → not strictly > 110, so close NOT taken on bar 3.
    # bar 4 close=113 > 110 → close taken on bar 4.
    assert bk["close_taken"] is True
    assert bk["bars_to_wick"] == 3


def test_detector_is_registered():
    d = get("swing_pivot")
    assert d.feature_name == "swing_pivot"
    assert "pivot_3_1h" in d.supported_modes


def test_outcomes_registered():
    from app.research.outcomes import get_by_feature
    c = get_by_feature("swing_pivot")
    assert c.outcome_version == "v1"
