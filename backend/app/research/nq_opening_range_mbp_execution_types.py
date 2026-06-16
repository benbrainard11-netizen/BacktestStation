"""Frozen settings for the NQ opening-range middle-third MBP study."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Literal

EntryStyle = Literal["immediate_break", "first_retest", "confirmation_30s"]
BreakSide = Literal["high", "low"]
TradeSide = Literal["long", "short"]

ENTRY_STYLES: tuple[EntryStyle, ...] = (
    "immediate_break",
    "first_retest",
    "confirmation_30s",
)


@dataclass(frozen=True)
class OpeningRangeMbpExecutionConfig:
    """Fixed assumptions for the middle-third OR MBP execution study."""

    symbol: str = "NQ.c.0"
    holdout_start: str = "2026-02-01"
    context_bucket: str = "middle_third"
    tick_size: float = 0.25
    slippage_ticks: int = 1
    contract_value: float = 20.0
    qty: int = 1
    commission_per_contract: float = 2.0
    confirmation_seconds: int = 30
    retest_deadline_minutes: int = 30
    rth_close_et: dt.time = dt.time(16, 0)
    walk_forward_min_train_months: int = 3

    @property
    def slippage_pts(self) -> float:
        return self.slippage_ticks * self.tick_size
