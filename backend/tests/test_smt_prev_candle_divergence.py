"""Tests for previous-candle multi-timeframe SMT divergence."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import pandas as pd
import pytest

from app.data.reader import _BAR_TIMEFRAMES, _timedelta_to_pandas_rule
from app.research import detectors as detector_registry
from app.research.detectors import DetectorContext
from app.research.outcomes.smt_prev_candle_reactions import SmtPrevCandleReactionsComputer

UTC = timezone.utc

NQ = "NQ.c.0"
ES = "ES.c.0"
YM = "YM.c.0"
SYMBOLS = [NQ, ES, YM]


class FakeBarReader:
    def __init__(self) -> None:
        self._frames: dict[tuple[str, str], pd.DataFrame] = {}

    def set(self, *, symbol: str, timeframe: str, df: pd.DataFrame) -> None:
        if not isinstance(df.index, pd.DatetimeIndex):
            raise ValueError("FakeBarReader frames must use a DatetimeIndex")
        if df.index.tz is None:
            df = df.tz_localize(UTC)
        else:
            df = df.tz_convert(UTC)
        self._frames[(symbol, timeframe)] = df.sort_index()

    def __call__(self, *, symbol: str, timeframe: str, start, end, **kwargs):
        key = (symbol, timeframe)
        if key not in self._frames:
            raise FileNotFoundError(f"no bars for {symbol} {timeframe}")
        start_ts = pd.Timestamp(start)
        end_ts = pd.Timestamp(end)
        if start_ts.tz is None:
            start_ts = start_ts.tz_localize(UTC)
        if end_ts.tz is None:
            end_ts = end_ts.tz_localize(UTC)
        df = self._frames[key]
        return df[(df.index >= start_ts) & (df.index < end_ts)].copy()


def _utc(year: int, month: int, day: int, hour: int = 12, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=UTC)


def _ohlc_frame(rows: list[tuple[datetime, float, float, float, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        [{"open": o, "high": h, "low": lo, "close": c, "volume": 100} for _, o, h, lo, c in rows],
        index=pd.DatetimeIndex([row[0] for row in rows], tz=UTC),
    )


def _seed_two_15m_candles(
    reader: FakeBarReader,
    *,
    symbol: str,
    prev_high: float,
    prev_low: float,
    cur_high: float,
    cur_low: float,
    cur_close: float,
) -> None:
    reader.set(
        symbol=symbol,
        timeframe="15m",
        df=_ohlc_frame(
            [
                (
                    _utc(2026, 5, 4, 12, 0),
                    prev_high - 1,
                    prev_high,
                    prev_low,
                    prev_low + 1,
                ),
                (
                    _utc(2026, 5, 4, 12, 15),
                    cur_close,
                    cur_high,
                    cur_low,
                    cur_close,
                ),
            ]
        ),
    )


def _scan_15m(reader: FakeBarReader):
    detector = detector_registry.get("smt_prev_candle_divergence")
    return detector.scan(
        DetectorContext(
            symbols=SYMBOLS,
            start=date(2026, 5, 4),
            end=date(2026, 5, 5),
            bar_reader=reader,
            mode="15m_prev_candle_smt",
        )
    )


def test_detector_registered_with_requested_modes():
    detector = detector_registry.get("smt_prev_candle_divergence")

    assert detector.feature_name == "smt_prev_candle_divergence"
    assert detector.supported_modes == (
        "15m_prev_candle_smt",
        "30m_prev_candle_smt",
        "1h_prev_candle_smt",
        "90m_prev_candle_smt",
        "4h_prev_candle_smt",
        "6h_prev_candle_smt",
    )


def test_reader_supports_90m_and_6h_rules():
    assert _timedelta_to_pandas_rule(_BAR_TIMEFRAMES["90m"]) == "90min"
    assert _timedelta_to_pandas_rule(_BAR_TIMEFRAMES["6h"]) == "6h"


def test_high_side_prev_candle_smt_records_close_confirmed_event():
    reader = FakeBarReader()
    _seed_two_15m_candles(
        reader,
        symbol=NQ,
        prev_high=100.0,
        prev_low=90.0,
        cur_high=101.0,
        cur_low=94.0,
        cur_close=100.5,
    )
    _seed_two_15m_candles(
        reader,
        symbol=ES,
        prev_high=200.0,
        prev_low=190.0,
        cur_high=199.0,
        cur_low=194.0,
        cur_close=198.0,
    )
    _seed_two_15m_candles(
        reader,
        symbol=YM,
        prev_high=300.0,
        prev_low=290.0,
        cur_high=299.0,
        cur_low=294.0,
        cur_close=298.0,
    )

    events = _scan_15m(reader)

    assert len(events) == 1
    event = events[0]
    assert event.feature_name == "smt_prev_candle_divergence"
    assert event.event_type == "15m_prev_candle_smt_high"
    assert event.event_data["base_event_type"] == "15m_prev_candle_smt"
    assert event.primary_symbol == NQ
    assert event.side == "high"
    assert event.bar_end_utc == _utc(2026, 5, 4, 12, 30)
    assert event.event_data["swept_symbols"] == [NQ]
    assert sorted(event.event_data["holding_symbols"]) == sorted([ES, YM])
    assert event.event_data["close_confirmed_symbols"] == [NQ]
    assert event.event_data["close_confirmed_at_close"] is True
    assert event.context["confirmed_at_close"] is True


def test_wick_only_smt_is_tagged_not_close_confirmed():
    reader = FakeBarReader()
    _seed_two_15m_candles(
        reader,
        symbol=NQ,
        prev_high=100.0,
        prev_low=90.0,
        cur_high=101.0,
        cur_low=94.0,
        cur_close=99.5,
    )
    _seed_two_15m_candles(
        reader,
        symbol=ES,
        prev_high=200.0,
        prev_low=190.0,
        cur_high=199.0,
        cur_low=194.0,
        cur_close=198.0,
    )
    _seed_two_15m_candles(
        reader,
        symbol=YM,
        prev_high=300.0,
        prev_low=290.0,
        cur_high=299.0,
        cur_low=294.0,
        cur_close=298.0,
    )

    events = _scan_15m(reader)

    assert len(events) == 1
    event = events[0]
    assert event.side == "high"
    assert event.event_data["close_confirmed_symbols"] == []
    assert event.event_data["close_confirmed_at_close"] is False
    assert event.event_data["primary_close_confirmed"] is False
    assert event.event_data["closed_back_inside_symbols"] == [NQ]


def test_all_symbols_sweeping_same_side_is_not_divergence():
    reader = FakeBarReader()
    _seed_two_15m_candles(
        reader,
        symbol=NQ,
        prev_high=100.0,
        prev_low=90.0,
        cur_high=101.0,
        cur_low=94.0,
        cur_close=100.5,
    )
    _seed_two_15m_candles(
        reader,
        symbol=ES,
        prev_high=200.0,
        prev_low=190.0,
        cur_high=201.0,
        cur_low=194.0,
        cur_close=200.5,
    )
    _seed_two_15m_candles(
        reader,
        symbol=YM,
        prev_high=300.0,
        prev_low=290.0,
        cur_high=301.0,
        cur_low=294.0,
        cur_close=300.5,
    )

    assert _scan_15m(reader) == []


def test_prev_candle_reaction_scores_thesis_direction():
    event_ts = _utc(2026, 5, 4, 12, 30)
    event = SimpleNamespace(
        side="high",
        primary_symbol=NQ,
        bar_end_utc=event_ts,
        event_data={
            "close_confirmed_at_close": True,
            "primary_close_confirmed": True,
            "per_symbol_states": {
                NQ: {
                    "current_close": 100.0,
                    "current_high": 101.0,
                    "current_low": 97.0,
                }
            },
        },
    )
    bars = _ohlc_frame(
        [
            (event_ts + timedelta(minutes=0), 100.0, 102.0, 99.0, 100.5),
            (event_ts + timedelta(minutes=1), 100.5, 101.0, 95.0, 96.0),
            (event_ts + timedelta(minutes=14), 96.0, 97.0, 95.5, 96.0),
        ]
    )
    reader = FakeBarReader()
    reader.set(symbol=NQ, timeframe="1m", df=bars)

    outcomes = SmtPrevCandleReactionsComputer().compute(event, reader)

    assert outcomes is not None
    window = outcomes["next_15m"]
    assert window["thesis_confirmed"] is True
    assert window["close_moved_with_thesis"] is True
    assert window["mfe_pts_in_thesis"] == pytest.approx(5.0)
    assert window["mae_pts_against_thesis"] == pytest.approx(2.0)
    assert window["took_current_candle_low"] is True
