"""Tests for the FVG formation detector."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import create_all, make_engine, make_session_factory
from app.research import detectors as detector_registry
from app.research.detectors import DetectorContext
from app.research.scan import run_scan

UTC = timezone.utc

NQ = "NQ.c.0"
ES = "ES.c.0"


@pytest.fixture
def session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = make_engine(f"sqlite:///{tmp_path / 'fvg.sqlite'}")
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


def _ohlc_frame(rows: list[tuple[datetime, float, float, float, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        [{"open": o, "high": h, "low": l, "close": c, "volume": 100}
         for _, o, h, l, c in rows],
        index=pd.DatetimeIndex([r[0] for r in rows], tz=UTC),
    )


# ---------- detection cases ----------


def test_bullish_fvg_fires(
    fake_reader: FakeBarReader,
    session_factory: sessionmaker[Session],
):
    """candle1.high < candle3.low → bullish FVG."""
    t1 = _utc(2026, 5, 4, 12, 0)
    t2 = _utc(2026, 5, 4, 13, 0)
    t3 = _utc(2026, 5, 4, 14, 0)
    fake_reader.set(symbol=NQ, timeframe="1h", df=_ohlc_frame([
        (t1, 21000, 21010, 20990, 21005),  # high 21010
        (t2, 21010, 21030, 21010, 21025),  # the impulse candle
        (t3, 21025, 21040, 21015, 21035),  # low 21015 > c1.high 21010
    ]))

    with session_factory() as db:
        result = run_scan(
            detector_name="fvg_formation",
            symbols=[NQ], start=date(2026, 5, 4), end=date(2026, 5, 5),
            bar_reader=fake_reader, db=db, mode="1h_fvg",
        )
        db.commit()
    assert result.n_errors == 0, result.error_messages
    assert result.n_inserted == 1


def test_bearish_fvg_fires(
    fake_reader: FakeBarReader,
    session_factory: sessionmaker[Session],
):
    t1 = _utc(2026, 5, 4, 12, 0)
    t2 = _utc(2026, 5, 4, 13, 0)
    t3 = _utc(2026, 5, 4, 14, 0)
    fake_reader.set(symbol=NQ, timeframe="1h", df=_ohlc_frame([
        (t1, 21000, 21010, 20990, 20995),  # low 20990
        (t2, 20995, 20998, 20970, 20975),  # the impulse candle (down)
        (t3, 20975, 20985, 20960, 20965),  # high 20985 < c1.low 20990
    ]))

    with session_factory() as db:
        result = run_scan(
            detector_name="fvg_formation",
            symbols=[NQ], start=date(2026, 5, 4), end=date(2026, 5, 5),
            bar_reader=fake_reader, db=db, mode="1h_fvg",
        )
        db.commit()
    assert result.n_inserted == 1


def test_no_event_when_candles_overlap(
    fake_reader: FakeBarReader,
    session_factory: sessionmaker[Session],
):
    """Normal range candles, no gap between c1 and c3."""
    t1 = _utc(2026, 5, 4, 12, 0)
    t2 = _utc(2026, 5, 4, 13, 0)
    t3 = _utc(2026, 5, 4, 14, 0)
    fake_reader.set(symbol=NQ, timeframe="1h", df=_ohlc_frame([
        (t1, 21000, 21020, 20990, 21015),
        (t2, 21015, 21030, 21010, 21020),
        (t3, 21020, 21025, 21015, 21022),  # low 21015 < c1.high 21020 → no gap
    ]))

    with session_factory() as db:
        result = run_scan(
            detector_name="fvg_formation",
            symbols=[NQ], start=date(2026, 5, 4), end=date(2026, 5, 5),
            bar_reader=fake_reader, db=db, mode="1h_fvg",
        )
        db.commit()
    assert result.n_inserted == 0


def test_event_data_shape(fake_reader: FakeBarReader):
    t1 = _utc(2026, 5, 4, 12, 0)
    t2 = _utc(2026, 5, 4, 13, 0)
    t3 = _utc(2026, 5, 4, 14, 0)
    fake_reader.set(symbol=NQ, timeframe="1h", df=_ohlc_frame([
        (t1, 21000, 21010, 20990, 21005),
        (t2, 21010, 21030, 21010, 21025),
        (t3, 21025, 21040, 21015, 21035),
    ]))

    detector = detector_registry.get("fvg_formation")
    events = detector.scan(DetectorContext(
        symbols=[NQ], start=date(2026, 5, 4), end=date(2026, 5, 5),
        bar_reader=fake_reader, mode="1h_fvg",
    ))
    assert len(events) == 1
    e = events[0]
    assert e.feature_name == "fvg_formation"
    assert e.event_type == "1h_fvg"
    assert e.timeframe == "1H"
    assert e.side == "bullish"
    assert e.primary_symbol == NQ
    d = e.event_data
    assert d["direction"] == "bullish"
    assert d["fvg_low"] == pytest.approx(21010.0)   # c1.high
    assert d["fvg_high"] == pytest.approx(21015.0)  # c3.low
    assert d["fvg_mid"] == pytest.approx(21012.5)
    assert d["fvg_width_pts"] == pytest.approx(5.0)
    assert d["candle_1"]["high"] == pytest.approx(21010.0)
    assert d["candle_3"]["low"] == pytest.approx(21015.0)


def test_per_symbol_independent_detection(
    fake_reader: FakeBarReader,
    session_factory: sessionmaker[Session],
):
    """Each symbol's FVGs are detected independently — NQ has a gap,
    ES doesn't, only one event fires."""
    t1 = _utc(2026, 5, 4, 12, 0)
    t2 = _utc(2026, 5, 4, 13, 0)
    t3 = _utc(2026, 5, 4, 14, 0)
    fake_reader.set(symbol=NQ, timeframe="1h", df=_ohlc_frame([
        (t1, 21000, 21010, 20990, 21005),
        (t2, 21010, 21030, 21010, 21025),
        (t3, 21025, 21040, 21015, 21035),  # bullish FVG
    ]))
    fake_reader.set(symbol=ES, timeframe="1h", df=_ohlc_frame([
        (t1, 5000, 5010, 4995, 5005),
        (t2, 5005, 5015, 5000, 5010),
        (t3, 5010, 5020, 5005, 5015),  # no gap
    ]))

    with session_factory() as db:
        result = run_scan(
            detector_name="fvg_formation",
            symbols=[NQ, ES], start=date(2026, 5, 4), end=date(2026, 5, 5),
            bar_reader=fake_reader, db=db, mode="1h_fvg",
        )
        db.commit()
    assert result.n_inserted == 1


