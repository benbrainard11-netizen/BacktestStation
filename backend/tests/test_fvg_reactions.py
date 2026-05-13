"""Tests for the FVG reactions outcome computer."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.db import models
from app.db.session import (
    create_all,
    make_engine,
    make_session_factory,
)
from app.research.outcomes import fvg_reactions  # noqa: F401  -- ensures register
from app.research.outcomes.fvg_reactions import FvgReactionsComputer
from app.research.outcomes.runner import run_outcomes
from app.services.research_events import make_event_id

UTC = timezone.utc

NQ = "NQ.c.0"


@pytest.fixture
def session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = make_engine(f"sqlite:///{tmp_path / 'fvg_react.sqlite'}")
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
        out = sliced.reset_index().rename(columns={"index": "ts_event"})
        if "ts_event" not in out.columns and df.index.name:
            out = out.rename(columns={df.index.name: "ts_event"})
        return out


@pytest.fixture
def fake_reader() -> FakeBarReader:
    return FakeBarReader()


def _utc(year, month, day, hour=0, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=UTC)


def _ohlc_frame(rows):
    return pd.DataFrame(
        [{"open": o, "high": h, "low": low, "close": c, "volume": 100}
         for _, o, h, low, c in rows],
        index=pd.DatetimeIndex([r[0] for r in rows], tz=UTC),
    )


def _build_fvg_event(
    *,
    event_type: str,
    direction: str,
    primary: str,
    bar_end_utc: datetime,
    fvg_high: float,
    fvg_low: float,
    c3_close: float,
) -> models.ResearchEvent:
    timeframe_map = {
        "1h_fvg": "1H", "4h_fvg": "4H", "daily_fvg": "1D", "weekly_fvg": "1W",
    }
    fvg_mid = (fvg_high + fvg_low) / 2.0
    event_data = {
        "schema_version": 1,
        "detector_version": "v1",
        "tracking_timeframe": event_type.replace("_fvg", ""),
        "direction": direction,
        "fvg_high": fvg_high,
        "fvg_low": fvg_low,
        "fvg_mid": fvg_mid,
        "fvg_width_pts": fvg_high - fvg_low,
        "candle_1": {"ts_utc": "x", "open": 0, "high": 0, "low": 0, "close": 0},
        "candle_2": {"ts_utc": "x", "open": 0, "high": 0, "low": 0, "close": 0},
        "candle_3": {
            "ts_utc": bar_end_utc.isoformat(),
            "open": c3_close - 1, "high": c3_close + 1,
            "low": c3_close - 2, "close": c3_close,
        },
    }
    return models.ResearchEvent(
        event_id=make_event_id("fvg_formation", primary, bar_end_utc, event_type),
        feature_name="fvg_formation",
        event_type=event_type,
        bar_end_utc=bar_end_utc.replace(tzinfo=None) if bar_end_utc.tzinfo else bar_end_utc,
        primary_symbol=primary,
        symbols=[primary],
        timeframe=timeframe_map[event_type],
        side=direction,
        event_data=event_data,
        detector_version="v1",
    )


# ---------- tests ----------


def test_bullish_fvg_unmitigated(fake_reader: FakeBarReader):
    """Bullish FVG with all forward bars trading above the gap."""
    fvg_ts = _utc(2026, 5, 4, 12)
    # 5 forward 1h bars, all rallying up — never enter the gap
    bars = _ohlc_frame([
        (fvg_ts + timedelta(hours=i), 21010 + i, 21030 + i, 21008 + i, 21020 + i)
        for i in range(1, 6)
    ])
    fake_reader.set(symbol=NQ, timeframe="1h", df=bars)

    event = _build_fvg_event(
        event_type="1h_fvg", direction="bullish", primary=NQ,
        bar_end_utc=fvg_ts,
        fvg_high=21005.0, fvg_low=21000.0, c3_close=21010.0,
    )
    out = FvgReactionsComputer().compute(event, fake_reader)
    assert out is not None
    mit = out["mitigation"]
    assert mit["tapped"] is False
    assert mit["fully_filled"] is False
    assert mit["bars_to_tap"] is None
    assert mit["deepest_wick_frac"] == 0.0
    assert mit["deepest_close_frac"] == 0.0
    assert mit["closed_inside"] is False
    assert mit["closed_through"] is False
    assert mit["tap_bar_classification"] is None
    assert out["post_tap_reaction"] is None


def test_bullish_fvg_full_fill(fake_reader: FakeBarReader):
    """First forward bar wicks fully through the gap."""
    fvg_ts = _utc(2026, 5, 4, 12)
    bars = _ohlc_frame([
        # Bar 1: deep down to 20999 — fully fills (low <= fvg_low=21000)
        (fvg_ts + timedelta(hours=1), 21010, 21015, 20999, 21008),
        (fvg_ts + timedelta(hours=2), 21008, 21020, 21005, 21015),
        (fvg_ts + timedelta(hours=3), 21015, 21030, 21010, 21025),
    ])
    fake_reader.set(symbol=NQ, timeframe="1h", df=bars)

    event = _build_fvg_event(
        event_type="1h_fvg", direction="bullish", primary=NQ,
        bar_end_utc=fvg_ts,
        fvg_high=21005.0, fvg_low=21000.0, c3_close=21010.0,
    )
    out = FvgReactionsComputer().compute(event, fake_reader)
    assert out is not None
    mit = out["mitigation"]
    assert mit["tapped"] is True
    assert mit["mid_filled"] is True
    assert mit["fully_filled"] is True
    assert mit["bars_to_tap"] == 1
    assert mit["bars_to_mid"] == 1
    assert mit["bars_to_full"] == 1
    assert mit["deepest_wick_frac"] == 1.0
    # Bar 1 closed at 21008 — back ABOVE the gap (close > fvg_high=21005),
    # so this is a clean wick rejection.
    assert mit["closed_inside"] is False
    assert mit["closed_through"] is False
    assert mit["tap_bar_classification"] == "wick_reject"
    assert mit["wick_quartiles_hit"] == [25, 50, 75, 100]


def test_bullish_fvg_partial_tap(fake_reader: FakeBarReader):
    """Bar 2 taps the gap but doesn't reach the mid."""
    fvg_ts = _utc(2026, 5, 4, 12)
    # gap is (21000, 21005), mid=21002.5
    bars = _ohlc_frame([
        (fvg_ts + timedelta(hours=1), 21010, 21020, 21008, 21015),  # above gap
        (fvg_ts + timedelta(hours=2), 21015, 21015, 21004, 21010),  # tapped (low=21004 <= 21005), did NOT cross mid
        (fvg_ts + timedelta(hours=3), 21010, 21020, 21008, 21015),
    ])
    fake_reader.set(symbol=NQ, timeframe="1h", df=bars)

    event = _build_fvg_event(
        event_type="1h_fvg", direction="bullish", primary=NQ,
        bar_end_utc=fvg_ts,
        fvg_high=21005.0, fvg_low=21000.0, c3_close=21010.0,
    )
    out = FvgReactionsComputer().compute(event, fake_reader)
    assert out is not None
    mit = out["mitigation"]
    assert mit["tapped"] is True
    assert mit["mid_filled"] is False
    assert mit["fully_filled"] is False
    assert mit["bars_to_tap"] == 2
    assert mit["bars_to_mid"] is None
    assert mit["bars_to_full"] is None
    # Wick depth = 21005 - 21004 = 1pt out of 5pt gap = 0.2
    assert mit["deepest_wick_frac"] == pytest.approx(0.2)
    # Bar 2 closed at 21010 — back above the gap → wick reject.
    assert mit["closed_inside"] is False
    assert mit["closed_through"] is False
    assert mit["tap_bar_classification"] == "wick_reject"
    # 20% wick → no quartile thresholds crossed
    assert mit["wick_quartiles_hit"] == []


