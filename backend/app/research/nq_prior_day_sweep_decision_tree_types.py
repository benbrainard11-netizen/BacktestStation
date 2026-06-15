"""Types and constants for the NQ prior-day sweep decision-tree study."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

PRIOR_DAY_LEVELS = {"prior_day_high", "prior_day_low"}
CONT = "continuation_breakout"
REV = "failed_breakout_reversal"
AMB = "ambiguous"
MISSING = "missing_mbp"


@dataclass(frozen=True)
class DecisionTreeStudyConfig:
    """Fixed settings for the prior-day sweep decision-tree study."""

    symbol: str = "NQ.c.0"
    label_source: Literal["bars", "mbp1"] = "bars"
    fixed_target_pts: float = 8.0
    feature_seconds: int = 30
    outcome_minutes: int = 60
    min_train_months: int = 3
    min_category_train_sample: int = 10
