"""Tests for the SMT HTF reactions outcome computer.

Synthetic ResearchEvent rows + FakeBarReader. No real-data dependency.
"""

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
from app.research.outcomes import smt_htf_reactions
from app.research.outcomes.runner import run_outcomes
from app.research.outcomes.smt_htf_reactions import (
    SmtHtfReactionsComputer,
)
from app.research.sessions import globex_week_for, previous_globex_week
from app.services.research_events import make_event_id

UTC = timezone.utc

NQ = "NQ.c.0"
ES = "ES.c.0"
YM = "YM.c.0"
SYMBOLS = [NQ, ES, YM]


# ---------- fixtures ----------


@pytest.fixture
def session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = make_engine(f"sqlite:///{tmp_path / 'reactions.sqlite'}")
    create_all(engine)
    return make_session_factory(engine)


class FakeBarReader:
    """Per-(symbol, timeframe) frames sliced by [start, end)."""

    def __init__(self) -> None:
        self._frames: dict[tuple[str, str], pd.DataFrame] = {}

    def set_1m(self, symbol: str, df: pd.DataFrame) -> None:
        if df.index.tz is None:
            df = df.tz_localize(UTC)
        else:
            df = df.tz_convert(UTC)
        self._frames[(symbol, "1m")] = df.sort_index()

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
        # read_bars returns a frame with ts_event as a column.
        # Mirror that to exercise the computer's index-normalization.
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


# ---------- helpers ----------


def _utc(year, month, day, hour=12, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=UTC)


def _flat_minute_bars(
    *,
    start: datetime,
    end: datetime,
    base: float,
    high_offset: float = 0.5,
    low_offset: float = 0.5,
) -> pd.DataFrame:
    """Generate 1m OHLC bars between [start, end) with constant base
    price and small +/- offsets on high/low."""
    rows = []
    cur = start
    while cur < end:
        rows.append(
            {
                "open": base,
                "high": base + high_offset,
                "low": base - low_offset,
                "close": base,
                "volume": 100,
            }
        )
        cur += timedelta(minutes=1)
    idx = pd.date_range(start=start, end=end - timedelta(minutes=1), freq="1min", tz=UTC)
    return pd.DataFrame(rows, index=idx)


def _spike_bar(df: pd.DataFrame, ts: datetime, *, high: float | None = None,
               low: float | None = None, close: float | None = None) -> pd.DataFrame:
    """Mutate one bar at `ts` to set extreme values. Returns the
    dataframe (modified in place; index must already contain ts)."""
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    ts = pd.Timestamp(ts)
    if ts not in df.index:
        raise KeyError(f"timestamp {ts} not in df index")
    if high is not None:
        df.at[ts, "high"] = high
    if low is not None:
        df.at[ts, "low"] = low
    if close is not None:
        df.at[ts, "close"] = close
    return df


def _build_event(
    *,
    side: str,
    primary: str,
    bar_end_utc: datetime,
    symbol_states: dict[str, dict[str, Any]],
    laggers: list[str],
) -> models.ResearchEvent:
    event_data = {
        "schema_version": 1,
        "detector_version": "v1",
        "first_break_symbol": primary,
        "first_break_time_utc": bar_end_utc.isoformat(),
        "first_break_price": symbol_states[primary][f"reference_{side}"] + (
            5.0 if side == "high" else -5.0
        ),
        "lagging_symbols_at_break": list(laggers),
        "confirming_symbols_at_break": [],
        "symbol_states": symbol_states,
        "later_confirmations": [],
        "did_all_confirm_by_window_end": False,
        "divergence_duration_seconds": None,
        "tracking_timeframe": "4h",
        "side": side,
        "reference_type": "previous_week",
    }
    return models.ResearchEvent(
        event_id=make_event_id(
            "smt_htf_reference_divergence", primary, bar_end_utc, "weekly_smt"
        ),
        feature_name="smt_htf_reference_divergence",
        event_type="weekly_smt",
        bar_end_utc=bar_end_utc.replace(tzinfo=None) if bar_end_utc.tzinfo else bar_end_utc,
        primary_symbol=primary,
        symbols=SYMBOLS,
        timeframe="4H",
        side=side,
        event_data=event_data,
        detector_version="v1",
    )


# ---------- tests ----------


