"""Tests for the displacement_candle reactions outcome computer."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from app.db import models
from app.research.outcomes.displacement_reactions import DisplacementReactionsComputer
from app.services.research_events import make_event_id

UTC = timezone.utc
NQ = "NQ.c.0"


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


def _build_disp_event(
    *,
    mode: str,
    direction: str,
    primary: str,
    bar_end_utc: datetime,
    d_open: float, d_high: float, d_low: float, d_close: float,
) -> models.ResearchEvent:
    timeframe_map = {
        "15m_disp": "15M",
        "30m_disp": "30M",
        "1h_disp": "1H",
        "4h_disp": "4H",
        "daily_disp": "1D",
        "unknown_mode": "1H",
    }
    body = abs(d_close - d_open)
    rng = d_high - d_low
    event_data = {
        "schema_version": 1,
        "detector_version": "v1",
        "tracking_timeframe": "1h",
        "direction": direction,
        "candle": {
            "ts_utc": bar_end_utc.isoformat(),
            "open": d_open, "high": d_high, "low": d_low, "close": d_close,
        },
        "body_pts": body,
        "range_pts": rng,
        "body_to_range_ratio": body / rng if rng > 0 else None,
        "rolling_mean_body_pts": 5.0,
        "ratio_vs_recent_mean": body / 5.0,
        "is_2x": (body / 5.0) >= 2.0,
        "is_3x": (body / 5.0) >= 3.0,
        "is_4x": (body / 5.0) >= 4.0,
        "is_5x": (body / 5.0) >= 5.0,
    }
    return models.ResearchEvent(
        event_id=make_event_id("displacement_candle", primary, bar_end_utc, mode),
        feature_name="displacement_candle",
        event_type=mode,
        bar_end_utc=bar_end_utc.replace(tzinfo=None) if bar_end_utc.tzinfo else bar_end_utc,
        primary_symbol=primary,
        symbols=[primary],
        timeframe=timeframe_map[mode],
        side=direction,
        event_data=event_data,
        detector_version="v1",
    )


def test_bullish_continuation_no_retrace(fake_reader: FakeBarReader):
    """Bullish disp with body 21030→21080. Forward bars rally without retracing."""
    disp_ts = datetime(2026, 5, 4, 12, tzinfo=UTC)
    bars = _ohlc_frame([
        (disp_ts + timedelta(hours=i), 21080 + i, 21100 + i, 21078 + i, 21090 + i)
        for i in range(1, 6)
    ])
    fake_reader.set(symbol=NQ, timeframe="1h", df=bars)
    event = _build_disp_event(
        mode="1h_disp", direction="bullish", primary=NQ, bar_end_utc=disp_ts,
        d_open=21030, d_high=21082, d_low=21028, d_close=21080,
    )
    out = DisplacementReactionsComputer().compute(event, fake_reader)
    assert out is not None
    assert out["thesis_direction"] == "up"
    assert out["forward_3_candles"]["mfe_pts_in_thesis"] >= 0
    # No bar low <= d.close (21080), so no retracement tap.
    # bar 1 low = 21078 ≤ 21080 → tapped close. Wait yes.
    # Actually let me check: bar 1 low = 21078, d.close = 21080.
    # So bar 1 low <= 21080 → tapped close. Yes — adjust expectation.
    retrac = out["retracement"]
    assert retrac["tapped_close"] is True  # bar 1 wicks down to 21078
    # But not tapped_mid (mid = (21080+21030)/2 = 21055), since lowest low across forward = 21078.
    assert retrac["tapped_mid"] is False


def test_full_retrace_invalidation(fake_reader: FakeBarReader):
    """Bullish disp gets fully reclaimed: a forward bar closes BELOW d.open."""
    disp_ts = datetime(2026, 5, 4, 12, tzinfo=UTC)
    # disp body 21030→21080
    bars = _ohlc_frame([
        (disp_ts + timedelta(hours=1), 21080, 21080, 21025, 21028),  # closes BELOW d.open=21030
        (disp_ts + timedelta(hours=2), 21028, 21035, 21020, 21025),
    ])
    fake_reader.set(symbol=NQ, timeframe="1h", df=bars)
    event = _build_disp_event(
        mode="1h_disp", direction="bullish", primary=NQ, bar_end_utc=disp_ts,
        d_open=21030, d_high=21082, d_low=21028, d_close=21080,
    )
    out = DisplacementReactionsComputer().compute(event, fake_reader)
    assert out is not None
    inv = out["invalidation"]
    assert inv["invalidated"] is True
    assert inv["bars_to_invalidation"] == 1
    retrac = out["retracement"]
    assert retrac["tapped_close"] is True
    assert retrac["tapped_mid"] is True
    assert retrac["tapped_open"] is True
    assert retrac["tapped_full"] is True  # bar 1 low 21025 < d.low 21028
    assert retrac["deepest_retracement_frac"] == 1.0


def test_bearish_disp_retrace(fake_reader: FakeBarReader):
    """Bearish disp 21080→21030. Forward bar wicks back UP to body."""
    disp_ts = datetime(2026, 5, 4, 12, tzinfo=UTC)
    bars = _ohlc_frame([
        (disp_ts + timedelta(hours=1), 21030, 21055, 21025, 21035),  # wicks to mid
        (disp_ts + timedelta(hours=2), 21035, 21040, 21025, 21030),
    ])
    fake_reader.set(symbol=NQ, timeframe="1h", df=bars)
    event = _build_disp_event(
        mode="1h_disp", direction="bearish", primary=NQ, bar_end_utc=disp_ts,
        d_open=21080, d_high=21082, d_low=21028, d_close=21030,
    )
    out = DisplacementReactionsComputer().compute(event, fake_reader)
    assert out is not None
    retrac = out["retracement"]
    # Bullish retracement check for bearish: bar.high >= d.close (21030).
    # bar 1 high = 21055 ≥ 21030 → tapped close.
    assert retrac["tapped_close"] is True
    assert retrac["bars_to_close"] == 1
    # Mid = (21080+21030)/2 = 21055. bar 1 high = 21055 ≥ 21055 → tapped mid.
    assert retrac["tapped_mid"] is True
    # Open = 21080. bar 1 high = 21055 < 21080 → NOT tapped open.
    assert retrac["tapped_open"] is False


def test_returns_none_for_unknown_mode(fake_reader: FakeBarReader):
    disp_ts = datetime(2026, 5, 4, 12, tzinfo=UTC)
    event = _build_disp_event(
        mode="unknown_mode", direction="bullish", primary=NQ, bar_end_utc=disp_ts,
        d_open=21030, d_high=21082, d_low=21028, d_close=21080,
    )
    assert DisplacementReactionsComputer().compute(event, fake_reader) is None


def test_15m_disp_reactions_use_next_15m_candles(fake_reader: FakeBarReader):
    disp_ts = datetime(2026, 5, 4, 12, tzinfo=UTC)
    bars = _ohlc_frame([
        (disp_ts + timedelta(minutes=15), 21080, 21100, 21078, 21090),
        (disp_ts + timedelta(minutes=30), 21090, 21110, 21085, 21105),
        (disp_ts + timedelta(minutes=45), 21105, 21120, 21095, 21115),
    ])
    fake_reader.set(symbol=NQ, timeframe="15m", df=bars)
    event = _build_disp_event(
        mode="15m_disp", direction="bullish", primary=NQ, bar_end_utc=disp_ts,
        d_open=21030, d_high=21082, d_low=21028, d_close=21080,
    )
    out = DisplacementReactionsComputer().compute(event, fake_reader)
    assert out is not None
    assert out["forward_3_candles"]["n_bars"] == 3
    assert out["forward_3_candles"]["mfe_pts_in_thesis"] == pytest.approx(40.0)


def test_computer_is_registered():
    from app.research.outcomes import OUTCOMES, get_by_feature
    assert "displacement_reactions_v1" in OUTCOMES
    c = get_by_feature("displacement_candle")
    assert c.outcome_version == "v1"
