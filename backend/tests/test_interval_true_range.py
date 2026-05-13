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
    engine = make_engine(f"sqlite:///{tmp_path / 'itr.sqlite'}")
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


def _three_globex_days() -> pd.DataFrame:
    rows = []
    specs = [
        (datetime(2026, 5, 4, 22, 0, tzinfo=UTC), 100.0, 105.0, 95.0, 102.0),
        (datetime(2026, 5, 5, 22, 0, tzinfo=UTC), 102.0, 112.0, 100.0, 110.0),
        (datetime(2026, 5, 6, 22, 0, tzinfo=UTC), 110.0, 120.0, 98.0, 116.0),
    ]
    for start, open_v, high_v, low_v, close_v in specs:
        cur = start
        for i in range(23 * 60):
            frac = i / (23 * 60 - 1)
            price = open_v + frac * (close_v - open_v)
            high = max(price + 0.25, high_v if i == 100 else price + 0.25)
            low = min(price - 0.25, low_v if i == 200 else price - 0.25)
            rows.append((cur, price, high, low, price))
            cur += timedelta(minutes=1)
    return _ohlc_frame(rows)


def test_daily_itr_detector_fires(session_factory: sessionmaker[Session]):
    reader = FakeBarReader()
    reader.set(symbol=NQ, timeframe="1m", df=_three_globex_days())

    with session_factory() as db:
        result = run_scan(
            detector_name="interval_true_range",
            symbols=[NQ],
            start=date(2026, 5, 6),
            end=date(2026, 5, 7),
            bar_reader=reader,
            db=db,
            mode="daily_itr",
        )
        db.commit()
        row = db.scalar(
            select(ResearchEvent).where(ResearchEvent.feature_name == "interval_true_range")
        )

    assert result.n_errors == 0, result.error_messages
    assert result.n_inserted >= 1
    assert row is not None
    assert row.event_type == "daily_itr"
    assert row.event_data["interval_range_pts"] > 0
    assert row.event_data["prev_interval_range_pts"] is not None
    assert row.event_data["next_interval_start_utc"] is not None


def test_itr_outcome_labels_next_interval(session_factory: sessionmaker[Session]):
    reader = FakeBarReader()
    reader.set(symbol=NQ, timeframe="1m", df=_three_globex_days())

    with session_factory() as db:
        run_scan(
            detector_name="interval_true_range",
            symbols=[NQ],
            start=date(2026, 5, 6),
            end=date(2026, 5, 7),
            bar_reader=reader,
            db=db,
            mode="daily_itr",
        )
        result = run_outcomes(
            computer=get_outcome("interval_true_range_reactions_v1"),
            bar_reader=reader,
            db=db,
            force=True,
        )
        db.commit()
        row = db.scalar(
            select(ResearchEvent).where(ResearchEvent.feature_name == "interval_true_range")
        )

    assert result.n_errors == 0, result.error_messages
    assert result.n_updated >= 1
    assert row is not None
    assert row.outcomes["next_interval"]["took_interval_high"] is True
    assert row.outcomes["next_interval"]["took_interval_low"] is True
    assert row.outcomes["next_interval"]["swept_both_sides"] is True


def test_session_itr_detector_and_registration(session_factory: sessionmaker[Session]):
    reader = FakeBarReader()
    reader.set(symbol=NQ, timeframe="1m", df=_three_globex_days())
    with session_factory() as db:
        result = run_scan(
            detector_name="interval_true_range",
            symbols=[NQ],
            start=date(2026, 5, 6),
            end=date(2026, 5, 7),
            bar_reader=reader,
            db=db,
            mode="asia_itr",
        )
    assert result.n_errors == 0, result.error_messages
    d = get("interval_true_range")
    assert d.feature_name == "interval_true_range"
    assert {"daily_itr", "weekly_itr", "asia_itr", "london_itr", "ny_itr"}.issubset(
        set(d.supported_modes)
    )
