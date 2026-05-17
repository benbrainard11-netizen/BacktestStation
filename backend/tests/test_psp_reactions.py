"""Tests for the PSP reactions outcome computer."""

from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.db import models
from app.db.session import (
    create_all,
    get_session,
    make_engine,
    make_session_factory,
)
from app.research.outcomes import psp_reactions  # noqa: F401  -- ensures register
from app.research.outcomes.runner import run_outcomes
from app.research.outcomes.psp_reactions import PspReactionsComputer
from app.services.research_events import make_event_id

UTC = timezone.utc

NQ = "NQ.c.0"
ES = "ES.c.0"
YM = "YM.c.0"


@pytest.fixture
def session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = make_engine(f"sqlite:///{tmp_path / 'psp_react.sqlite'}")
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


def _utc(year, month, day, hour=12, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=UTC)


def _ohlc_frame(rows):
    return pd.DataFrame(
        [{"open": o, "high": h, "low": l, "close": c, "volume": 100}
         for _, o, h, l, c in rows],
        index=pd.DatetimeIndex([r[0] for r in rows], tz=UTC),
    )


def _build_psp_event(
    *,
    event_type: str,
    minority_dir: str,
    primary: str,
    bar_end_utc: datetime,
    primary_close: float,
    majority_symbols: list[str],
) -> models.ResearchEvent:
    event_data = {
        "schema_version": 1,
        "detector_version": "v1",
        "minority_direction": minority_dir,
        "minority_symbols": [primary],
        "majority_symbols": majority_symbols,
        "bullish_symbols": [primary] if minority_dir == "bullish" else majority_symbols,
        "bearish_symbols": majority_symbols if minority_dir == "bullish" else [primary],
        "per_symbol_states": {
            primary: {"open": primary_close - 5, "close": primary_close,
                      "high": primary_close + 1, "low": primary_close - 6,
                      "direction": minority_dir, "body_pts": 5.0 if minority_dir == "bullish" else -5.0},
            **{m: {"open": 1000, "close": 990 if minority_dir == "bullish" else 1010,
                   "high": 1011, "low": 989, "direction": "bearish" if minority_dir == "bullish" else "bullish",
                   "body_pts": -10.0 if minority_dir == "bullish" else 10.0}
               for m in majority_symbols},
        },
    }
    return models.ResearchEvent(
        event_id=make_event_id("psp_candle_divergence", primary, bar_end_utc, event_type),
        feature_name="psp_candle_divergence",
        event_type=event_type,
        bar_end_utc=bar_end_utc.replace(tzinfo=None) if bar_end_utc.tzinfo else bar_end_utc,
        primary_symbol=primary,
        symbols=[primary, *majority_symbols],
        timeframe=event_type.split("_")[0].upper() if event_type != "daily_psp" else "1D",
        side=minority_dir,
        event_data=event_data,
        detector_version="v1",
    )


# ---------- tests ----------


def test_next_candle_continuation_bullish(fake_reader: FakeBarReader):
    """Bullish minority. Next candle closes higher (continuation)."""
    psp_ts = _utc(2026, 5, 4, 12, 0)
    next_ts = _utc(2026, 5, 4, 13, 0)
    next2 = _utc(2026, 5, 4, 14, 0)
    next3 = _utc(2026, 5, 4, 15, 0)
    next4 = _utc(2026, 5, 4, 16, 0)
    next5 = _utc(2026, 5, 4, 17, 0)
    fake_reader.set(symbol=NQ, timeframe="1h", df=_ohlc_frame([
        (next_ts, 21000, 21030, 20995, 21025),  # bullish, +25
        (next2, 21025, 21040, 21010, 21035),
        (next3, 21035, 21050, 21030, 21045),
        (next4, 21045, 21055, 21030, 21050),
        (next5, 21050, 21060, 21040, 21055),
    ]))
    fake_reader.set(symbol=ES, timeframe="1h", df=_ohlc_frame([
        (next_ts, 5000, 5005, 4990, 4992),
    ]))
    fake_reader.set(symbol=YM, timeframe="1h", df=_ohlc_frame([
        (next_ts, 40000, 40010, 39980, 39985),
    ]))

    event = _build_psp_event(
        event_type="1h_psp", minority_dir="bullish", primary=NQ,
        bar_end_utc=psp_ts, primary_close=21000.0,
        majority_symbols=[ES, YM],
    )
    out = PspReactionsComputer().compute(event, fake_reader)
    assert out is not None
    assert out["minority_direction"] == "bullish"
    assert out["next_candle"]["direction"] == "bullish"
    assert out["next_candle"]["relative_to_minority"] == "continued"
    assert out["next_candle"]["return_pts_from_psp_close"] == pytest.approx(25.0)
    # forward_5: MFE = 60 (high 21060 - close 21000), MAE = 10 (close 21000 - low 20990 wait)
    # actually low across 5 = min low = 20990? no, the lowest low is 20990 (first bar) → MAE = 21000 - 20990 = 10? hmm wait first bar low was 20995.
    # First-bar low = 20995. Min across all = 20995. MAE = 21000 - 20995 = 5.
    fwd5 = out["forward_5_candles"]
    assert fwd5["n_bars"] == 5
    assert fwd5["mfe_pts_in_minority"] == pytest.approx(60.0)
    assert fwd5["mae_pts_against_minority"] == pytest.approx(5.0)
    # majority both bearish on next → both held
    mr = out["majority_reaction"]
    assert mr["n_held"] == 2
    assert mr["n_rolled"] == 0


