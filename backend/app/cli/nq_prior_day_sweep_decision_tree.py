"""Run the NQ prior-day sweep decision-tree study."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from app.research.nq_liquidity_sweep_outcomes_types import LiquiditySweepStudyConfig
from app.research.nq_prior_day_sweep_decision_tree import (
    run_prior_day_sweep_decision_tree_study,
    write_prior_day_sweep_decision_tree_outputs,
)
from app.research.nq_prior_day_sweep_decision_tree_types import (
    DecisionTreeStudyConfig,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", action="append", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--symbol", default="NQ.c.0")
    parser.add_argument("--label-source", choices=["bars", "mbp1"], default="bars")
    parser.add_argument("--fixed-target-pts", type=float, default=8.0)
    parser.add_argument("--feature-seconds", type=int, default=30)
    parser.add_argument("--outcome-minutes", type=int, default=60)
    parser.add_argument("--min-train-months", type=int, default=3)
    parser.add_argument("--min-category-train-sample", type=int, default=10)
    args = parser.parse_args(argv)

    config = DecisionTreeStudyConfig(
        symbol=args.symbol,
        label_source=args.label_source,
        fixed_target_pts=args.fixed_target_pts,
        feature_seconds=args.feature_seconds,
        outcome_minutes=args.outcome_minutes,
        min_train_months=args.min_train_months,
        min_category_train_sample=args.min_category_train_sample,
    )
    sweep_config = LiquiditySweepStudyConfig(
        symbol=args.symbol,
        feature_seconds=args.feature_seconds,
        outcome_minutes=args.outcome_minutes,
        min_outcome_pts=args.fixed_target_pts,
    )
    result = run_prior_day_sweep_decision_tree_study(
        input_dirs=args.input_dir,
        config=config,
        sweep_config=sweep_config,
    )
    write_prior_day_sweep_decision_tree_outputs(result, args.output_dir)
    print(json.dumps(_json_safe(result["summary"]), indent=2))
    return 0


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


if __name__ == "__main__":
    raise SystemExit(main())
