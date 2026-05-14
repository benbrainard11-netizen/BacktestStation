"""Tests for the liquidity_sweep reactions outcome computer."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.db import models
from app.db.session import create_all, make_engine, make_session_factory
from app.research.outcomes import liquidity_sweep_reactions  # noqa: F401
from app.research.outcomes.liquidity_sweep_reactions import (
    LiquiditySweepReactionsComputer,
)
from app.research.outcomes.runner import run_outcomes
from app.services.research_events import make_event_id

UTC = timezone.utc
NQ = "NQ.c.0"


@pytest.fixture
def session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = make_engine(f"sqlite:///{tmp_path / 'sweep_react.sqlite'}")
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
        return sliced.reset_index().rename(columns={"index": "ts_event"})


@pytest.fixture
def fake_reader() -> FakeBarReader:
    return FakeBarReader()


def _utc(year, month, day, hour=12):
    return datetime(year, month, day, hour, tzinfo=UTC)


def _ohlc_frame(rows):
    return pd.DataFrame(
        [{"open": o, "high": h, "low": low, "close": c, "volume": 100}
         for _, o, h, low, c in rows],
        index=pd.DatetimeIndex([r[0] for r in rows], tz=UTC),
    )


def _build_sweep_event(
    *,
    mode: str,
    ref_type: str, ref_side: str, thesis: str,
    primary: str,
    bar_end_utc: datetime,
    ref_price: float,
    manip_high: float, manip_low: float, manip_close: float,
) -> models.ResearchEvent:
    timeframe_map = {
        "pdl_1h": "1H", "pdl_4h": "4H", "pdh_1h": "1H", "pdh_4h": "4H",
        "pwl_4h": "4H", "pwl_daily": "1D", "pwh_4h": "4H", "pwh_daily": "1D",
        "unknown_mode": "1H",
    }
    event_data = {
        "schema_version": 1,
        "detector_version": "v1",
        "mode": mode,
        "ref_type": ref_type,
        "ref_side": ref_side,
        "thesis": thesis,
        "tracking_timeframe": "1h",
        "swept_reference": {
            "type": ref_type, "side": ref_side, "level_price": ref_price,
            "level_set_ts_utc": "2026-05-04T00:00:00+00:00",
            "prior_period_label": "globex_day",
            "prior_period_start_utc": "2026-05-03T22:00:00+00:00",
            "prior_period_end_utc": "2026-05-04T22:00:00+00:00",
        },
        "manipulation_candle": {
            "ts_utc": bar_end_utc.isoformat(),
            "open": manip_close - 5, "high": manip_high,
            "low": manip_low, "close": manip_close,
        },
        "sweep_depth_pts": (
            ref_price - manip_low if ref_side == "low" else manip_high - ref_price
        ),
    }
    return models.ResearchEvent(
        event_id=make_event_id("liquidity_sweep", primary, bar_end_utc, mode),
        feature_name="liquidity_sweep",
        event_type=mode,
        bar_end_utc=bar_end_utc.replace(tzinfo=None) if bar_end_utc.tzinfo else bar_end_utc,
        primary_symbol=primary,
        symbols=[primary],
        timeframe=timeframe_map[mode],
        side=ref_side,
        event_data=event_data,
        detector_version="v1",
    )


# ---------- tests ----------


def test_recovery_and_continuation_bullish(fake_reader: FakeBarReader):
    """Sweep low at 21050. Forward bar 1 closes at 21070 (recovers
    above ref). No continuation deeper than manip low."""
    sweep_ts = _utc(2026, 5, 5, 12)
    bars = _ohlc_frame([
        (sweep_ts + timedelta(hours=1), 21045, 21075, 21042, 21070),
        (sweep_ts + timedelta(hours=2), 21070, 21080, 21065, 21075),
    ])
    fake_reader.set(symbol=NQ, timeframe="1h", df=bars)
    event = _build_sweep_event(
        mode="pdl_1h", ref_type="pdl", ref_side="low", thesis="bullish",
        primary=NQ, bar_end_utc=sweep_ts,
        ref_price=21050, manip_high=21055, manip_low=21040, manip_close=21045,
    )
    out = LiquiditySweepReactionsComputer().compute(event, fake_reader)
    assert out is not None
    assert out["outcome_version"] == "v2"
    rec = out["swept_level_recovery"]
    assert rec["level_recovered"] is True
    assert rec["bars_to_recovery"] == 1
    cont = out["forward_continuation"]
    # bar 1 low = 21042 — that IS lower than manip_low=21040? No, 21042 > 21040.
    # bar 1 low 21042 > manip_low 21040 → no continuation.
    assert cont["continued"] is False
    assert out["swept_reference_reaction"]["close_above_reference"] is True
    assert out["manipulation_range_reaction"]["closed_above_manipulation_high"] is True


def test_continuation_no_recovery_bullish(fake_reader: FakeBarReader):
    """Sweep low. Forward bars keep going lower → no recovery, continuation."""
    sweep_ts = _utc(2026, 5, 5, 12)
    bars = _ohlc_frame([
        (sweep_ts + timedelta(hours=1), 21045, 21048, 21030, 21035),  # deeper low
        (sweep_ts + timedelta(hours=2), 21035, 21040, 21020, 21025),
    ])
    fake_reader.set(symbol=NQ, timeframe="1h", df=bars)
    event = _build_sweep_event(
        mode="pdl_1h", ref_type="pdl", ref_side="low", thesis="bullish",
        primary=NQ, bar_end_utc=sweep_ts,
        ref_price=21050, manip_high=21055, manip_low=21040, manip_close=21045,
    )
    out = LiquiditySweepReactionsComputer().compute(event, fake_reader)
    assert out is not None
    assert out["swept_level_recovery"]["level_recovered"] is False
    cont = out["forward_continuation"]
    assert cont["continued"] is True
    assert cont["bars_to_first_extension"] == 1
    # deepest extension = 21040 - 21020 = 20 (bar 2's low went to 21020)
    assert cont["deepest_extension_pts"] == pytest.approx(20.0)


def test_no_ob_confirmation_when_no_ob_events(
    fake_reader: FakeBarReader,
    session_factory: sessionmaker[Session],
):
    """If no OB events exist for this primary, ob_confirmation = no."""
    sweep_ts = _utc(2026, 5, 5, 12)
    bars = _ohlc_frame([
        (sweep_ts + timedelta(hours=i), 21045 + i, 21075 + i, 21042 + i, 21070 + i)
        for i in range(1, 4)
    ])
    fake_reader.set(symbol=NQ, timeframe="1h", df=bars)
    event = _build_sweep_event(
        mode="pdl_1h", ref_type="pdl", ref_side="low", thesis="bullish",
        primary=NQ, bar_end_utc=sweep_ts,
        ref_price=21050, manip_high=21055, manip_low=21040, manip_close=21045,
    )
    with session_factory() as db:
        db.add(event)
        db.commit()
        result = run_outcomes(
            computer=LiquiditySweepReactionsComputer(),
            bar_reader=fake_reader, db=db,
        )
        db.commit()
        assert result.n_updated == 1
        # Reload event to check outcomes.
        db.refresh(event)
        ob_conf = event.outcomes["ob_confirmation"]
        assert ob_conf["did_confirm"] is False
        assert ob_conf["bars_to_first_ob"] is None


def test_ob_confirmation_join(
    fake_reader: FakeBarReader,
    session_factory: sessionmaker[Session],
):
    """Sweep at t. OB event at t+2h with matching primary, ref, direction.
    Should be picked up as the confirming OB."""
    sweep_ts = _utc(2026, 5, 5, 12)
    bars = _ohlc_frame([
        (sweep_ts + timedelta(hours=i), 21045 + i, 21075 + i, 21042 + i, 21070 + i)
        for i in range(1, 4)
    ])
    fake_reader.set(symbol=NQ, timeframe="1h", df=bars)
    sweep = _build_sweep_event(
        mode="pdl_1h", ref_type="pdl", ref_side="low", thesis="bullish",
        primary=NQ, bar_end_utc=sweep_ts,
        ref_price=21050, manip_high=21055, manip_low=21040, manip_close=21045,
    )
    # Create an OB event 2h after sweep.
    ob_ts = sweep_ts + timedelta(hours=2)
    ob = models.ResearchEvent(
        event_id=make_event_id("order_block", NQ, ob_ts, "swept_pdl_1h"),
        feature_name="order_block",
        event_type="swept_pdl_1h",
        bar_end_utc=ob_ts.replace(tzinfo=None),
        primary_symbol=NQ,
        symbols=[NQ],
        timeframe="1H",
        side="bullish",
        event_data={"detector_version": "v1"},
        detector_version="v1",
    )
    with session_factory() as db:
        db.add(sweep)
        db.add(ob)
        db.commit()
        result = run_outcomes(
            computer=LiquiditySweepReactionsComputer(),
            bar_reader=fake_reader, db=db,
        )
        db.commit()
        # sweep got outcomes; the ob also got outcomes (None — no OB
        # outcomes computer call here but the runner only operates on
        # the matching feature_name=liquidity_sweep, so OB is unaffected).
        assert result.n_updated == 1
        db.refresh(sweep)
        ob_conf = sweep.outcomes["ob_confirmation"]
        assert ob_conf["did_confirm"] is True
        assert ob_conf["first_ob_mode"] == "swept_pdl_1h"
        # bars_to_first_ob: ob_ts - sweep_ts = 2h. tf_minutes=60. 2h / 1h = 2.
        assert ob_conf["bars_to_first_ob"] == 2


def test_returns_none_for_unknown_mode(fake_reader: FakeBarReader):
    sweep_ts = _utc(2026, 5, 5, 12)
    event = _build_sweep_event(
        mode="unknown_mode", ref_type="pdl", ref_side="low", thesis="bullish",
        primary=NQ, bar_end_utc=sweep_ts,
        ref_price=21050, manip_high=21055, manip_low=21040, manip_close=21045,
    )
    assert LiquiditySweepReactionsComputer().compute(event, fake_reader) is None


def test_computer_is_registered():
    from app.research.outcomes import OUTCOMES, get_by_feature
    assert "liquidity_sweep_reactions_v2" in OUTCOMES
    c = get_by_feature("liquidity_sweep")
    assert c.outcome_version == "v2"
