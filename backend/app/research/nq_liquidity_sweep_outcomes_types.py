"""Types for the NQ liquidity sweep outcome study."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Literal

SweepSide = Literal["high", "low"]
OutcomeLabel = Literal[
    "continuation_breakout",
    "failed_breakout_reversal",
    "ambiguous",
]


@dataclass(frozen=True)
class LiquiditySweepStudyConfig:
    """Fixed research settings for the baseline sweep outcome study."""

    symbol: str = "NQ.c.0"
    tick_size: float = 0.25
    sweep_buffer_ticks: int = 1
    rth_open_et: dt.time = dt.time(9, 30)
    sweep_start_et: dt.time = dt.time(9, 35)
    rth_close_et: dt.time = dt.time(16, 0)
    globex_close_et: dt.time = dt.time(17, 0)
    overnight_freeze_et: dt.time = dt.time(9, 30)
    feature_seconds: int = 30
    outcome_minutes: int = 60
    pre_sweep_range_minutes: int = 15
    min_outcome_pts: float = 8.0
    bootstrap_iterations: int = 300
    permutation_iterations: int = 300
    random_seed: int = 42

    @property
    def sweep_buffer_pts(self) -> float:
        return self.sweep_buffer_ticks * self.tick_size


@dataclass(frozen=True)
class SweepLevel:
    session_date: dt.date
    level_type: str
    level_price: float
    sweep_side: SweepSide
    source_start_utc: dt.datetime
    source_end_utc: dt.datetime


@dataclass(frozen=True)
class SweepEvent:
    event_id: str
    session_date: dt.date
    level_type: str
    level_price: float
    sweep_side: SweepSide
    sweep_ts: dt.datetime
    sweep_price: float
    ticks_through_level: float
    time_of_day: str
    pre_sweep_15m_range_pts: float | None
    outcome_distance_pts: float
    outcome_label: OutcomeLabel
    continuation_hit_ts: dt.datetime | None
    reversal_hit_ts: dt.datetime | None
