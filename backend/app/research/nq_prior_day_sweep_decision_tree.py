"""Prior-day high/low sweep decision-tree research study."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pandas as pd

from app.research.nq_liquidity_sweep_outcomes_types import LiquiditySweepStudyConfig
from app.research.nq_prior_day_sweep_decision_tree_context import (
    enrich_prior_day_sweeps,
    load_study_bars,
)
from app.research.nq_prior_day_sweep_decision_tree_stats import (
    CATEGORICAL_FACTORS,
    add_combination_columns,
    categorical_decision_table,
    combination_names,
    factor_rankings_from_decision_table,
    monthly_outcomes,
    numeric_factor_stats,
)
from app.research.nq_prior_day_sweep_decision_tree_types import (
    AMB,
    CONT,
    MISSING,
    REV,
    DecisionTreeStudyConfig,
)


def run_prior_day_sweep_decision_tree_study(
    *,
    input_dirs: list[Path],
    config: DecisionTreeStudyConfig | None = None,
    sweep_config: LiquiditySweepStudyConfig | None = None,
) -> dict[str, object]:
    cfg = config or DecisionTreeStudyConfig()
    sweep_cfg = sweep_config or LiquiditySweepStudyConfig(symbol=cfg.symbol)
    events = _concat(input_dirs, "liquidity_sweep_events.csv")
    features = _concat(input_dirs, "liquidity_sweep_features.csv")
    if events.empty or features.empty:
        raise ValueError("input dirs must contain liquidity_sweep_events/features CSVs")

    start = pd.to_datetime(events["session_date"]).dt.date.min()
    end = pd.to_datetime(events["session_date"]).dt.date.max()
    bars = load_study_bars(symbol=cfg.symbol, start=start, end=end)
    enriched = enrich_prior_day_sweeps(
        events,
        features,
        bars=bars,
        config=cfg,
        sweep_config=sweep_cfg,
    )
    enriched = add_combination_columns(enriched)
    labeled = _labeled(enriched)
    factor_table = categorical_decision_table(labeled, CATEGORICAL_FACTORS, cfg)
    combo_table = categorical_decision_table(labeled, combination_names(), cfg)
    factor_rankings = factor_rankings_from_decision_table(factor_table)
    combo_rankings = factor_rankings_from_decision_table(combo_table)
    result = {
        "events": enriched,
        "labeled_events": labeled,
        "factor_decision_table": factor_table,
        "factor_rankings": factor_rankings,
        "combination_decision_table": combo_table,
        "combination_rankings": combo_rankings,
        "numeric_factor_stats": numeric_factor_stats(labeled),
        "monthly_outcomes": monthly_outcomes(labeled),
        "config": asdict(cfg),
    }
    result["summary"] = study_summary(enriched, labeled, factor_rankings, combo_rankings, cfg)
    return result


def write_prior_day_sweep_decision_tree_outputs(
    result: dict[str, object],
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    mapping = {
        "events": "prior_day_sweep_decision_tree_events.csv",
        "labeled_events": "prior_day_sweep_decision_tree_labeled_events.csv",
        "factor_decision_table": "prior_day_sweep_decision_tree_factor_table.csv",
        "factor_rankings": "prior_day_sweep_decision_tree_factor_rankings.csv",
        "combination_decision_table": "prior_day_sweep_decision_tree_combinations.csv",
        "combination_rankings": "prior_day_sweep_decision_tree_combination_rankings.csv",
        "numeric_factor_stats": "prior_day_sweep_decision_tree_numeric_stats.csv",
        "monthly_outcomes": "prior_day_sweep_decision_tree_monthly_outcomes.csv",
    }
    for key, filename in mapping.items():
        value = result[key]
        assert isinstance(value, pd.DataFrame)
        value.to_csv(output_dir / filename, index=False)
    (output_dir / "prior_day_sweep_decision_tree_summary.json").write_text(
        json.dumps(_json_safe(result["summary"]), indent=2),
        encoding="utf-8",
    )
    (output_dir / "prior_day_sweep_decision_tree_config.json").write_text(
        json.dumps(_json_safe(result["config"]), indent=2),
        encoding="utf-8",
    )


def study_summary(
    enriched: pd.DataFrame,
    labeled: pd.DataFrame,
    factors: pd.DataFrame,
    combos: pd.DataFrame,
    config: DecisionTreeStudyConfig,
) -> dict[str, object]:
    cont = int((labeled["fixed_outcome_label"] == CONT).sum()) if not labeled.empty else 0
    rev = int((labeled["fixed_outcome_label"] == REV).sum()) if not labeled.empty else 0
    amb = int((enriched["fixed_outcome_label"] == AMB).sum()) if not enriched.empty else 0
    missing = int((enriched["fixed_outcome_label"] == MISSING).sum()) if not enriched.empty else 0
    total = cont + rev
    return {
        "symbol": config.symbol,
        "label_source": config.label_source,
        "fixed_continuation_target_pts": config.fixed_target_pts,
        "fixed_reversal_target_pts": config.fixed_target_pts,
        "feature_seconds": config.feature_seconds,
        "outcome_minutes": config.outcome_minutes,
        "total_prior_day_sweeps": int(len(enriched)),
        "non_ambiguous_labeled_sweeps": total,
        "continuations": cont,
        "reversals": rev,
        "ambiguous": amb,
        "missing_mbp": missing,
        "baseline_continuation_rate": cont / total if total else None,
        "baseline_failure_rate": rev / total if total else None,
        "months": int(labeled["month"].nunique()) if not labeled.empty else 0,
        "top_factor": _top_row(factors),
        "top_combination": _top_row(combos),
        "method_note": (
            "Fixed bins and fixed 8-point targets; walk-forward uses prior months "
            "to evaluate the next month without random row shuffling."
        ),
    }


def _labeled(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    out = df.loc[df["fixed_outcome_label"].isin([CONT, REV])].copy()
    out["month"] = pd.to_datetime(out["session_date"]).dt.to_period("M").astype(str)
    return out


def _concat(input_dirs: list[Path], filename: str) -> pd.DataFrame:
    frames = []
    for input_dir in input_dirs:
        path = input_dir / filename
        if path.exists():
            frames.append(pd.read_csv(path))
    return pd.concat(frames, ignore_index=True, sort=False) if frames else pd.DataFrame()


def _top_row(df: pd.DataFrame) -> dict[str, object] | None:
    if df.empty:
        return None
    return _json_safe(df.iloc[0].to_dict())


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value