def test_next_candle_reversal(fake_reader: FakeBarReader):
    """Bearish minority. Next candle closes higher (reversed minority)."""
    psp_ts = _utc(2026, 5, 4, 12, 0)
    next_ts = _utc(2026, 5, 4, 13, 0)
    fake_reader.set(symbol=NQ, timeframe="1h", df=_ohlc_frame([
        (next_ts, 21000, 21030, 20990, 21025),  # bullish (against bearish minority)
        (next_ts + timedelta(hours=1), 21025, 21035, 21015, 21030),
        (next_ts + timedelta(hours=2), 21030, 21040, 21020, 21035),
        (next_ts + timedelta(hours=3), 21035, 21045, 21025, 21040),
        (next_ts + timedelta(hours=4), 21040, 21050, 21030, 21045),
    ]))
    fake_reader.set(symbol=ES, timeframe="1h", df=_ohlc_frame([
        (next_ts, 5000, 5010, 4995, 5005),  # bullish (rolled — flipped from bearish-majority to bullish next)
    ]))
    fake_reader.set(symbol=YM, timeframe="1h", df=_ohlc_frame([
        (next_ts, 40000, 40020, 39990, 40015),  # bullish (rolled)
    ]))
    event = _build_psp_event(
        event_type="1h_psp", minority_dir="bearish", primary=NQ,
        bar_end_utc=psp_ts, primary_close=21000.0,
        majority_symbols=[ES, YM],
    )
    out = PspReactionsComputer().compute(event, fake_reader)
    assert out is not None
    assert out["next_candle"]["relative_to_minority"] == "reversed"
    # MFE in minority (bearish) direction = ref_close - min_low
    # min_low across 5 bars = 20990 (first), min = 20990. MFE = 21000 - 20990 = 10.
    fwd3 = out["forward_3_candles"]
    assert fwd3["mfe_pts_in_minority"] == pytest.approx(10.0)
    # ES + YM both bullish next; minority is bearish.
    # Per the computer: state == "rolled" iff next-candle direction
    # equals minority direction. Bullish != bearish, so they HELD
    # their bullish-majority direction. (See test_majority_reaction_split
    # for the actual rolled case.)
    assert out["majority_reaction"]["n_held"] == 2
    assert out["majority_reaction"]["n_rolled"] == 0
    assert out["majority_reaction"]["all_rolled"] is False


def test_returns_none_when_forward_data_missing(fake_reader: FakeBarReader):
    """No forward bars for primary → None (caller skips)."""
    event = _build_psp_event(
        event_type="1h_psp", minority_dir="bullish", primary=NQ,
        bar_end_utc=_utc(2026, 5, 4, 12, 0), primary_close=21000.0,
        majority_symbols=[ES, YM],
    )
    out = PspReactionsComputer().compute(event, fake_reader)
    assert out is None


def test_returns_none_when_event_type_unknown(fake_reader: FakeBarReader):
    event = _build_psp_event(
        event_type="weekly_psp", minority_dir="bullish", primary=NQ,
        bar_end_utc=_utc(2026, 5, 4, 12, 0), primary_close=21000.0,
        majority_symbols=[ES, YM],
    )
    out = PspReactionsComputer().compute(event, fake_reader)
    assert out is None