def test_bearish_fvg_full_fill(fake_reader: FakeBarReader):
    """Bearish FVG: bar wicks UP through the gap."""
    fvg_ts = _utc(2026, 5, 4, 12)
    # gap is (20995, 21000) for bearish (fvg_low=20995=c3.high, fvg_high=21000=c1.low)
    bars = _ohlc_frame([
        (fvg_ts + timedelta(hours=1), 20990, 21001, 20985, 20995),  # high=21001 >= fvg_high=21000 → full fill
        (fvg_ts + timedelta(hours=2), 20995, 20998, 20985, 20990),
    ])
    fake_reader.set(symbol=NQ, timeframe="1h", df=bars)

    event = _build_fvg_event(
        event_type="1h_fvg", direction="bearish", primary=NQ,
        bar_end_utc=fvg_ts,
        fvg_high=21000.0, fvg_low=20995.0, c3_close=20990.0,
    )
    out = FvgReactionsComputer().compute(event, fake_reader)
    assert out is not None
    mit = out["mitigation"]
    assert mit["tapped"] is True
    assert mit["fully_filled"] is True
    assert mit["bars_to_full"] == 1


def test_excursion_thesis_direction_bullish(fake_reader: FakeBarReader):
    """Bullish FVG: thesis = up. MFE = max high - ref_close."""
    fvg_ts = _utc(2026, 5, 4, 12)
    bars = _ohlc_frame([
        (fvg_ts + timedelta(hours=i + 1), 21010 + i, 21050 + i, 21000 + i, 21020 + i)
        for i in range(3)
    ])
    fake_reader.set(symbol=NQ, timeframe="1h", df=bars)
    event = _build_fvg_event(
        event_type="1h_fvg", direction="bullish", primary=NQ,
        bar_end_utc=fvg_ts,
        fvg_high=21005.0, fvg_low=21000.0, c3_close=21010.0,
    )
    out = FvgReactionsComputer().compute(event, fake_reader)
    assert out is not None
    f3 = out["forward_3_candles"]
    # max high across 3 = 21052 (bar 3). MFE in thesis = 21052 - 21010 = 42.
    assert f3["mfe_pts_in_thesis"] == pytest.approx(42.0)
    # min low = 21000 (bar 1). MAE = 21010 - 21000 = 10.
    assert f3["mae_pts_against_thesis"] == pytest.approx(10.0)


