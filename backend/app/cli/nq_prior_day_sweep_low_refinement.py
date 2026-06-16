"""Run low-side refinement diagnostics for prior-day sweep validation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from app.research.nq_prior_day_sweep_low_refinement import (
    run_prior_day_sweep_low_refinement_study,
    write_prior_day_sweep_low_refinement_outputs,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempts-path", type=Path, required=True)
    parser.add_argument("--events-path", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--holdout-start", default="2026-02-01")
    parser.add_argument("--holdout-end", default="2026-05-24")
    args = parser.parse_args(argv)

    result = run_prior_day_sweep_low_refinement_study(
        attempts_path=args.attempts_path,
        events_path=args.events_path,
        holdout_start=args.holdout_start,
        holdout_end=args.holdout_end,
    )
    write_prior_day_sweep_low_refinement_outputs(result, args.output_dir)
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
