"""Tests for volume_profile detector (different from the older
_volume_profile feature tests in test_volume_profile.py)."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import create_all, make_engine, make_session_factory
from app.research.detectors import get
from app.research.detectors.volume_profile import _value_area
from app.research.scan import run_scan

UTC = timezone.utc
NQ = "NQ.c.0"


@pytest.fixture
def session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = make_engine(f"sqlite:///{tmp_path / 'vp.sqlite'}")
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
        [{"open": o, "high": h, "low": low, "close": c, "volume": v}
         for _, o, h, low, c, v in rows],
        index=pd.DatetimeIndex([r[0] for r in rows], tz=UTC),
    )


def test_value_area_expansion_simple():
    """Synthetic 7-bin distribution centered on bin 3.
    Total = 1000. 70% target = 700.
    Bins: [10, 50, 200, 400, 200, 100, 40]
    Start at POC (bin 3, 400). Iteratively add larger neighbor:
      - cumulative=400. neighbors: 200 (left bin 2), 200 (right bin 4). tie → above.
      - add bin 4. cumulative=600. neighbors: 200 (bin 2), 100 (bin 5). above < below
        actually 100 < 200, so add LEFT (bin 2 has 200). cumulative=800. DONE.
      val_idx=2, vah_idx=4."""
    bins = np.array([10, 50, 200, 400, 200, 100, 40], dtype=float)
    val, vah = _value_area(bins, poc_idx=3, total_volume=1000.0, target_pct=0.7)
    assert vah - val >= 2  # at least 3 bins
    # POC must be inside
    assert val <= 3 <= vah


def test_daily_volume_profile_fires(
    fake_reader: FakeBarReader,
    session_factory: sessionmaker[Session],
):
    """Full Globex day of 1m bars with varying prices → daily VP fires."""
    day_start = datetime(2026, 5, 4, 22, 0, tzinfo=UTC)
    rows = []
    cur = day_start
    for i in range(23 * 60):
        price = 21000 + (i % 100) * 0.5  # cycle prices to populate bins
        rows.append((cur, price, price + 5, price - 5, price + 2, 100 + i))
        cur += timedelta(minutes=1)
    fake_reader.set(symbol=NQ, timeframe="1m", df=_ohlc_frame(rows))

    with session_factory() as db:
        result = run_scan(
            detector_name="volume_profile",
            symbols=[NQ],
            start=date(2026, 5, 5), end=date(2026, 5, 6),
            bar_reader=fake_reader, db=db, mode="daily_volume_profile",
        )
        db.commit()
    assert result.n_errors == 0, result.error_messages
    assert result.n_inserted >= 1


def test_detector_is_registered():
    d = get("volume_profile")
    assert d.feature_name == "volume_profile"
    assert "daily_volume_profile" in d.supported_modes
    assert "weekly_volume_profile" in d.supported_modes
    assert "asia_volume_profile" in d.supported_modes
    assert "london_volume_profile" in d.supported_modes
    assert "ny_volume_profile" in d.supported_modes
