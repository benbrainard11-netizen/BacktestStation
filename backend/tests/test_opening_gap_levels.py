from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import ResearchEvent
from app.db.session import create_all, make_engine, make_session_factory
from app.research.detectors import get
from app.research.outcomes import get as get_outcome
from app.research.outcomes.runner import run_outcomes
from app.research.scan import run_scan

UTC = timezone.utc
NQ = "NQ.c.0"


@pytest.fixture
def session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = make_engine(f"sqlite:///{tmp_path / 'opening_gap.sqlite'}")
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


def _ohlc_frame(rows):
    return pd.DataFrame(
        [{"open": o, "high": h, "low": low, "close": c, "volume": 100}
         for _, o, h, low, c in rows],
        index=pd.DatetimeIndex([r[0] for r in rows], tz=UTC),
    )


def _daily_gap_bars() -> pd.DataFrame:
    rows = []
    # Previous Globex day for 2026-05-05 starts 2026-05-03 22:00 UTC
    cur = datetime(2026, 5, 3, 22, 0, tzinfo=UTC)
    while cur < datetime(2026, 5, 4, 21, 0, tzinfo=UTC):
        rows.append((cur, 100.0, 101.0, 99.0, 100.0))
        cur += timedelta(minutes=1)
    # New day opens 10 points higher, then fills the gap.
    cur = datetime(2026, 5, 4, 22, 0, tzinfo=UTC)
    for i in range(300):
        price = 110.0 if i < 60 else 105.0 if i < 120 else 99.0
        rows.append((cur, price, price + 1.0, price - 1.0, price))
        cur += timedelta(minutes=1)
    return _ohlc_frame(rows)


def test_ndog_detector_fires_gap_event(session_factory: sessionmaker[Session]):
    reader = FakeBarReader()
    reader.set(symbol=NQ, timeframe="1m", df=_daily_gap_bars())

    with session_factory() as db:
        result = run_scan(
            detector_name="opening_gap_levels",
            symbols=[NQ],
            start=date(2026, 5, 5),
            end=date(2026, 5, 6),
            bar_reader=reader,
            db=db,
            mode="ndog",
        )
        db.commit()
        row = db.scalar(select(ResearchEvent).where(ResearchEvent.feature_name == "opening_gap_levels"))

    assert result.n_errors == 0, result.error_messages
    assert result.n_inserted == 1
    assert row is not None
    assert row.event_type == "ndog"
    assert row.side == "gap_up"
    assert row.event_data["gap_high"] == 110.0
    assert row.event_data["gap_low"] == 100.0
    assert row.event_data["gap_mid"] == 105.0


def test_opening_gap_outcome_finds_fill(session_factory: sessionmaker[Session]):
    reader = FakeBarReader()
    reader.set(symbol=NQ, timeframe="1m", df=_daily_gap_bars())

    with session_factory() as db:
        run_scan(
            detector_name="opening_gap_levels",
            symbols=[NQ],
            start=date(2026, 5, 5),
            end=date(2026, 5, 6),
            bar_reader=reader,
            db=db,
            mode="ndog",
        )
        result = run_outcomes(
            computer=get_outcome("opening_gap_reactions_v1"),
            bar_reader=reader,
            db=db,
            force=True,
        )
        db.commit()
        row = db.scalar(select(ResearchEvent).where(ResearchEvent.feature_name == "opening_gap_levels"))

    assert result.n_errors == 0, result.error_messages
    assert result.n_updated == 1
    assert row is not None
    assert row.outcomes["next_240m"]["touched_gap"] is True
    assert row.outcomes["next_240m"]["touched_midpoint"] is True
    assert row.outcomes["next_240m"]["fully_filled"] is True


def test_opening_gap_detector_is_registered():
    d = get("opening_gap_levels")
    assert d.feature_name == "opening_gap_levels"
    assert "ndog" in d.supported_modes
    assert "nwog" in d.supported_modes
