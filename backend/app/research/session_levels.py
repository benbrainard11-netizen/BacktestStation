"""Canonical futures session level definitions.

This module separates the period being measured from the eventual sweep
logic. `prev_td_low` means previous full Globex trading-day low; it is
not interchangeable with `prev_rth_low`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

import pandas as pd

from app.research.reference_levels import compute_reference_level
from app.research.sessions import (
    ET,
    GlobexPeriod,
    globex_day_for,
    previous_globex_day,
    previous_trading_date,
    rth_session_for_trading_date,
    session_for_trading_date,
)

LevelSide = Literal["high", "low"]
SESSION_NAMES = ("asia", "london", "ny")


@dataclass(frozen=True, slots=True)
class SessionLevelSpec:
    """A level family and the exact period used to compute it."""

    family: str
    side: LevelSide
    period: GlobexPeriod

    @property
    def name(self) -> str:
        return f"{self.family}_{self.side}"

    @property
    def start_utc(self) -> datetime:
        return self.period.start_utc

    @property
    def end_utc(self) -> datetime:
        return self.period.end_utc


@dataclass(frozen=True, slots=True)
class ComputedSessionLevel:
    """A concrete price level computed from a SessionLevelSpec."""

    spec: SessionLevelSpec
    value: float
    level_set_ts_utc: datetime
    n_bars: int

    @property
    def name(self) -> str:
        return self.spec.name

    @property
    def family(self) -> str:
        return self.spec.family

    @property
    def side(self) -> LevelSide:
        return self.spec.side


def level_specs_for_event_time(ref: datetime) -> list[SessionLevelSpec]:
    """Return non-lookahead canonical level periods available at `ref`.

    Always includes:
      - previous full Globex trading day (`prev_td_high/low`)
      - previous RTH (`prev_rth_high/low`)
      - previous trading day's Asia/London/NY sessions

    Also includes completed sessions from the current trading day, such as
    `curr_td_asia_low` during London/NY and `curr_td_london_low` during NY.
    In-progress sessions are intentionally omitted; those should be modeled
    as developing levels with a different family name.
    """
    if ref.tzinfo is None:
        ref = ref.replace(tzinfo=timezone.utc)
    current_td = globex_day_for(ref).end_utc.astimezone(ET).date()
    prev_td = previous_trading_date(current_td)

    out: list[SessionLevelSpec] = []
    out.extend(_both_sides("prev_td", previous_globex_day(ref)))
    out.extend(_both_sides("prev_rth", rth_session_for_trading_date(prev_td)))

    for session_name in SESSION_NAMES:
        out.extend(
            _both_sides(
                f"prev_td_{session_name}",
                session_for_trading_date(prev_td, session_name),
            )
        )

    for session_name in SESSION_NAMES:
        period = session_for_trading_date(current_td, session_name)
        if period.end_utc <= _to_utc(ref):
            out.extend(_both_sides(f"curr_td_{session_name}", period))

    return out


def compute_session_levels(
    bars: pd.DataFrame,
    specs: list[SessionLevelSpec],
    *,
    ts_col: str | None = None,
    high_col: str = "high",
    low_col: str = "low",
) -> list[ComputedSessionLevel]:
    """Compute concrete prices for session level specs from OHLC bars."""
    levels: list[ComputedSessionLevel] = []
    for spec in specs:
        ref = compute_reference_level(
            bars,
            side=spec.side,
            start_utc=spec.start_utc,
            end_utc=spec.end_utc,
            high_col=high_col,
            low_col=low_col,
            ts_col=ts_col,
        )
        if ref is None:
            continue
        levels.append(
            ComputedSessionLevel(
                spec=spec,
                value=ref.value,
                level_set_ts_utc=ref.ts_utc,
                n_bars=ref.n_bars,
            )
        )
    return levels


def _both_sides(family: str, period: GlobexPeriod) -> list[SessionLevelSpec]:
    return [
        SessionLevelSpec(family=family, side="high", period=period),
        SessionLevelSpec(family=family, side="low", period=period),
    ]


def _to_utc(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc)