def test_returns_none_for_unknown_event_type(fake_reader: FakeBarReader):
    fvg_ts = _utc(2026, 5, 4, 12)
    event = _build_fvg_event(
        event_type="weekly_fvg", direction="bullish", primary=NQ,
        bar_end_utc=fvg_ts,
        fvg_high=21005.0, fvg_low=21000.0, c3_close=21010.0,
    )
    assert FvgReactionsComputer().compute(event, fake_reader) is None


def test_returns_none_when_no_forward_bars(fake_reader: FakeBarReader):
    fvg_ts = _utc(2026, 5, 4, 12)
    event = _build_fvg_event(
        event_type="1h_fvg", direction="bullish", primary=NQ,
        bar_end_utc=fvg_ts,
        fvg_high=21005.0, fvg_low=21000.0, c3_close=21010.0,
    )
    assert FvgReactionsComputer().compute(event, fake_reader) is None


def test_runner_idempotent(
    fake_reader: FakeBarReader,
    session_factory: sessionmaker[Session],
):
    fvg_ts = _utc(2026, 5, 4, 12)
    bars = _ohlc_frame([
        (fvg_ts + timedelta(hours=i + 1),
         21010 + i, 21030 + i, 21000 + i, 21020 + i)
        for i in range(5)
    ])
    fake_reader.set(symbol=NQ, timeframe="1h", df=bars)
    event = _build_fvg_event(
        event_type="1h_fvg", direction="bullish", primary=NQ,
        bar_end_utc=fvg_ts,
        fvg_high=21005.0, fvg_low=21000.0, c3_close=21010.0,
    )

    with session_factory() as db:
        db.add(event)
        db.commit()
        first = run_outcomes(
            computer=FvgReactionsComputer(), bar_reader=fake_reader, db=db,
        )
        db.commit()
        assert first.n_updated == 1
        second = run_outcomes(
            computer=FvgReactionsComputer(), bar_reader=fake_reader, db=db,
        )
        db.commit()
        assert second.n_updated == 0
        assert second.n_skipped_already_current == 1


def test_computer_is_registered():
    from app.research.outcomes import OUTCOMES, get_by_feature
    assert "fvg_reactions_v1" in OUTCOMES
    c = get_by_feature("fvg_formation")
    assert c.outcome_version == "v2"


# ---------- v2-specific tests ----------


def test_bullish_fvg_close_inside(fake_reader: FakeBarReader):
    """First tap bar CLOSES inside the gap (between fvg_low and fvg_high)."""
    fvg_ts = _utc(2026, 5, 4, 12)
    bars = _ohlc_frame([
        # Bar 1 wicks down to 21001 and CLOSES at 21002 (inside the gap (21000, 21005))
        (fvg_ts + timedelta(hours=1), 21006, 21008, 21001, 21002),
        (fvg_ts + timedelta(hours=2), 21002, 21010, 21001, 21008),
    ])
    fake_reader.set(symbol=NQ, timeframe="1h", df=bars)
    event = _build_fvg_event(
        event_type="1h_fvg", direction="bullish", primary=NQ,
        bar_end_utc=fvg_ts,
        fvg_high=21005.0, fvg_low=21000.0, c3_close=21010.0,
    )
    out = FvgReactionsComputer().compute(event, fake_reader)
    assert out is not None
    mit = out["mitigation"]
    assert mit["tapped"] is True
    assert mit["closed_inside"] is True
    assert mit["closed_through"] is False
    assert mit["bars_to_close_inside"] == 1
    assert mit["tap_bar_classification"] == "close_inside"


