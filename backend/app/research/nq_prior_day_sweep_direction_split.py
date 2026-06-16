"""Direction-split diagnostics for prior-day sweep strategy validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from app.research.nq_prior_day_sweep_direction_split_stats import (
    POST_SWEEP_FEATURES,
    categorical_effect_summary,
    direction_comparison,
    event_continuation_summary,
    numeric_direction_summary,
    strategy_direction_summary,
    strategy_variant_direction_summary,
)
from app.research.nq_prior_day_sweep_failure_modes import (
    prepare_prior_day_sweep_attempts,
)


def run_prior_day_sweep_direction_split_analysis(
    *,
    attempts_path: Path,
    events_path: Path,
    holdout_start: str = "2026-02-01",
    holdout_end: str = "2026-05-24",
) -> dict[str, object]:
    attempts = pd.read_csv(attempts_path)
    events = _prepare_events(pd.read_csv(events_path), holdout_start, holdout_end)
    joined = prepare_prior_day_sweep_attempts(
        attempts,
        events,
        holdout_start,
        holdout_end,
    )
    trades = joined.loc[joined["trade_result"].isin(["win", "loss"])].copy()

    event_summary = event_continuation_summary(events)
    strategy_summary = strategy_direction_summary(joined)
    variant_summary = strategy_variant_direction_summary(joined)
    overnight = categorical_effect_summary(trades, "overnight_range_location_vs_sweep")
    time_of_day = categorical_effect_summary(trades, "time_of_day_bucket")
    post_sweep = numeric_direction_summary(trades, POST_SWEEP_FEATURES)
    comparison = direction_comparison(event_summary, strategy_summary)

    return {
        "joined_attempts": joined,
        "event_continuation": event_summary,
        "strategy_direction": strategy_summary,
        "strategy_variant_direction": variant_summary,
        "overnight_location": overnight,
        "time_of_day": time_of_day,
        "post_sweep_activity": post_sweep,
        "direction_comparison": comparison,
        "summary": _summary(event_summary, strategy_summary, comparison),
    }


def write_prior_day_sweep_direction_split_outputs(
    result: dict[str, object],
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    mapping = {
        "event_continuation": "prior_day_sweep_direction_event_continuation.csv",
        "strategy_direction": "prior_day_sweep_direction_strategy.csv",
        "strategy_variant_direction": "prior_day_sweep_direction_variants.csv",
        "overnight_location": "prior_day_sweep_direction_overnight_location.csv",
        "time_of_day": "prior_day_sweep_direction_time_of_day.csv",
        "post_sweep_activity": "prior_day_sweep_direction_post_sweep_activity.csv",
        "direction_comparison": "prior_day_sweep_direction_comparison.csv",
    }
    for key, filename in mapping.items():
        value = result[key]
        assert isinstance(value, pd.DataFrame)
        value.to_csv(output_dir / filename, index=False)
    (output_dir / "prior_day_sweep_direction_summary.json").write_text(
        json.dumps(_json_safe(result["summary"]), indent=2),
        encoding="utf-8",
    )


def _prepare_events(
    events: pd.DataFrame,
    holdout_start: str,
    holdout_end: str,
) -> pd.DataFrame:
    out = events.copy()
    out["session_date"] = pd.to_datetime(out["session_date"], errors="coerce")
    out["is_holdout"] = (
        (out["session_date"] >= pd.Timestamp(holdout_start))
        & (out["session_date"] < pd.Timestamp(holdout_end))
    )
    return out


def _summary(
    event_summary: pd.DataFrame,
    strategy_summary: pd.DataFrame,
    comparison: pd.DataFrame,
) -> dict[str, object]:
    return {
        "event_continuation": _json_safe(event_summary.to_dict("records")),
        "strategy_direction": _json_safe(strategy_summary.to_dict("records")),
        "direction_comparison": _json_safe(comparison.to_dict("records")),
    }


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value
