"""Tests for the PSP (Precision Swing Point) candle divergence detector."""

from __future__ import annotations

from collections.abc import Generator
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
YM = "YM.c.0"
SYMBOLS = [NQ, ES, YM]


@pytest.fixture
def session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = make_engine(f"sqlite:///{tmp_path / 'psp.sqlite'}")
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


def _ohlc_one_candle(ts: datetime, *, o: float, h: float, l: float, c: float) -> pd.DataFrame:
    return pd.DataFrame(
        [{"open": o, "high": h, "low": l, "close": c, "volume": 100}],
        index=pd.DatetimeIndex([ts], tz=UTC),
    )


def _ohlc_frame(rows: list[tuple[datetime, float, float, float, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        [{"open": o, "high": h, "low": l, "close": c, "volume": 100}
         for _, o, h, l, c in rows],
        index=pd.DatetimeIndex([r[0] for r in rows], tz=UTC),
    )


# ---------- detection cases ----------


def test_one_vs_two_split_fires_event(
    fake_reader: FakeBarReader,
    session_factory: sessionmaker[Session],
):
    """NQ closes bullish, ES + YM close bearish on the same 4H candle.
    PSP fires; primary_symbol = NQ (the lone diverger)."""
    ts = _utc(2026, 5, 4, 12, 0)
    fake_reader.set(symbol=NQ, timeframe="4h", df=_ohlc_one_candle(
        ts, o=21000, h=21020, l=20990, c=21015,  # bullish
    ))
    fake_reader.set(symbol=ES, timeframe="4h", df=_ohlc_one_candle(
        ts, o=5000, h=5005, l=4985, c=4990,  # bearish
    ))
    fake_reader.set(symbol=YM, timeframe="4h", df=_ohlc_one_candle(
        ts, o=40000, h=40020, l=39950, c=39960,  # bearish
    ))

    with session_factory() as db:
        result = run_scan(
            detector_name="psp_candle_divergence",
            symbols=SYMBOLS,
            start=date(2026, 5, 4),
            end=date(2026, 5, 5),
            bar_reader=fake_reader,
            db=db,
            mode="4h_psp",
        )
        db.commit()

    assert result.n_errors == 0, result.error_messages
    assert result.n_inserted == 1


def test_event_data_shape(fake_reader: FakeBarReader):
    """The event payload should carry per-symbol direction, body, and
    minority/majority groupings."""
    ts = _utc(2026, 5, 4, 12, 0)
    fake_reader.set(symbol=NQ, timeframe="4h", df=_ohlc_one_candle(
        ts, o=21000, h=21020, l=20990, c=21015,
    ))
    fake_reader.set(symbol=ES, timeframe="4h", df=_ohlc_one_candle(
        ts, o=5000, h=5005, l=4985, c=4990,
    ))
    fake_reader.set(symbol=YM, timeframe="4h", df=_ohlc_one_candle(
        ts, o=40000, h=40020, l=39950, c=39960,
    ))

    detector = detector_registry.get("psp_candle_divergence")
    events = detector.scan(DetectorContext(
        symbols=SYMBOLS, start=date(2026, 5, 4), end=date(2026, 5, 5),
        bar_reader=fake_reader, mode="4h_psp",
    ))
    assert len(events) == 1
    e = events[0]
    assert e.feature_name == "psp_candle_divergence"
    assert e.event_type == "4h_psp"
    assert e.timeframe == "4H"
    assert e.side == "bullish"  # minority direction
    assert e.primary_symbol == NQ  # alphabetically-first minority

    d = e.event_data
    assert d["minority_direction"] == "bullish"
    assert d["minority_symbols"] == [NQ]
    assert sorted(d["majority_symbols"]) == sorted([ES, YM])
    assert d["bullish_symbols"] == [NQ]
    assert sorted(d["bearish_symbols"]) == sorted([ES, YM])
    assert d["per_symbol_states"][NQ]["direction"] == "bullish"
    assert d["per_symbol_states"][NQ]["body_pts"] == pytest.approx(15.0)
    assert d["per_symbol_states"][ES]["direction"] == "bearish"


def test_no_event_when_all_bullish(
    fake_reader: FakeBarReader,
    session_factory: sessionmaker[Session],
):
    ts = _utc(2026, 5, 4, 12, 0)
    for sym, base in [(NQ, 21000), (ES, 5000), (YM, 40000)]:
        fake_reader.set(symbol=sym, timeframe="4h", df=_ohlc_one_candle(
            ts, o=base, h=base + 20, l=base - 10, c=base + 15,  # bullish
        ))

    with session_factory() as db:
        result = run_scan(
            detector_name="psp_candle_divergence",
            symbols=SYMBOLS,
            start=date(2026, 5, 4), end=date(2026, 5, 5),
            bar_reader=fake_reader, db=db, mode="4h_psp",
        )
        db.commit()
    assert result.n_inserted == 0


def test_no_event_when_all_bearish(
    fake_reader: FakeBarReader,
    session_factory: sessionmaker[Session],
):
    ts = _utc(2026, 5, 4, 12, 0)
    for sym, base in [(NQ, 21000), (ES, 5000), (YM, 40000)]:
        fake_reader.set(symbol=sym, timeframe="4h", df=_ohlc_one_candle(
            ts, o=base, h=base + 5, l=base - 20, c=base - 15,  # bearish
        ))

    with session_factory() as db:
        result = run_scan(
            detector_name="psp_candle_divergence",
            symbols=SYMBOLS,
            start=date(2026, 5, 4), end=date(2026, 5, 5),
            bar_reader=fake_reader, db=db, mode="4h_psp",
        )
        db.commit()
    assert result.n_inserted == 0


def test_doji_skips_candle(fake_reader: FakeBarReader):
    """If any symbol is a doji (close == open), v1 skips the candle."""
    ts = _utc(2026, 5, 4, 12, 0)
    fake_reader.set(symbol=NQ, timeframe="4h", df=_ohlc_one_candle(
        ts, o=21000, h=21020, l=20990, c=21015,  # bullish
    ))
    fake_reader.set(symbol=ES, timeframe="4h", df=_ohlc_one_candle(
        ts, o=5000, h=5005, l=4995, c=5000,  # doji
    ))
    fake_reader.set(symbol=YM, timeframe="4h", df=_ohlc_one_candle(
        ts, o=40000, h=40020, l=39950, c=39960,  # bearish
    ))
    detector = detector_registry.get("psp_candle_divergence")
    events = detector.scan(DetectorContext(
        symbols=SYMBOLS, start=date(2026, 5, 4), end=date(2026, 5, 5),
        bar_reader=fake_reader, mode="4h_psp",
    ))
    assert len(events) == 0


def test_bear_minority_primary_is_alphabetical(fake_reader: FakeBarReader):
    """When the minority is bearish and contains multiple symbols (with
    >3 symbol setups), primary_symbol is alphabetically-first."""
    ts = _utc(2026, 5, 4, 12, 0)
    # ES + NQ bullish, YM alone bearish — minority = YM
    fake_reader.set(symbol=NQ, timeframe="4h", df=_ohlc_one_candle(
        ts, o=21000, h=21020, l=20990, c=21015,  # bullish
    ))
    fake_reader.set(symbol=ES, timeframe="4h", df=_ohlc_one_candle(
        ts, o=5000, h=5020, l=4990, c=5015,  # bullish
    ))
    fake_reader.set(symbol=YM, timeframe="4h", df=_ohlc_one_candle(
        ts, o=40000, h=40005, l=39950, c=39960,  # bearish
    ))
    detector = detector_registry.get("psp_candle_divergence")
    events = detector.scan(DetectorContext(
        symbols=SYMBOLS, start=date(2026, 5, 4), end=date(2026, 5, 5),
        bar_reader=fake_reader, mode="4h_psp",
    ))
    assert len(events) == 1
    assert events[0].primary_symbol == YM
    assert events[0].side == "bearish"


def test_only_common_timestamps_evaluated(fake_reader: FakeBarReader):
    """If one symbol's 4H frame is missing some timestamps, those
    candles are skipped — direction comparison requires data for all
    symbols."""
    t1 = _utc(2026, 5, 4, 12, 0)
    t2 = _utc(2026, 5, 4, 16, 0)
    nq = _ohlc_frame([
        (t1, 21000, 21020, 20990, 21015),  # bullish
        (t2, 21015, 21030, 21000, 21005),  # bearish
    ])
    es = _ohlc_frame([
        (t1, 5000, 5005, 4985, 4990),  # bearish
        # t2 missing — skipped
    ])
    ym = _ohlc_frame([
        (t1, 40000, 40020, 39950, 39960),  # bearish
        (t2, 39960, 39990, 39950, 39980),  # bullish
    ])
    fake_reader.set(symbol=NQ, timeframe="4h", df=nq)
    fake_reader.set(symbol=ES, timeframe="4h", df=es)
    fake_reader.set(symbol=YM, timeframe="4h", df=ym)

    detector = detector_registry.get("psp_candle_divergence")
    events = detector.scan(DetectorContext(
        symbols=SYMBOLS, start=date(2026, 5, 4), end=date(2026, 5, 5),
        bar_reader=fake_reader, mode="4h_psp",
    ))
    # Only t1 has all 3 symbols → exactly one event
    assert len(events) == 1
    assert events[0].bar_end_utc.replace(tzinfo=UTC) == t1


def test_full_rescan_idempotent(
    fake_reader: FakeBarReader,
    session_factory: sessionmaker[Session],
):
    ts = _utc(2026, 5, 4, 12, 0)
    fake_reader.set(symbol=NQ, timeframe="4h", df=_ohlc_one_candle(
        ts, o=21000, h=21020, l=20990, c=21015,
    ))
    fake_reader.set(symbol=ES, timeframe="4h", df=_ohlc_one_candle(
        ts, o=5000, h=5005, l=4985, c=4990,
    ))
    fake_reader.set(symbol=YM, timeframe="4h", df=_ohlc_one_candle(
        ts, o=40000, h=40020, l=39950, c=39960,
    ))

    with session_factory() as db:
        first = run_scan(
            detector_name="psp_candle_divergence",
            symbols=SYMBOLS, start=date(2026, 5, 4), end=date(2026, 5, 5),
            bar_reader=fake_reader, db=db, mode="4h_psp",
        )
        db.commit()
        second = run_scan(
            detector_name="psp_candle_divergence",
            symbols=SYMBOLS, start=date(2026, 5, 4), end=date(2026, 5, 5),
            bar_reader=fake_reader, db=db, mode="4h_psp",
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
                detector_name="psp_candle_divergence",
                symbols=SYMBOLS, start=date(2026, 5, 4), end=date(2026, 5, 5),
                bar_reader=fake_reader, db=db, mode="weekly_psp",
            )


def test_detector_is_registered():
    names = detector_registry.list_names()
    assert "psp_candle_divergence" in names
    d = detector_registry.get("psp_candle_divergence")
    assert d.feature_name == "psp_candle_divergence"
    assert d.detector_version == "v1"
    assert "daily_psp" in d.supported_modes
    assert "4h_psp" in d.supported_modes
    assert "1h_psp" in d.supported_modes