def test_high_side_smt_outcome_shape(fake_reader: FakeBarReader):
    """High-side weekly SMT: NQ took prev-week-high. Verify outcome
    block shape + thesis_direction + intra-period MFE/MAE math."""
    # Period N spans the week containing 2026-05-04 (Mon)
    n_period = globex_week_for(_utc(2026, 5, 4, 12, 0))
    n1_period = globex_week_for(n_period.end_utc + timedelta(seconds=1))
    n2_period = globex_week_for(n1_period.end_utc + timedelta(seconds=1))

    # Reference levels (computed from prev_period — we don't load
    # those bars in the outcome computer; they're already in event_data)
    ref_high_nq = 21000.0
    ref_low_nq = 20850.0

    # Period N bars for NQ: base 21010 (above the 21000 reference, so
    # primary stayed swept). Mid-period dip to 20900 then recovery.
    n_bars = _flat_minute_bars(
        start=n_period.start_utc, end=n_period.end_utc, base=21010.0,
    )
    # Spike a bar to 21080 on 2026-05-05 14:00 UTC (intra-period high)
    _spike_bar(n_bars, _utc(2026, 5, 5, 14, 0), high=21080.0, low=21010.0)
    # Spike another to 20960 (dipping below ref_high but not below
    # ref_low) on 2026-05-06 14:00 UTC
    _spike_bar(n_bars, _utc(2026, 5, 6, 14, 0), high=21010.0, low=20960.0)
    # Force last bar (period close) to close at 21030
    last_ts = n_bars.index[-1].to_pydatetime()
    _spike_bar(n_bars, last_ts, close=21030.0)

    # N+1 bars: NQ trades down hard, taking N's low (21010 - 0.5 = 20840.5? no wait)
    # NQ's period-N low = min of low column = 20840.5 (default offset) but
    # we spiked the 14:00 bar's low to 20960 so actual min is 20840.5.
    # Want N+1 to take this — set N+1 low to 20800.
    n1_bars = _flat_minute_bars(
        start=n1_period.start_utc, end=n1_period.end_utc, base=20950.0,
    )
    _spike_bar(n1_bars, _utc(2026, 5, 12, 14, 0), low=20800.0)
    # Force N+1 close to 20900 (below n_close 21030 → moved with thesis)
    _spike_bar(n1_bars, n1_bars.index[-1].to_pydatetime(), close=20900.0)

    # N+2 bars: stays around 20950, doesn't take new highs or lows
    n2_bars = _flat_minute_bars(
        start=n2_period.start_utc, end=n2_period.end_utc, base=20950.0,
    )
    _spike_bar(n2_bars, n2_bars.index[-1].to_pydatetime(), close=20940.0)

    fake_reader.set_1m(NQ, n_bars)
    fake_reader.set_1m(NQ, pd.concat([n_bars, n1_bars, n2_bars]).sort_index())

    event = _build_event(
        side="high",
        primary=NQ,
        bar_end_utc=_utc(2026, 5, 5, 12, 0),
        symbol_states={
            NQ: {"reference_high": ref_high_nq, "reference_low": ref_low_nq,
                 "broke_high": True, "broke_low": False},
            ES: {"reference_high": 5000.0, "reference_low": 4900.0,
                 "broke_high": False, "broke_low": False},
            YM: {"reference_high": 40000.0, "reference_low": 39000.0,
                 "broke_high": True, "broke_low": False},
        },
        laggers=[ES, YM],
    )

    computer = SmtHtfReactionsComputer()
    outcome = computer.compute(event, fake_reader)
    assert outcome is not None

    assert outcome["outcome_version"] == "v2"
    assert outcome["thesis_direction"] == "down"
    pc = outcome["period_close"]
    assert pc["primary_close_price"] == pytest.approx(21030.0)
    # v2: extreme timestamps present
    assert pc["primary_period_high_ts"] is not None
    assert pc["primary_period_low_ts"] is not None
    # ES is unswept (broke_high=False), YM is swept (broke_high=True)
    assert pc["lagging_unswept_at_close"] == [ES]
    assert pc["lagging_swept_at_close"] == [YM]
    assert pc["smt_active_for_side_at_close"] is True  # ES still lagging
    assert pc["primary_still_swept_at_close"] is True  # 21030 > 21000

    np1 = outcome["next_period"]
    assert np1["primary_close_price"] == pytest.approx(20900.0)
    assert np1["primary_return_pts"] == pytest.approx(20900.0 - 21030.0)
    # Took N's low? N's low = 20840.5 (default offset); N+1's low = 20800 → True
    assert np1["primary_took_period_n_low"] is True
    assert np1["thesis_confirmed_strict"] is True
    assert np1["close_moved_with_thesis"] is True
    # MFE in thesis direction = n_close (21030) - n+1 low (20800) = 230
    assert np1["mfe_pts_in_thesis"] == pytest.approx(230.0)


