"""ML snapshot feature registry.

This module is intentionally small and explicit. It records timing rules for
features used by snapshot matrices so model scripts do not have to infer
whether a column is legal at a given prediction timestamp.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

SnapshotName = Literal["at_fire", "at_period_close"]


@dataclass(frozen=True, slots=True)
class FeatureRule:
    prefix: str
    family: str
    valid_snapshots: tuple[SnapshotName, ...]
    description: str


@dataclass(frozen=True, slots=True)
class LabelRule:
    prefix: str
    horizon: str
    description: str


SMT_LAG_MIN = {"previous_day_smt": 60, "weekly_smt": 240}
_SMT_MTF_BASE_LAG_MIN = {
    "15m_prev_candle_smt": 0,
    "30m_prev_candle_smt": 0,
    "1h_prev_candle_smt": 0,
    "90m_prev_candle_smt": 0,
    "4h_prev_candle_smt": 0,
    "6h_prev_candle_smt": 0,
}
SMT_MTF_LAG_MIN = {
    **_SMT_MTF_BASE_LAG_MIN,
    **{
        f"{event_type}_{side}": lag
        for event_type, lag in _SMT_MTF_BASE_LAG_MIN.items()
        for side in ("high", "low")
    },
}
PSP_LAG_MIN = {
    "15m_psp": 15,
    "30m_psp": 30,
    "1h_psp": 60,
    "4h_psp": 240,
    "daily_psp": 24 * 60,
}
FVG_LAG_MIN = {"15m_fvg": 15, "1h_fvg": 60, "4h_fvg": 240, "daily_fvg": 24 * 60}
OB_LAG_MIN = {
    "swept_pdl_1h": 60, "swept_pdl_4h": 240,
    "swept_pdh_1h": 60, "swept_pdh_4h": 240,
    "swept_pwl_4h": 240, "swept_pwl_daily": 24 * 60,
    "swept_pwh_4h": 240, "swept_pwh_daily": 24 * 60,
    "swept_asia_low_1h": 60, "swept_asia_high_1h": 60,
    "swept_london_low_1h": 60, "swept_london_high_1h": 60,
    "swept_ny_low_1h": 60, "swept_ny_high_1h": 60,
}
SWEEP_LAG_MIN = {
    "pdl_1h": 60, "pdl_4h": 240,
    "pdh_1h": 60, "pdh_4h": 240,
    "pwl_4h": 240, "pwl_daily": 24 * 60,
    "pwh_4h": 240, "pwh_daily": 24 * 60,
    "asia_low_1h": 60, "asia_high_1h": 60,
    "london_low_1h": 60, "london_high_1h": 60,
    "ny_low_1h": 60, "ny_high_1h": 60,
}
DISP_LAG_MIN = {
    "15m_disp": 15,
    "30m_disp": 30,
    "1h_disp": 60,
    "4h_disp": 240,
    "daily_disp": 24 * 60,
}
SWING_LAG_MIN = {
    "pivot_3_1h": 4 * 60,
    "pivot_5_1h": 6 * 60,
    "pivot_3_4h": 4 * 240,
    "pivot_5_4h": 6 * 240,
    "pivot_5_daily": 6 * 24 * 60,
}
EQL_LAG_MIN = {
    "eq_pivot_3_1h_5pts": SWING_LAG_MIN["pivot_3_1h"],
    "eq_pivot_3_1h_15pts": SWING_LAG_MIN["pivot_3_1h"],
    "eq_pivot_5_1h_5pts": SWING_LAG_MIN["pivot_5_1h"],
    "eq_pivot_5_1h_15pts": SWING_LAG_MIN["pivot_5_1h"],
    "eq_pivot_3_4h_15pts": SWING_LAG_MIN["pivot_3_4h"],
    "eq_pivot_5_4h_15pts": SWING_LAG_MIN["pivot_5_4h"],
    "eq_pivot_5_daily_30pts": SWING_LAG_MIN["pivot_5_daily"],
}


FEATURE_RULES: tuple[FeatureRule, ...] = (
    FeatureRule(
        prefix="asof.",
        family="snapshot_metadata",
        valid_snapshots=("at_fire", "at_period_close"),
        description="Snapshot identity, cutoff timestamp, and label window timestamps.",
    ),
    FeatureRule(
        prefix="anchor.",
        family="anchor_metadata",
        valid_snapshots=("at_fire", "at_period_close"),
        description="Anchor event identifiers and raw event-time metadata.",
    ),
    FeatureRule(
        prefix="ts.",
        family="time",
        valid_snapshots=("at_fire", "at_period_close"),
        description="Calendar features computed from the snapshot timestamp.",
    ),
    FeatureRule(
        prefix="smt.",
        family="smt_event_time",
        valid_snapshots=("at_fire", "at_period_close"),
        description="Filtered SMT fields knowable at first divergent break.",
    ),
    FeatureRule(
        prefix="fvg.",
        family="fvg_event_time",
        valid_snapshots=("at_fire", "at_period_close"),
        description="Filtered FVG event-time fields knowable at detector fire.",
    ),
    FeatureRule(
        prefix="sweep.",
        family="sweep_event_time",
        valid_snapshots=("at_fire", "at_period_close"),
        description="Filtered liquidity-sweep event-time fields knowable at detector fire.",
    ),
    FeatureRule(
        prefix="disp.",
        family="displacement_event_time",
        valid_snapshots=("at_fire", "at_period_close"),
        description="Filtered displacement-candle event-time fields knowable at detector fire.",
    ),
    FeatureRule(
        prefix="ob.",
        family="order_block_event_time",
        valid_snapshots=("at_fire", "at_period_close"),
        description="Filtered order-block event-time fields knowable at detector fire.",
    ),
    FeatureRule(
        prefix="psp.",
        family="psp_event_time",
        valid_snapshots=("at_fire", "at_period_close"),
        description="Filtered PSP event-time fields knowable at detector fire.",
    ),
    FeatureRule(
        prefix="swing.",
        family="swing_pivot_event_time",
        valid_snapshots=("at_fire", "at_period_close"),
        description="Filtered swing-pivot fields knowable after right-side confirmation bars.",
    ),
    FeatureRule(
        prefix="eql.",
        family="equal_levels_event_time",
        valid_snapshots=("at_fire", "at_period_close"),
        description="Filtered equal-level fields knowable after the confirming pivot is knowable.",
    ),
    FeatureRule(
        prefix="ft.",
        family="first_third_event_time",
        valid_snapshots=("at_fire", "at_period_close"),
        description="Filtered first-third range fields knowable after the first-third window closes.",
    ),
    FeatureRule(
        prefix="orb.",
        family="opening_range_event_time",
        valid_snapshots=("at_fire", "at_period_close"),
        description="Filtered opening-range fields knowable after the range window closes.",
    ),
    FeatureRule(
        prefix="tp.",
        family="time_profile_event_time",
        valid_snapshots=("at_fire", "at_period_close"),
        description="Filtered time-profile fields knowable after the parent period closes.",
    ),
    FeatureRule(
        prefix="vp.",
        family="volume_profile_event_time",
        valid_snapshots=("at_fire", "at_period_close"),
        description="Filtered volume-profile fields knowable after the parent period closes.",
    ),
    FeatureRule(
        prefix="fvp.",
        family="forming_volume_profile_event_time",
        valid_snapshots=("at_fire", "at_period_close"),
        description="Filtered forming volume-profile fields knowable at the as-of snapshot cutoff.",
    ),
    FeatureRule(
        prefix="ogap.",
        family="opening_gap_event_time",
        valid_snapshots=("at_fire", "at_period_close"),
        description="Filtered NDOG/NWOG level fields knowable at the new day/week open.",
    ),
    FeatureRule(
        prefix="itr.",
        family="interval_true_range_event_time",
        valid_snapshots=("at_fire", "at_period_close"),
        description="Completed daily/weekly/session interval range fields known after the interval closes.",
    ),
    FeatureRule(
        prefix="macro.",
        family="macro_event_time",
        valid_snapshots=("at_fire", "at_period_close"),
        description="Scheduled macro-event fields known before release plus pre-release market context.",
    ),
    FeatureRule(
        prefix="xd.",
        family="prior_cross_detector",
        valid_snapshots=("at_fire", "at_period_close"),
        description="Coarse Phase 1 flags for prior detector events before anchor fire.",
    ),
    FeatureRule(
        prefix="xctx.",
        family="cross_concept_context",
        valid_snapshots=("at_fire", "at_period_close"),
        description="Generated cross-concept prior-event counts, flags, and age features.",
    ),
    FeatureRule(
        prefix="fvggeom.",
        family="fvg_geometry_context",
        valid_snapshots=("at_fire", "at_period_close"),
        description="State-aware nearest FVG zone geometry known by the snapshot cutoff.",
    ),
    FeatureRule(
        prefix="obgeom.",
        family="order_block_geometry_context",
        valid_snapshots=("at_fire", "at_period_close"),
        description="State-aware nearest order-block zone geometry known by the snapshot cutoff.",
    ),
    FeatureRule(
        prefix="gapctx.",
        family="opening_gap_memory_context",
        valid_snapshots=("at_fire", "at_period_close"),
        description="State-aware nearest NDOG/NWOG memory levels known by the snapshot cutoff.",
    ),
    FeatureRule(
        prefix="liqgeom.",
        family="swing_equal_level_geometry_context",
        valid_snapshots=("at_fire", "at_period_close"),
        description="State-aware nearest swing/equal-high/equal-low liquidity levels known by the snapshot cutoff.",
    ),
    FeatureRule(
        prefix="regime.",
        family="completed_interval_regime_context",
        valid_snapshots=("at_fire", "at_period_close"),
        description="Completed session/day/week true-range regime features known before the snapshot cutoff.",
    ),
    FeatureRule(
        prefix="smtstate.",
        family="active_smt_state_context",
        valid_snapshots=("at_fire", "at_period_close"),
        description="Active forming/confirmed SMT state joined as-of the snapshot cutoff.",
    ),
    FeatureRule(
        prefix="pc.",
        family="period_close",
        valid_snapshots=("at_period_close",),
        description="Fields and aligned event flags knowable only by period N close.",
    ),
)


LABEL_RULES: tuple[LabelRule, ...] = (
    LabelRule("label.n1_", "N+1", "Next-period labels derived after period N close."),
    LabelRule("label.n2_", "N+2", "N+2 labels derived after N+1."),
    LabelRule("label.n1_or_n2_", "N+1-or-N+2", "Composite forward label."),
)


def registry_as_dict() -> dict:
    return {
        "feature_rules": [asdict(rule) for rule in FEATURE_RULES],
        "label_rules": [asdict(rule) for rule in LABEL_RULES],
        "detector_lags_min": {
            "smt": SMT_LAG_MIN,
            "smt_mtf": SMT_MTF_LAG_MIN,
            "psp": PSP_LAG_MIN,
            "fvg": FVG_LAG_MIN,
            "ob": OB_LAG_MIN,
            "sweep": SWEEP_LAG_MIN,
            "disp": DISP_LAG_MIN,
            "swing": SWING_LAG_MIN,
            "eql": EQL_LAG_MIN,
        },
    }


def allowed_snapshots_for_column(col: str) -> tuple[SnapshotName, ...] | None:
    for rule in FEATURE_RULES:
        if col.startswith(rule.prefix):
            return rule.valid_snapshots
    return None
