"""Low-side refinement diagnostics for prior-day sweep strategy validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from app.research.nq_prior_day_sweep_failure_modes import (
    prepare_prior_day_sweep_attempts,
)
from app.research.nq_prior_day_sweep_low_refinement_stats import (
    categorical_summary,
    context_validation,
    event_continuation,
    monthly_summary,
    numeric_summary,
    numeric_validation,
    strategy_summary,
    variant_summary,
)

LOW = "prior_day_low"


def run_prior_day_sweep_low_refinement_study(
    *,
    attempts_path: Path,
    events_path: Path,
    holdout_start: str = "2026-02-01",
    holdout_end: str = "2026-05-24",
) -> dict[str, object]:
    events = _prepare_events(pd.read_csv(events_path), holdout_start, holdout_end)
    attempts = pd.read_csv(attempts_path)
    joined = prepare_prior_day_sweep_attempts(
        attempts,
        events,
        holdout_start,
        holdout_end,
    )
    low_attempts = joined.loc[joined["level_type"] == LOW].copy()
    low_events = events.loc[events["level_type"] == LOW].copy()
    trades = low_attempts.loc[low_attempts["trade_result"].isin(["win", "loss"])].copy()

    categorical = categorical_summary(trades)
    numeric = numeric_summary(trades)
    result = {
        "low_attempts": low_attempts,
        "event_continuation": event_continuation(low_events),
        "strategy_summary": strategy_summary(low_attempts),
        "variant_summary": variant_summary(low_attempts),
        "categorical_summary": categorical,
        "numeric_summary": numeric,
        "context_validation": context_validation(categorical),
        "numeric_validation": numeric_validation(numeric),
        "monthly_summary": monthly_summary(low_attempts, low_events),
    }
    result["summary"] = _json_safe(summary_rows(result))
    return result


def write_prior_day_sweep_low_refinement_outputs(
    result: dict[str, object],
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    mapping = {
        "low_attempts": "prior_day_low_refinement_attempts.csv",
        "event_continuation": "prior_day_low_refinement_event_continuation.csv",
        "strategy_summary": "prior_day_low_refinement_strategy.csv",
        "variant_summary": "prior_day_low_refinement_variants.csv",
        "categorical_summary": "prior_day_low_refinement_categorical.csv",
        "numeric_summary": "prior_day_low_refinement_numeric.csv",
        "context_validation": "prior_day_low_refinement_context_validation.csv",
        "numeric_validation": "prior_day_low_refinement_numeric_validation.csv",
        "monthly_summary": "prior_day_low_refinement_monthly.csv",
    }
    for key, filename in mapping.items():
        value = result[key]
        assert isinstance(value, pd.DataFrame)
        value.to_csv(output_dir / filename, index=False)
    (output_dir / "prior_day_low_refinement_summary.json").write_text(
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
    out["month"] = out["session_date"].dt.to_period("M").astype(str)
    return out


def summary_rows(result: dict[str, Any]) -> dict[str, object]:
    return {
        "strategy_summary": result["strategy_summary"].to_dict("records"),
        "event_continuation": result["event_continuation"].to_dict("records"),
        "top_contexts": result["context_validation"].head(8).to_dict("records"),
        "top_numeric": result["numeric_validation"].head(8).to_dict("records"),
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