def test_low_side_smt_outcome_thesis_up(fake_reader: FakeBarReader):
    """Low-side SMT: NQ took prev-week-low. Thesis = expansion UP."""
    n_period = globex_week_for(_utc(2026, 5, 4, 12, 0))
    n1_period = globex_week_for(n_period.end_utc + timedelta(seconds=1))
    n2_period = globex_week_for(n1_period.end_utc + timedelta(seconds=1))

    ref_high_nq = 21000.0
    ref_low_nq = 20850.0

    # NQ traded BELOW ref_low at some point, ended below the ref_low
    n_bars = _flat_minute_bars(
        start=n_period.start_utc, end=n_period.end_utc, base=20830.0,
    )
    _spike_bar(n_bars, n_bars.index[-1].to_pydatetime(), close=20840.0)

    # N+1: takes N's high → thesis confirmed
    n1_bars = _flat_minute_bars(
        start=n1_period.start_utc, end=n1_period.end_utc, base=20900.0,
    )
    n_high = float(n_bars["high"].max())
    _spike_bar(n1_bars, _utc(2026, 5, 12, 14, 0), high=n_high + 50.0)
    _spike_bar(n1_bars, n1_bars.index[-1].to_pydatetime(), close=20950.0)

    n2_bars = _flat_minute_bars(
        start=n2_period.start_utc, end=n2_period.end_utc, base=20970.0,
    )

    fake_reader.set_1m(NQ, pd.concat([n_bars, n1_bars, n2_bars]).sort_index())

    event = _build_event(
        side="low",
        primary=NQ,
        bar_end_utc=_utc(2026, 5, 5, 12, 0),
        symbol_states={
            NQ: {"reference_high": ref_high_nq, "reference_low": ref_low_nq,
                 "broke_high": False, "broke_low": True},
            ES: {"reference_high": 5000.0, "reference_low": 4900.0,
                 "broke_high": False, "broke_low": False},
            YM: {"reference_high": 40000.0, "reference_low": 39000.0,
                 "broke_high": False, "broke_low": False},
        },
        laggers=[ES, YM],
    )

    computer = SmtHtfReactionsComputer()
    outcome = computer.compute(event, fake_reader)
    assert outcome is not None
    assert outcome["thesis_direction"] == "up"
    pc = outcome["period_close"]
    # Primary closed at 20840 < 20850 → still swept on low side
    assert pc["primary_still_swept_at_close"] is True
    # ES + YM both unswept on low side
    assert sorted(pc["lagging_unswept_at_close"]) == sorted([ES, YM])
    assert pc["smt_active_for_side_at_close"] is True

    np1 = outcome["next_period"]
    assert np1["primary_took_period_n_high"] is True
    assert np1["thesis_confirmed_strict"] is True
    assert np1["mfe_pts_in_thesis"] > 0


def test_outcome_returns_none_when_period_n_data_missing(fake_reader: FakeBarReader):
    """Missing N period bars → None outcome (caller skips, doesn't crash)."""
    event = _build_event(
        side="high",
        primary=NQ,
        bar_end_utc=_utc(2026, 5, 5, 12, 0),
        symbol_states={
            NQ: {"reference_high": 21000.0, "reference_low": 20850.0,
                 "broke_high": True, "broke_low": False},
            ES: {"reference_high": 5000.0, "reference_low": 4900.0,
                 "broke_high": False, "broke_low": False},
            YM: {"reference_high": 40000.0, "reference_low": 39000.0,
                 "broke_high": False, "broke_low": False},
        },
        laggers=[ES, YM],
    )
    computer = SmtHtfReactionsComputer()
    out = computer.compute(event, fake_reader)
    assert out is None


def test_runner_idempotent_on_outcome_version(
    fake_reader: FakeBarReader,
    session_factory: sessionmaker[Session],
):
    """Re-running the runner over the same events with the same
    outcome_version is a no-op."""
    n_period = globex_week_for(_utc(2026, 5, 4, 12, 0))
    n1_period = globex_week_for(n_period.end_utc + timedelta(seconds=1))
    n2_period = globex_week_for(n1_period.end_utc + timedelta(seconds=1))

    bars = pd.concat([
        _flat_minute_bars(start=n_period.start_utc, end=n_period.end_utc, base=21010),
        _flat_minute_bars(start=n1_period.start_utc, end=n1_period.end_utc, base=20950),
        _flat_minute_bars(start=n2_period.start_utc, end=n2_period.end_utc, base=20950),
    ]).sort_index()
    fake_reader.set_1m(NQ, bars)

    event = _build_event(
        side="high",
        primary=NQ,
        bar_end_utc=_utc(2026, 5, 5, 12, 0),
        symbol_states={
            NQ: {"reference_high": 21000.0, "reference_low": 20850.0,
                 "broke_high": True, "broke_low": False},
            ES: {"reference_high": 5000.0, "reference_low": 4900.0,
                 "broke_high": False, "broke_low": False},
            YM: {"reference_high": 40000.0, "reference_low": 39000.0,
                 "broke_high": False, "broke_low": False},
        },
        laggers=[ES, YM],
    )

    with session_factory() as db:
        db.add(event)
        db.commit()

        computer = SmtHtfReactionsComputer()
        first = run_outcomes(computer=computer, bar_reader=fake_reader, db=db)
        db.commit()
        assert first.n_updated == 1

        second = run_outcomes(computer=computer, bar_reader=fake_reader, db=db)
        db.commit()
        assert second.n_updated == 0
        assert second.n_skipped_already_current == 1


