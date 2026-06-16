"""Run frozen prior-day-low forward validation after the 2026-05-23 cutoff."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from app.research.nq_prior_day_low_forward_validation import (
    run_prior_day_low_forward_validation,
    write_prior_day_low_forward_validation_outputs,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events-path", type=Path, required=True)
    parser.add_argument("--attempts-path", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--cutoff", default="2026-05-23")
    parser.add_argument("--max-events", type=int, default=100)
    parser.add_argument("--strategy-config-path", type=Path)
    parser.add_argument("--decision-tree-config-path", type=Path)
    args = parser.parse_args(argv)

    result = run_prior_day_low_forward_validation(
        events_path=args.events_path,
        attempts_path=args.attempts_path,
        cutoff=args.cutoff,
        max_events=args.max_events,
        strategy_config_path=args.strategy_config_path,
        decision_tree_config_path=args.decision_tree_config_path,
    )
    write_prior_day_low_forward_validation_outputs(result, args.output_dir)
    print(json.dumps(_json_safe(result["summary"]), indent=2))
    return 0


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


if __name__ == "__main__":
    raise SystemExit(main())