def test_full_rescan_idempotent(
    fake_reader: FakeBarReader,
    session_factory: sessionmaker[Session],
):
    t1 = _utc(2026, 5, 4, 12, 0)
    t2 = _utc(2026, 5, 4, 13, 0)
    t3 = _utc(2026, 5, 4, 14, 0)
    fake_reader.set(symbol=NQ, timeframe="1h", df=_ohlc_frame([
        (t1, 21000, 21010, 20990, 21005),
        (t2, 21010, 21030, 21010, 21025),
        (t3, 21025, 21040, 21015, 21035),
    ]))

    with session_factory() as db:
        first = run_scan(
            detector_name="fvg_formation",
            symbols=[NQ], start=date(2026, 5, 4), end=date(2026, 5, 5),
            bar_reader=fake_reader, db=db, mode="1h_fvg",
        )
        db.commit()
        second = run_scan(
            detector_name="fvg_formation",
            symbols=[NQ], start=date(2026, 5, 4), end=date(2026, 5, 5),
            bar_reader=fake_reader, db=db, mode="1h_fvg",
        )
        db.commit()
    assert first.n_inserted == 1
    assert second.n_inserted == 0
    assert second.n_skipped_duplicate == 1


def test_unsupported_mode_rejected(
    fake_reader: FakeBarReader,
    session_factory: sessionmaker[Session],
):
    with session_factory() as db:
        with pytest.raises(ValueError, match="does not support mode"):
            run_scan(
                detector_name="fvg_formation",
                symbols=[NQ], start=date(2026, 5, 4), end=date(2026, 5, 5),
                bar_reader=fake_reader, db=db, mode="weekly_fvg",
            )


def test_short_frame_no_events(fake_reader: FakeBarReader):
    """Less than 3 bars → no possible FVG."""
    t1 = _utc(2026, 5, 4, 12, 0)
    t2 = _utc(2026, 5, 4, 13, 0)
    fake_reader.set(symbol=NQ, timeframe="1h", df=_ohlc_frame([
        (t1, 21000, 21010, 20990, 21005),
        (t2, 21010, 21030, 21010, 21025),
    ]))
    detector = detector_registry.get("fvg_formation")
    events = detector.scan(DetectorContext(
        symbols=[NQ], start=date(2026, 5, 4), end=date(2026, 5, 5),
        bar_reader=fake_reader, mode="1h_fvg",
    ))
    assert events == []


def test_detector_is_registered():
    names = detector_registry.list_names()
    assert "fvg_formation" in names
    d = detector_registry.get("fvg_formation")
    assert d.feature_name == "fvg_formation"
    assert d.detector_version == "v1"
    assert "daily_fvg" in d.supported_modes
    assert "4h_fvg" in d.supported_modes
    assert "1h_fvg" in d.supported_modes