def test_runner_force_recomputes(
    fake_reader: FakeBarReader,
    session_factory: sessionmaker[Session],
):
    """force=True bypasses the version-skip."""
    n_period = globex_week_for(_utc(2026, 5, 4, 12, 0))
    n1_period = globex_week_for(n_period.end_utc + timedelta(seconds=1))
    n2_period = globex_week_for(n1_period.end_utc + timedelta(seconds=1))
    bars = pd.concat([
        _flat_minute_bars(start=n_period.start_utc, end=n_period.end_utc, base=21010),
        _flat_minute_bars(start=n1_period.start_utc, end=n1_period.end_utc, base=20950),
        _flat_minute_bars(start=n2_period.start_utc, end=n2_period.end_utc, base=20950),
    ]).sort_index()
    fake_reader.set_1m(NQ, bars)

    event = _build_event(
        side="high",
        primary=NQ,
        bar_end_utc=_utc(2026, 5, 5, 12, 0),
        symbol_states={
            NQ: {"reference_high": 21000.0, "reference_low": 20850.0,
                 "broke_high": True, "broke_low": False},
            ES: {"reference_high": 5000.0, "reference_low": 4900.0,
                 "broke_high": False, "broke_low": False},
            YM: {"reference_high": 40000.0, "reference_low": 39000.0,
                 "broke_high": False, "broke_low": False},
        },
        laggers=[ES, YM],
    )

    with session_factory() as db:
        db.add(event)
        db.commit()
        computer = SmtHtfReactionsComputer()
        run_outcomes(computer=computer, bar_reader=fake_reader, db=db)
        db.commit()
        forced = run_outcomes(
            computer=computer, bar_reader=fake_reader, db=db, force=True,
        )
        db.commit()
        assert forced.n_updated == 1
        assert forced.n_skipped_already_current == 0


def test_smt_active_at_close_false_when_all_laggers_resolved(
    fake_reader: FakeBarReader,
):
    """If all laggers eventually broke, smt_active_for_side_at_close = False."""
    n_period = globex_week_for(_utc(2026, 5, 4, 12, 0))
    n1_period = globex_week_for(n_period.end_utc + timedelta(seconds=1))
    n2_period = globex_week_for(n1_period.end_utc + timedelta(seconds=1))
    bars = pd.concat([
        _flat_minute_bars(start=n_period.start_utc, end=n_period.end_utc, base=21010),
        _flat_minute_bars(start=n1_period.start_utc, end=n1_period.end_utc, base=20950),
        _flat_minute_bars(start=n2_period.start_utc, end=n2_period.end_utc, base=20950),
    ]).sort_index()
    fake_reader.set_1m(NQ, bars)

    event = _build_event(
        side="high",
        primary=NQ,
        bar_end_utc=_utc(2026, 5, 5, 12, 0),
        symbol_states={
            NQ: {"reference_high": 21000.0, "reference_low": 20850.0,
                 "broke_high": True, "broke_low": False},
            ES: {"reference_high": 5000.0, "reference_low": 4900.0,
                 "broke_high": True, "broke_low": False},  # eventually broke
            YM: {"reference_high": 40000.0, "reference_low": 39000.0,
                 "broke_high": True, "broke_low": False},  # eventually broke
        },
        laggers=[ES, YM],
    )
    out = SmtHtfReactionsComputer().compute(event, fake_reader)
    assert out is not None
    pc = out["period_close"]
    assert pc["lagging_unswept_at_close"] == []
    assert pc["smt_active_for_side_at_close"] is False


def test_computer_is_registered():
    from app.research.outcomes import OUTCOMES, get_by_feature
    assert "smt_htf_reactions_v1" in OUTCOMES
    c = get_by_feature("smt_htf_reference_divergence")
    assert c.outcome_version == "v2"
