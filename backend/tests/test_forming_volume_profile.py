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
    engine = make_engine(f"sqlite:///{tmp_path / 'forming_vp.sqlite'}")
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


def _forming_day_bars() -> pd.DataFrame:
    day_start = datetime(2026, 5, 4, 22, 0, tzinfo=UTC)
    rows = []
    cur = day_start
    for i in range(23 * 60):
        if i < 240:
            price = 100.0 + (i % 20) * 0.1
            high = price + 1.0
        elif i < 300:
            price = 130.0
            high = 140.0
        else:
            price = 160.0
            high = 1000.0 if i == 600 else 162.0
        rows.append(
            {
                "open": price,
                "high": high,
                "low": price - 1.0,
                "close": price,
                "volume": 100 + i,
            }
        )
        cur += timedelta(minutes=1)
    return pd.DataFrame(rows, index=pd.date_range(day_start, periods=len(rows), freq="1min"))


def test_forming_vp_detector_excludes_future_bars(
    session_factory: sessionmaker[Session],
):
    reader = FakeBarReader()
    reader.set(symbol=NQ, timeframe="1m", df=_forming_day_bars())

    with session_factory() as db:
        result = run_scan(
            detector_name="forming_volume_profile",
            symbols=[NQ],
            start=date(2026, 5, 5),
            end=date(2026, 5, 6),
            bar_reader=reader,
            db=db,
            mode="daily_vp_asof_4h",
        )
        db.commit()
        rows = list(
            db.scalars(
                select(ResearchEvent)
                .where(ResearchEvent.feature_name == "forming_volume_profile")
                .order_by(ResearchEvent.bar_end_utc)
            )
        )

    assert result.n_errors == 0, result.error_messages
    assert result.n_inserted == 5
    first = rows[0]
    assert first.event_data["asof_ts_utc"] == "2026-05-05T02:00:00+00:00"
    assert first.event_data["profile_high_so_far"] < 200.0
    assert first.event_data["profile_high_so_far"] != 1000.0


def test_forming_vp_outcomes_use_future_from_asof(
    session_factory: sessionmaker[Session],
):
    reader = FakeBarReader()
    reader.set(symbol=NQ, timeframe="1m", df=_forming_day_bars())

    with session_factory() as db:
        run_scan(
            detector_name="forming_volume_profile",
            symbols=[NQ],
            start=date(2026, 5, 5),
            end=date(2026, 5, 6),
            bar_reader=reader,
            db=db,
            mode="daily_vp_asof_4h",
        )
        computer = get_outcome("forming_volume_profile_reactions_v1")
        result = run_outcomes(computer=computer, bar_reader=reader, db=db, force=True)
        db.commit()
        first = db.scalar(
            select(ResearchEvent)
            .where(ResearchEvent.feature_name == "forming_volume_profile")
            .order_by(ResearchEvent.bar_end_utc)
        )

    assert result.n_errors == 0, result.error_messages
    assert result.n_updated == 5
    assert first is not None
    assert first.outcomes["next_60m"]["forward_high"] == 140.0
    assert first.outcomes["rest_of_day"]["forward_high"] == 1000.0
    assert first.outcomes["next_60m"]["forward_high"] < first.outcomes["rest_of_day"]["forward_high"]


def test_forming_vp_detector_is_registered():
    d = get("forming_volume_profile")
    assert d.feature_name == "forming_volume_profile"
    assert "daily_vp_asof_1h" in d.supported_modes
    assert "daily_vp_asof_4h" in d.supported_modes