def test_15m_psp_reactions_use_next_15m_candle(fake_reader: FakeBarReader):
    psp_ts = _utc(2026, 5, 4, 12, 0)
    next_ts = _utc(2026, 5, 4, 12, 15)
    fake_reader.set(symbol=NQ, timeframe="15m", df=_ohlc_frame([
        (next_ts, 21000, 21030, 20995, 21025),
        (next_ts + timedelta(minutes=15), 21025, 21040, 21010, 21035),
        (next_ts + timedelta(minutes=30), 21035, 21050, 21030, 21045),
    ]))
    fake_reader.set(symbol=ES, timeframe="15m", df=_ohlc_frame([
        (next_ts, 5000, 5005, 4990, 4992),
    ]))
    fake_reader.set(symbol=YM, timeframe="15m", df=_ohlc_frame([
        (next_ts, 40000, 40010, 39980, 39985),
    ]))
    event = _build_psp_event(
        event_type="15m_psp", minority_dir="bullish", primary=NQ,
        bar_end_utc=psp_ts, primary_close=21000.0,
        majority_symbols=[ES, YM],
    )
    out = PspReactionsComputer().compute(event, fake_reader)
    assert out is not None
    assert out["next_candle"]["relative_to_minority"] == "continued"
    assert out["forward_3_candles"]["n_bars"] == 3


def test_runner_idempotent(
    fake_reader: FakeBarReader,
    session_factory: sessionmaker[Session],
):
    psp_ts = _utc(2026, 5, 4, 12, 0)
    next_ts = _utc(2026, 5, 4, 13, 0)
    bars = _ohlc_frame([
        (next_ts + timedelta(hours=i), 21000 + i, 21010 + i, 20995 + i, 21005 + i)
        for i in range(6)
    ])
    fake_reader.set(symbol=NQ, timeframe="1h", df=bars)
    fake_reader.set(symbol=ES, timeframe="1h", df=_ohlc_frame([
        (next_ts, 5000, 5005, 4995, 5002),
    ]))
    fake_reader.set(symbol=YM, timeframe="1h", df=_ohlc_frame([
        (next_ts, 40000, 40010, 39990, 40005),
    ]))
    event = _build_psp_event(
        event_type="1h_psp", minority_dir="bullish", primary=NQ,
        bar_end_utc=psp_ts, primary_close=21000.0,
        majority_symbols=[ES, YM],
    )

    with session_factory() as db:
        db.add(event)
        db.commit()
        first = run_outcomes(
            computer=PspReactionsComputer(), bar_reader=fake_reader, db=db,
        )
        db.commit()
        assert first.n_updated == 1
        second = run_outcomes(
            computer=PspReactionsComputer(), bar_reader=fake_reader, db=db,
        )
        db.commit()
        assert second.n_updated == 0
        assert second.n_skipped_already_current == 1


def test_majority_reaction_split(fake_reader: FakeBarReader):
    """One majority symbol holds, one rolls."""
    psp_ts = _utc(2026, 5, 4, 12, 0)
    next_ts = _utc(2026, 5, 4, 13, 0)
    fake_reader.set(symbol=NQ, timeframe="1h", df=_ohlc_frame([
        (next_ts, 21000, 21010, 20995, 21005),
        (next_ts + timedelta(hours=1), 21005, 21015, 21000, 21010),
        (next_ts + timedelta(hours=2), 21010, 21020, 21005, 21015),
    ]))
    # ES bullish next (rolled — was bearish majority, now bullish like the minority)
    fake_reader.set(symbol=ES, timeframe="1h", df=_ohlc_frame([
        (next_ts, 5000, 5010, 4995, 5005),
    ]))
    # YM bearish next (held — still bearish like its prior majority)
    fake_reader.set(symbol=YM, timeframe="1h", df=_ohlc_frame([
        (next_ts, 40000, 40005, 39980, 39985),
    ]))
    event = _build_psp_event(
        event_type="1h_psp", minority_dir="bullish", primary=NQ,
        bar_end_utc=psp_ts, primary_close=21000.0,
        majority_symbols=[ES, YM],
    )
    out = PspReactionsComputer().compute(event, fake_reader)
    assert out is not None
    mr = out["majority_reaction"]
    assert mr["n_held"] == 1
    assert mr["n_rolled"] == 1
    assert mr["all_rolled"] is False


def test_computer_is_registered():
    from app.research.outcomes import OUTCOMES, get_by_feature
    assert "psp_reactions_v1" in OUTCOMES
    c = get_by_feature("psp_candle_divergence")
    assert c.outcome_version == "v1"
