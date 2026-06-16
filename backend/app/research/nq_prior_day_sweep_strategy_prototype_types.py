"""Types for the NQ prior-day sweep strategy prototype study."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Literal

EntryMethod = Literal["immediate_sweep", "first_retest", "delay_30s"]
StopMethod = Literal["fixed_8", "level_reversal_8", "sweep_extreme"]
TargetMethod = Literal["fixed_8", "fixed_12", "r_1_5"]
SequencingSource = Literal["bars", "mbp1"]
Side = Literal["long", "short"]

ENTRY_METHODS: tuple[EntryMethod, ...] = (
    "immediate_sweep",
    "first_retest",
    "delay_30s",
)
STOP_METHODS: tuple[StopMethod, ...] = ("fixed_8", "level_reversal_8", "sweep_extreme")
TARGET_METHODS: tuple[TargetMethod, ...] = ("fixed_8", "fixed_12", "r_1_5")


@dataclass(frozen=True)
class PriorDaySweepPrototypeConfig:
    """Frozen research settings for the first prior-day sweep prototype."""

    symbol: str = "NQ.c.0"
    sequencing_source: SequencingSource = "bars"
    tick_size: float = 0.25
    contract_value: float = 20.0
    qty: int = 1
    initial_equity: float = 25_000.0
    commission_per_contract: float = 2.0
    slippage_ticks: int = 1
    min_context_score: int = 2
    delayed_entry_seconds: int = 30
    retest_deadline_minutes: int = 30
    max_hold_minutes: int = 60
    forced_flat_et: dt.time = dt.time(12, 0)
    stop_buffer_pts: float = 0.50
    min_sweep_extreme_stop_pts: float = 6.0
    max_sweep_extreme_stop_pts: float = 30.0
    walk_forward_min_train_months: int = 3
    variant_ids: tuple[str, ...] = ()

    @property
    def slippage_pts(self) -> float:
        return self.slippage_ticks * self.tick_size