def test_bullish_fvg_close_through(fake_reader: FakeBarReader):
    """First tap bar CLOSES through the gap (below fvg_low)."""
    fvg_ts = _utc(2026, 5, 4, 12)
    bars = _ohlc_frame([
        # Bar 1 closes at 20998 — below fvg_low=21000 → broken FVG
        (fvg_ts + timedelta(hours=1), 21006, 21006, 20995, 20998),
        (fvg_ts + timedelta(hours=2), 20998, 21002, 20995, 21000),
    ])
    fake_reader.set(symbol=NQ, timeframe="1h", df=bars)
    event = _build_fvg_event(
        event_type="1h_fvg", direction="bullish", primary=NQ,
        bar_end_utc=fvg_ts,
        fvg_high=21005.0, fvg_low=21000.0, c3_close=21010.0,
    )
    out = FvgReactionsComputer().compute(event, fake_reader)
    assert out is not None
    mit = out["mitigation"]
    assert mit["closed_through"] is True
    assert mit["bars_to_close_through"] == 1
    assert mit["tap_bar_classification"] == "close_through"
    # close_quartiles_hit caps at 75 (close-through is "100%+")
    assert 75 in mit["close_quartiles_hit"]


def test_post_tap_reaction_bullish(fake_reader: FakeBarReader):
    """post_tap_reaction measures forward MFE/MAE FROM the tap bar's close."""
    fvg_ts = _utc(2026, 5, 4, 12)
    # Bar 1 = no tap (above gap). Bar 2 taps. Bars 3-5 rally hard from tap close.
    bars = _ohlc_frame([
        (fvg_ts + timedelta(hours=1), 21010, 21020, 21008, 21015),  # above gap
        (fvg_ts + timedelta(hours=2), 21015, 21015, 21004, 21010),  # taps wick to 21004, closes 21010
        (fvg_ts + timedelta(hours=3), 21010, 21030, 21008, 21025),
        (fvg_ts + timedelta(hours=4), 21025, 21040, 21020, 21035),
        (fvg_ts + timedelta(hours=5), 21035, 21050, 21030, 21045),
    ])
    fake_reader.set(symbol=NQ, timeframe="1h", df=bars)
    event = _build_fvg_event(
        event_type="1h_fvg", direction="bullish", primary=NQ,
        bar_end_utc=fvg_ts,
        fvg_high=21005.0, fvg_low=21000.0, c3_close=21010.0,
    )
    out = FvgReactionsComputer().compute(event, fake_reader)
    assert out is not None
    ptr = out["post_tap_reaction"]
    assert ptr is not None
    assert ptr["tap_bar_index"] == 2
    assert ptr["tap_bar_close"] == 21010.0
    assert ptr["tap_bar_classification"] == "wick_reject"
    # Forward 3 after tap = bars 3,4,5. max high = 21050. MFE in thesis = 21050 - 21010 = 40.
    f3 = ptr["forward_3_after_tap"]
    assert f3["n_bars"] == 3
    assert f3["mfe_pts_in_thesis"] == pytest.approx(40.0)
    # MAE = 21010 - min(21008, 21020, 21030) = 21010 - 21008 = 2.
    assert f3["mae_pts_against_thesis"] == pytest.approx(2.0)


def test_post_tap_reaction_none_when_untapped(fake_reader: FakeBarReader):
    """No tap → post_tap_reaction is None."""
    fvg_ts = _utc(2026, 5, 4, 12)
    bars = _ohlc_frame([
        (fvg_ts + timedelta(hours=i + 1), 21010 + i, 21020 + i, 21008 + i, 21015 + i)
        for i in range(3)
    ])
    fake_reader.set(symbol=NQ, timeframe="1h", df=bars)
    event = _build_fvg_event(
        event_type="1h_fvg", direction="bullish", primary=NQ,
        bar_end_utc=fvg_ts,
        fvg_high=21005.0, fvg_low=21000.0, c3_close=21010.0,
    )
    out = FvgReactionsComputer().compute(event, fake_reader)
    assert out is not None
    assert out["post_tap_reaction"] is None
    assert out["mitigation"]["tapped"] is False


def test_quartiles_hit_partial(fake_reader: FakeBarReader):
    """Wick reaches 60% → wick_quartiles_hit = [25, 50] (not 75 or 100)."""
    fvg_ts = _utc(2026, 5, 4, 12)
    # gap 21000-21010 (width=10). 60% wick = depth 6 = bar.low = 21004.
    bars = _ohlc_frame([
        (fvg_ts + timedelta(hours=1), 21015, 21015, 21004, 21013),
        (fvg_ts + timedelta(hours=2), 21013, 21020, 21010, 21015),
    ])
    fake_reader.set(symbol=NQ, timeframe="1h", df=bars)
    event = _build_fvg_event(
        event_type="1h_fvg", direction="bullish", primary=NQ,
        bar_end_utc=fvg_ts,
        fvg_high=21010.0, fvg_low=21000.0, c3_close=21015.0,
    )
    out = FvgReactionsComputer().compute(event, fake_reader)
    assert out is not None
    mit = out["mitigation"]
    assert mit["deepest_wick_frac"] == pytest.approx(0.6)
    assert mit["wick_quartiles_hit"] == [25, 50]
