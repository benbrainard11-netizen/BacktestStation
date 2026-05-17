"""Shared vocabulary for level/zone reaction datasets.

This module defines names and small helpers for comparing different price
levels with one common schema. It is intentionally outcome-side only: these
fields describe what future bars did after a level was known.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any

LEVEL_REACTION_SCHEMA_VERSION = 1

LEVEL_HORIZONS = (
    "next_60m",
    "next_240m",
    "next_1d",
    "next_5d",
    "next_20d",
    "full_horizon",
)

STANDARD_LEVEL_COLUMNS = (
    "level.event_id",
    "level.kind",
    "level.subtype",
    "level.symbol",
    "level.side",
    "level.created_ts_utc",
    "level.price_low",
    "level.price_high",
    "level.price_mid",
    "level.size_pts",
    "level.direction",
)

STANDARD_HORIZON_FIELDS: dict[str, str] = {
    "touched": "Any wick overlap with the level/zone.",
    "meaningful_touch": "Concept-specific non-trivial touch after creation; for opening gaps this means midpoint/full-fill progress.",
    "partial_touch": "Touched the zone but did not complete the full-fill rule.",
    "midpoint_touched": "Touched the zone midpoint.",
    "full_touch": "Completed the concept-specific full touch/fill rule.",
    "closed_inside": "At least one close finished inside the zone.",
    "closed_through": "At least one close accepted through the far side.",
    "directional_rejection": "Touched and held in the level's expected support/resistance direction.",
    "directional_break_acceptance": "Accepted through against the expected support/resistance direction.",
    "continuation_acceptance": "Accepted away from the level in the continuation direction.",
    "through_acceptance": "Accepted through the far side of the level.",
    "partial_touch_rejected": "Partial touch followed by directional rejection.",
    "full_touch_rejected_inside": "Full touch/fill followed by rejection back inside instead of through.",
    "clean_fill_through": "Full touch/fill followed by through-side acceptance.",
    "unfilled_expanded_away": "Stayed unfilled and expanded away by at least one level size.",
    "unfilled_clean_continuation": "Stayed unfilled and accepted away from the level.",
    "time_to_touch_minutes": "Minutes from level creation to first touch.",
    "time_to_meaningful_touch_minutes": "Minutes from level creation to the first non-trivial touch.",
    "time_to_full_touch_minutes": "Minutes from level creation to full touch/fill.",
    "reaction_away_pts": "Maximum favorable excursion away from the level's expected side.",
    "reaction_through_pts": "Maximum excursion through the opposite/far side.",
    "reaction_away_x_size": "reaction_away_pts divided by level size.",
    "reaction_through_x_size": "reaction_through_pts divided by level size.",
}


@dataclass(frozen=True)
class AgeBucket:
    label: str
    min_minutes: float
    max_minutes: float


AGE_BUCKETS: tuple[AgeBucket, ...] = (
    AgeBucket("0-1h", 0, 60),
    AgeBucket("1-4h", 60, 240),
    AgeBucket("4h-1d", 240, 24 * 60),
    AgeBucket("1-3d", 24 * 60, 3 * 24 * 60),
    AgeBucket("3-7d", 3 * 24 * 60, 7 * 24 * 60),
    AgeBucket("7-20d", 7 * 24 * 60, 20 * 24 * 60 + 1),
)
UNREACHED_BUCKET = "unreached_20d"


def level_reaction_column(horizon: str, field: str) -> str:
    """Return the standard flat column name for a horizon-specific reaction."""
    if horizon not in LEVEL_HORIZONS:
        raise ValueError(f"unknown level-reaction horizon: {horizon}")
    if field not in STANDARD_HORIZON_FIELDS:
        raise ValueError(f"unknown level-reaction field: {field}")
    return f"lr.{horizon}.{field}"


def age_bucket_minutes(minutes: Any) -> str:
    """Bucket a time-to-touch/fill value for age-decay analysis."""
    try:
        value = float(minutes)
    except (TypeError, ValueError):
        return UNREACHED_BUCKET
    if not isfinite(value) or value < 0:
        return UNREACHED_BUCKET
    for bucket in AGE_BUCKETS:
        if bucket.min_minutes <= value < bucket.max_minutes:
            return bucket.label
    return "20d+"


def schema_payload() -> dict[str, Any]:
    """Machine-readable definition for generated level-reaction artifacts."""
    return {
        "schema_version": LEVEL_REACTION_SCHEMA_VERSION,
        "level_columns": list(STANDARD_LEVEL_COLUMNS),
        "horizons": list(LEVEL_HORIZONS),
        "horizon_fields": STANDARD_HORIZON_FIELDS,
        "age_buckets": [
            {
                "label": bucket.label,
                "min_minutes": bucket.min_minutes,
                "max_minutes": bucket.max_minutes,
            }
            for bucket in AGE_BUCKETS
        ],
        "unreached_bucket": UNREACHED_BUCKET,
        "safety": (
            "lr.* columns are outcome/label columns computed from future bars. "
            "They must not be used as model inputs unless intentionally training "
            "a target label."
        ),
    }
