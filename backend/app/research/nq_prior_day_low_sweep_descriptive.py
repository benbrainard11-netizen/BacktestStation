"""Descriptive study for prior-day low sweep winner/loss differences."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from app.research.nq_prior_day_low_sweep_descriptive_stats import (
    categorical_distributions,
    effect_consistency,
    numeric_distributions,
    numeric_effects,
)
from app.research.nq_prior_day_sweep_failure_modes import (
    prepare_prior_day_sweep_attempts,
)

LOW = "prior_day_low"


def run_prior_day_low_sweep_descriptive_study(
    *,
    attempts_path: Path,
    events_path: Path,
    holdout_start: str = "2026-02-01",
    holdout_end: str = "2026-05-24",
) -> dict[str, object]:
    attempts = pd.read_csv(attempts_path)
    events = pd.read_csv(events_path)
    joined = prepare_prior_day_sweep_attempts(
        attempts,
        events,
        holdout_start,
        holdout_end,
    )
    trades = joined.loc[
        (joined["level_type"] == LOW) & (joined["trade_result"].isin(["win", "loss"]))
    ].copy()
    trades = trades.sort_values(["session_date", "event_id", "variant_id"]).reset_index(
        drop=True
    )

    categorical = categorical_distributions(trades)
    numeric_dist = numeric_distributions(trades)
    numeric_eff = numeric_effects(trades)
    consistency = effect_consistency(categorical, numeric_eff)

    result = {
        "trade_rows": trades,
        "categorical_distributions": categorical,
        "numeric_distributions": numeric_dist,
        "numeric_effects": numeric_eff,
        "effect_consistency": consistency,
    }
    result["summary"] = _json_safe(summary_rows(result))
    return result


def write_prior_day_low_sweep_descriptive_outputs(
    result: dict[str, object],
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    mapping = {
        "trade_rows": "prior_day_low_descriptive_trades.csv",
        "categorical_distributions": "prior_day_low_descriptive_categorical.csv",
        "numeric_distributions": "prior_day_low_descriptive_numeric_distributions.csv",
        "numeric_effects": "prior_day_low_descriptive_numeric_effects.csv",
        "effect_consistency": "prior_day_low_descriptive_consistency.csv",
    }
    for key, filename in mapping.items():
        value = result[key]
        assert isinstance(value, pd.DataFrame)
        value.to_csv(output_dir / filename, index=False)
    (output_dir / "prior_day_low_descriptive_summary.json").write_text(
        json.dumps(_json_safe(result["summary"]), indent=2),
        encoding="utf-8",
    )


def summary_rows(result: dict[str, object]) -> dict[str, object]:
    trades = result["trade_rows"]
    consistency = result["effect_consistency"]
    assert isinstance(trades, pd.DataFrame)
    assert isinstance(consistency, pd.DataFrame)
    consistent = consistency.loc[consistency["read"] == "directionally_consistent"]
    return {
        "trade_counts": [_scope_counts(scope, frame) for scope, frame in _scopes(trades)],
        "directionally_consistent_effects": consistent.to_dict("records"),
        "all_effect_consistency": consistency.to_dict("records"),
    }


def _scope_counts(scope: str, frame: pd.DataFrame) -> dict[str, object]:
    wins = int((frame["trade_result"] == "win").sum())
    losses = int((frame["trade_result"] == "loss").sum())
    total = wins + losses
    return {
        "scope": scope,
        "trades": total,
        "wins": wins,
        "losses": losses,
        "win_rate": wins / total if total else None,
    }


def _scopes(df: pd.DataFrame) -> list[tuple[str, pd.DataFrame]]:
    return [
        ("full", df),
        ("in_sample", df.loc[~df["is_holdout"]].copy()),
        ("holdout", df.loc[df["is_holdout"]].copy()),
    ]


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
