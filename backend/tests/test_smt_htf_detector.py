"""Tests for the SMT HTF reference-divergence detector.

Covers the 9 test cases from docs/RESEARCH_KNOWLEDGE_LAYER.md plus
additional shape assertions on event_data.

Tests use a synthetic in-memory bar_reader injected via
DetectorContext.bar_reader. No real data dependency; no warehouse
files needed.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import create_all, make_engine, make_session_factory
from app.research import detectors as detector_registry
from app.research.scan import run_scan

UTC = timezone.utc

NQ = "NQ.c.0"
ES = "ES.c.0"
YM = "YM.c.0"
SYMBOLS = [NQ, ES, YM]


# ---------- Fixtures ----------


@pytest.fixture
def session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = make_engine(f"sqlite:///{tmp_path / 'smt.sqlite'}")
    create_all(engine)
    return make_session_factory(engine)


class FakeBarReader:
    """Returns predetermined frames per (symbol, timeframe), sliced by
    [start, end) on the request. Mirrors the kwargs of
    `app.data.reader.read_bars`."""

    def __init__(self) -> None:
        self._frames: dict[tuple[str, str], pd.DataFrame] = {}

    def set(self, *, symbol: str, timeframe: str, df: pd.DataFrame) -> None:
        # Normalize to UTC-tz-aware DatetimeIndex for slicing
        if not isinstance(df.index, pd.DatetimeIndex):
            raise ValueError("FakeBarReader frames must have a DatetimeIndex")
        if df.index.tz is None:
            df = df.tz_localize(UTC)
        else:
            df = df.tz_convert(UTC)
        self._frames[(symbol, timeframe)] = df.sort_index()

    def __call__(self, *, symbol: str, timeframe: str, start, end, **kw):
        key = (symbol, timeframe)
        if key not in self._frames:
            raise FileNotFoundError(f"no bars for {symbol} {timeframe}")
        df = self._frames[key]
        start_ts = pd.Timestamp(start)
        end_ts = pd.Timestamp(end)
        if start_ts.tz is None:
            start_ts = start_ts.tz_localize(UTC)
        if end_ts.tz is None:
            end_ts = end_ts.tz_localize(UTC)
        mask = (df.index >= start_ts) & (df.index < end_ts)
        return df.loc[mask].copy()


@pytest.fixture
def fake_reader() -> FakeBarReader:
    return FakeBarReader()


# ---------- Helper: build OHLC frames ----------


def _ohlc_frame(
    rows: list[tuple[datetime, float, float, float, float]],
) -> pd.DataFrame:
    """rows = [(ts, open, high, low, close), ...]"""
    return pd.DataFrame(
        [
            {"open": o, "high": h, "low": lo, "close": c, "volume": 100}
            for _, o, h, lo, c in rows
        ],
        index=pd.DatetimeIndex([r[0] for r in rows], tz=UTC),
    )


def _utc(year: int, month: int, day: int, hour: int = 12, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=UTC)


# ---------- Reference / scan windows used in scenarios ----------
#
# Globex week containing 2026-05-04 (Mon) =
#    2026-05-03 22:00 UTC (Sun 18:00 ET) → 2026-05-08 21:00 UTC (Fri 17:00 ET)
# Previous Globex week =
#    2026-04-26 22:00 UTC → 2026-05-01 21:00 UTC


# Reference period (previous week)
_PREV_WEEK_START = _utc(2026, 4, 26, 22, 0)
_PREV_WEEK_END = _utc(2026, 5, 1, 21, 0)
# Current week (one we're scanning)
_CUR_WEEK_START = _utc(2026, 5, 3, 22, 0)
_CUR_WEEK_END = _utc(2026, 5, 8, 21, 0)


# ---------- Helpers to seed reference + tracking frames ----------


def _seed_reference_1m(
    reader: FakeBarReader,
    *,
    symbol: str,
    high: float,
    low: float,
) -> None:
    """One bar at the middle of the prev week with the requested high/low."""
    df = _ohlc_frame([(_utc(2026, 4, 28, 12, 0), high, high, low, high)])
    reader.set(symbol=symbol, timeframe="1m", df=df)


def _seed_tracking(
    reader: FakeBarReader,
    *,
    symbol: str,
    timeframe: str,
    bars: list[tuple[datetime, float, float, float, float]],
) -> None:
    reader.set(symbol=symbol, timeframe=timeframe, df=_ohlc_frame(bars))


# ---------- Test 1: weekly high-side SMT (NQ first, ES/YM lag) ----------


def test_weekly_high_side_smt_records_event(
    fake_reader: FakeBarReader,
    session_factory: sessionmaker[Session],
):
    # Reference: NQ 21000, ES 5000, YM 40000
    _seed_reference_1m(fake_reader, symbol=NQ, high=21000.0, low=20800.0)
    _seed_reference_1m(fake_reader, symbol=ES, high=5000.0, low=4900.0)
    _seed_reference_1m(fake_reader, symbol=YM, high=40000.0, low=39000.0)
    # Tracking 4H: NQ breaks at Mon 12:00 UTC, ES/YM stay below
    _seed_tracking(
        fake_reader, symbol=NQ, timeframe="4h",
        bars=[
            (_utc(2026, 5, 4, 8, 0), 20990, 20999, 20970, 20995),
            (_utc(2026, 5, 4, 12, 0), 20995, 21010, 20990, 21005),  # BREAK
            (_utc(2026, 5, 4, 16, 0), 21005, 21020, 21000, 21015),
        ],
    )
    _seed_tracking(
        fake_reader, symbol=ES, timeframe="4h",
        bars=[
            (_utc(2026, 5, 4, 8, 0), 4980, 4995, 4970, 4990),
            (_utc(2026, 5, 4, 12, 0), 4990, 4998, 4985, 4995),  # no break
            (_utc(2026, 5, 4, 16, 0), 4995, 5005, 4992, 5002),  # break (later)
        ],
    )
    _seed_tracking(
        fake_reader, symbol=YM, timeframe="4h",
        bars=[
            (_utc(2026, 5, 4, 8, 0), 39950, 39990, 39920, 39980),
            (_utc(2026, 5, 4, 12, 0), 39980, 39998, 39970, 39985),  # no break
            (_utc(2026, 5, 4, 16, 0), 39985, 39995, 39960, 39990),  # still none
        ],
    )

    with session_factory() as db:
        result = run_scan(
            detector_name="smt_htf_reference_divergence",
            symbols=SYMBOLS,
            start=date(2026, 5, 4),
            end=date(2026, 5, 8),
            bar_reader=fake_reader,
            db=db,
            mode="weekly_smt",
        )
        db.commit()

    assert result.n_errors == 0, result.error_messages
    assert result.n_inserted == 1
    assert result.n_skipped_duplicate == 0


def test_weekly_high_side_event_data_shape(
    fake_reader: FakeBarReader,
    session_factory: sessionmaker[Session],
):
    """Verify the event payload has all the keys SMT analysis needs."""
    _seed_reference_1m(fake_reader, symbol=NQ, high=21000.0, low=20800.0)
    _seed_reference_1m(fake_reader, symbol=ES, high=5000.0, low=4900.0)
    _seed_reference_1m(fake_reader, symbol=YM, high=40000.0, low=39000.0)
    _seed_tracking(fake_reader, symbol=NQ, timeframe="4h", bars=[
        (_utc(2026, 5, 4, 12, 0), 20995, 21010, 20990, 21005),
    ])
    _seed_tracking(fake_reader, symbol=ES, timeframe="4h", bars=[
        (_utc(2026, 5, 4, 12, 0), 4990, 4995, 4985, 4992),
        (_utc(2026, 5, 4, 16, 0), 4992, 5005, 4990, 5002),  # later confirm
    ])
    _seed_tracking(fake_reader, symbol=YM, timeframe="4h", bars=[
        (_utc(2026, 5, 4, 12, 0), 39990, 39998, 39980, 39995),
    ])  # YM never confirms

    detector = detector_registry.get("smt_htf_reference_divergence")
    from app.research.detectors import DetectorContext
    ctx = DetectorContext(
        symbols=SYMBOLS, start=date(2026, 5, 4), end=date(2026, 5, 8),
        bar_reader=fake_reader, mode="weekly_smt",
    )
    events = detector.scan(ctx)
    assert len(events) == 1
    e = events[0]
    assert e.feature_name == "smt_htf_reference_divergence"
    assert e.event_type == "weekly_smt"
    assert e.timeframe == "4H"
    assert e.side == "high"
    assert e.primary_symbol == NQ  # NQ broke first
    data = e.event_data
    assert data["reference_type"] == "previous_week"
    assert data["tracking_timeframe"] == "4h"
    assert data["first_break_symbol"] == NQ
    assert data["first_break_price"] == pytest.approx(21010.0)
    assert sorted(data["lagging_symbols_at_break"]) == sorted([ES, YM])
    assert data["confirming_symbols_at_break"] == []
    # symbol_states should carry per-symbol reference levels
    states = data["symbol_states"]
    assert states[NQ]["reference_high"] == pytest.approx(21000.0)
    assert states[NQ]["broke_high"] is True
    assert states[ES]["broke_high"] is True  # ES eventually broke
    assert states[YM]["broke_high"] is False
    # later_confirmations should list ES (eventually broke), not YM
    confirmed = [c["symbol"] for c in data["later_confirmations"]]
    assert ES in confirmed
    assert YM not in confirmed
    assert data["did_all_confirm_by_window_end"] is False
    # divergence_duration_seconds is None when not all confirmed
    assert data["divergence_duration_seconds"] is None


# ---------- Test 2: weekly low-side SMT ----------


def test_weekly_low_side_smt_records_event(
    fake_reader: FakeBarReader,
    session_factory: sessionmaker[Session],
):
    _seed_reference_1m(fake_reader, symbol=NQ, high=21000.0, low=20800.0)
    _seed_reference_1m(fake_reader, symbol=ES, high=5000.0, low=4900.0)
    _seed_reference_1m(fake_reader, symbol=YM, high=40000.0, low=39000.0)
    # NQ breaks low at 12:00, ES/YM stay above their lows
    _seed_tracking(fake_reader, symbol=NQ, timeframe="4h", bars=[
        (_utc(2026, 5, 4, 12, 0), 20810, 20815, 20790, 20795),  # BREAK low
    ])
    _seed_tracking(fake_reader, symbol=ES, timeframe="4h", bars=[
        (_utc(2026, 5, 4, 12, 0), 4910, 4915, 4905, 4910),
    ])
    _seed_tracking(fake_reader, symbol=YM, timeframe="4h", bars=[
        (_utc(2026, 5, 4, 12, 0), 39010, 39020, 39005, 39015),
    ])

    with session_factory() as db:
        result = run_scan(
            detector_name="smt_htf_reference_divergence",
            symbols=SYMBOLS,
            start=date(2026, 5, 4),
            end=date(2026, 5, 8),
            bar_reader=fake_reader,
            db=db,
            mode="weekly_smt",
        )
        db.commit()

    assert result.n_errors == 0, result.error_messages
    assert result.n_inserted == 1


# ---------- Test 3: previous-day SMT (1H tracking) ----------


def test_previous_day_high_side_smt(
    fake_reader: FakeBarReader,
    session_factory: sessionmaker[Session],
):
    """ES takes prev-day high on 1H, NQ/YM lag → event."""
    # Globex day for Tue 2026-05-05 = Mon 22:00 UTC → Tue 21:00 UTC
    # Prev day = Sun 22:00 UTC → Mon 21:00 UTC (the Sun-Mon session)
    # Reference period: Sun 2026-05-03 22:00 UTC → Mon 2026-05-04 21:00 UTC
    _seed_reference_1m(fake_reader, symbol=NQ, high=21000.0, low=20800.0)
    _seed_reference_1m(fake_reader, symbol=ES, high=5000.0, low=4900.0)
    _seed_reference_1m(fake_reader, symbol=YM, high=40000.0, low=39000.0)
    # Override 1m fixture with a bar in the right Sun→Mon window
    fake_reader.set(
        symbol=NQ, timeframe="1m",
        df=_ohlc_frame([(_utc(2026, 5, 4, 12, 0), 21000, 21000, 20800, 21000)]),
    )
    fake_reader.set(
        symbol=ES, timeframe="1m",
        df=_ohlc_frame([(_utc(2026, 5, 4, 12, 0), 5000, 5000, 4900, 5000)]),
    )
    fake_reader.set(
        symbol=YM, timeframe="1m",
        df=_ohlc_frame([(_utc(2026, 5, 4, 12, 0), 40000, 40000, 39000, 40000)]),
    )
    # Tracking 1H bars within Tue's Globex day (Mon 22:00 UTC → Tue 21:00 UTC)
    # ES breaks first at Tue 14:00 UTC; NQ/YM lag.
    _seed_tracking(fake_reader, symbol=ES, timeframe="1h", bars=[
        (_utc(2026, 5, 5, 13, 0), 4995, 4998, 4990, 4995),
        (_utc(2026, 5, 5, 14, 0), 4995, 5005, 4992, 5002),  # BREAK
    ])
    _seed_tracking(fake_reader, symbol=NQ, timeframe="1h", bars=[
        (_utc(2026, 5, 5, 13, 0), 20990, 20995, 20980, 20985),
        (_utc(2026, 5, 5, 14, 0), 20985, 20998, 20980, 20990),  # no break
    ])
    _seed_tracking(fake_reader, symbol=YM, timeframe="1h", bars=[
        (_utc(2026, 5, 5, 13, 0), 39990, 39995, 39980, 39985),
        (_utc(2026, 5, 5, 14, 0), 39985, 39998, 39980, 39990),  # no break
    ])

    with session_factory() as db:
        result = run_scan(
            detector_name="smt_htf_reference_divergence",
            symbols=SYMBOLS,
            start=date(2026, 5, 5),
            end=date(2026, 5, 6),
            bar_reader=fake_reader,
            db=db,
            mode="previous_day_smt",
        )
        db.commit()

    assert result.n_errors == 0, result.error_messages
    assert result.n_inserted == 1


# ---------- Test 4: tie-breaker — all break in same candle → no event ----------


def test_no_event_when_all_break_same_candle(
    fake_reader: FakeBarReader,
    session_factory: sessionmaker[Session],
):
    _seed_reference_1m(fake_reader, symbol=NQ, high=21000.0, low=20800.0)
    _seed_reference_1m(fake_reader, symbol=ES, high=5000.0, low=4900.0)
    _seed_reference_1m(fake_reader, symbol=YM, high=40000.0, low=39000.0)
    # All three symbols' high-side breaks land in the same 4H candle
    _seed_tracking(fake_reader, symbol=NQ, timeframe="4h", bars=[
        (_utc(2026, 5, 4, 12, 0), 20995, 21010, 20990, 21005),
    ])
    _seed_tracking(fake_reader, symbol=ES, timeframe="4h", bars=[
        (_utc(2026, 5, 4, 12, 0), 4995, 5010, 4990, 5005),
    ])
    _seed_tracking(fake_reader, symbol=YM, timeframe="4h", bars=[
        (_utc(2026, 5, 4, 12, 0), 39995, 40010, 39990, 40005),
    ])

    with session_factory() as db:
        result = run_scan(
            detector_name="smt_htf_reference_divergence",
            symbols=SYMBOLS,
            start=date(2026, 5, 4),
            end=date(2026, 5, 8),
            bar_reader=fake_reader,
            db=db,
            mode="weekly_smt",
        )
        db.commit()

    # All-symbols-break-same-candle is a correlated breakout, not SMT.
    # No HIGH event. (Low side might or might not fire depending on
    # bars; we only assert NO weekly_smt high-side event.)
    assert result.n_errors == 0
    # 0 high-side events recorded means at most low-side events. Since
    # low-side bars stay above prev lows, no event fires at all.
    assert result.n_inserted == 0


# ---------- Test 5: no symbol breaks → no event ----------


def test_no_event_when_no_symbol_breaks(
    fake_reader: FakeBarReader,
    session_factory: sessionmaker[Session],
):
    _seed_reference_1m(fake_reader, symbol=NQ, high=21000.0, low=20800.0)
    _seed_reference_1m(fake_reader, symbol=ES, high=5000.0, low=4900.0)
    _seed_reference_1m(fake_reader, symbol=YM, high=40000.0, low=39000.0)
    # All bars stay strictly inside the reference range — no break.
    _seed_tracking(fake_reader, symbol=NQ, timeframe="4h", bars=[
        (_utc(2026, 5, 4, 12, 0), 20900, 20950, 20850, 20920),
    ])
    _seed_tracking(fake_reader, symbol=ES, timeframe="4h", bars=[
        (_utc(2026, 5, 4, 12, 0), 4940, 4970, 4920, 4955),
    ])
    _seed_tracking(fake_reader, symbol=YM, timeframe="4h", bars=[
        (_utc(2026, 5, 4, 12, 0), 39400, 39600, 39200, 39500),
    ])

    with session_factory() as db:
        result = run_scan(
            detector_name="smt_htf_reference_divergence",
            symbols=SYMBOLS,
            start=date(2026, 5, 4),
            end=date(2026, 5, 8),
            bar_reader=fake_reader,
            db=db,
            mode="weekly_smt",
        )
        db.commit()

    assert result.n_errors == 0
    assert result.n_inserted == 0


# ---------- Test 6: idempotence — re-running does not duplicate ----------


def test_full_rescan_is_idempotent(
    fake_reader: FakeBarReader,
    session_factory: sessionmaker[Session],
):
    _seed_reference_1m(fake_reader, symbol=NQ, high=21000.0, low=20800.0)
    _seed_reference_1m(fake_reader, symbol=ES, high=5000.0, low=4900.0)
    _seed_reference_1m(fake_reader, symbol=YM, high=40000.0, low=39000.0)
    _seed_tracking(fake_reader, symbol=NQ, timeframe="4h", bars=[
        (_utc(2026, 5, 4, 12, 0), 20995, 21010, 20990, 21005),
    ])
    _seed_tracking(fake_reader, symbol=ES, timeframe="4h", bars=[
        (_utc(2026, 5, 4, 12, 0), 4990, 4995, 4985, 4992),
    ])
    _seed_tracking(fake_reader, symbol=YM, timeframe="4h", bars=[
        (_utc(2026, 5, 4, 12, 0), 39990, 39998, 39980, 39995),
    ])

    with session_factory() as db:
        first = run_scan(
            detector_name="smt_htf_reference_divergence",
            symbols=SYMBOLS,
            start=date(2026, 5, 4),
            end=date(2026, 5, 8),
            bar_reader=fake_reader,
            db=db,
            mode="weekly_smt",
        )
        db.commit()

        second = run_scan(
            detector_name="smt_htf_reference_divergence",
            symbols=SYMBOLS,
            start=date(2026, 5, 4),
            end=date(2026, 5, 8),
            bar_reader=fake_reader,
            db=db,
            mode="weekly_smt",
        )
        db.commit()

    assert first.n_inserted == 1
    assert second.n_inserted == 0
    assert second.n_skipped_duplicate == 1


# ---------- Test 7: detector_version + replay_pointer surface in event ----------


def test_event_includes_detector_version_and_replay_pointer(
    fake_reader: FakeBarReader,
):
    _seed_reference_1m(fake_reader, symbol=NQ, high=21000.0, low=20800.0)
    _seed_reference_1m(fake_reader, symbol=ES, high=5000.0, low=4900.0)
    _seed_reference_1m(fake_reader, symbol=YM, high=40000.0, low=39000.0)
    _seed_tracking(fake_reader, symbol=NQ, timeframe="4h", bars=[
        (_utc(2026, 5, 4, 12, 0), 20995, 21010, 20990, 21005),
    ])
    _seed_tracking(fake_reader, symbol=ES, timeframe="4h", bars=[
        (_utc(2026, 5, 4, 12, 0), 4990, 4995, 4985, 4992),
    ])
    _seed_tracking(fake_reader, symbol=YM, timeframe="4h", bars=[
        (_utc(2026, 5, 4, 12, 0), 39990, 39998, 39980, 39995),
    ])

    detector = detector_registry.get("smt_htf_reference_divergence")
    from app.research.detectors import DetectorContext
    events = detector.scan(DetectorContext(
        symbols=SYMBOLS, start=date(2026, 5, 4), end=date(2026, 5, 8),
        bar_reader=fake_reader, mode="weekly_smt",
    ))
    assert len(events) == 1
    e = events[0]
    # detector_version on both the row column and inside event_data
    assert e.detector_version == "v1"
    assert e.event_data["detector_version"] == "v1"
    # replay_pointer carries primary_symbol + ts + tracking_timeframe
    assert e.replay_pointer is not None
    assert e.replay_pointer["primary_symbol"] == NQ
    assert e.replay_pointer["tracking_timeframe"] == "4h"


# ---------- Test 8: missing reference data is not a crash ----------


def test_missing_reference_data_skips_period_safely(
    fake_reader: FakeBarReader,
    session_factory: sessionmaker[Session],
):
    """If 1m bars are missing for one symbol's prev-week reference,
    skip the period rather than crash the scan."""
    # Only seed reference for NQ; ES and YM intentionally missing.
    _seed_reference_1m(fake_reader, symbol=NQ, high=21000.0, low=20800.0)
    _seed_tracking(fake_reader, symbol=NQ, timeframe="4h", bars=[
        (_utc(2026, 5, 4, 12, 0), 20995, 21010, 20990, 21005),
    ])

    with session_factory() as db:
        result = run_scan(
            detector_name="smt_htf_reference_divergence",
            symbols=SYMBOLS,
            start=date(2026, 5, 4),
            end=date(2026, 5, 8),
            bar_reader=fake_reader,
            db=db,
            mode="weekly_smt",
        )
        db.commit()

    assert result.n_errors == 0
    assert result.n_inserted == 0


# ---------- Test 9: scan rejects too-few-symbols ----------


def test_scan_requires_at_least_two_symbols(
    fake_reader: FakeBarReader,
    session_factory: sessionmaker[Session],
):
    with session_factory() as db:
        result = run_scan(
            detector_name="smt_htf_reference_divergence",
            symbols=[NQ],
            start=date(2026, 5, 4),
            end=date(2026, 5, 8),
            bar_reader=fake_reader,
            db=db,
            mode="weekly_smt",
        )
        db.commit()

    # Detector raises ValueError → orchestrator catches it as an error
    assert result.n_errors == 1
    assert result.n_inserted == 0


def test_unsupported_mode_rejected(
    fake_reader: FakeBarReader,
    session_factory: sessionmaker[Session],
):
    with session_factory() as db:
        with pytest.raises(ValueError, match="does not support mode"):
            run_scan(
                detector_name="smt_htf_reference_divergence",
                symbols=SYMBOLS,
                start=date(2026, 5, 4),
                end=date(2026, 5, 8),
                bar_reader=fake_reader,
                db=db,
                mode="not_a_real_mode",
            )


# ---------- Detector registry sanity ----------


def test_detector_is_registered():
    names = detector_registry.list_names()
    assert "smt_htf_reference_divergence" in names
    d = detector_registry.get("smt_htf_reference_divergence")
    assert d.feature_name == "smt_htf_reference_divergence"
    assert d.detector_version == "v1"
    assert "weekly_smt" in d.supported_modes
    assert "previous_day_smt" in d.supported_modes
