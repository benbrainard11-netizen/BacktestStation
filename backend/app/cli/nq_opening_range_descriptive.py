"""Run the NQ opening-range descriptive study."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from app.research.nq_opening_range_descriptive import (
    run_opening_range_descriptive_study,
    write_opening_range_descriptive_outputs,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--symbol", default="NQ.c.0")
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--holdout-start", default="2026-02-01")
    parser.add_argument("--context-deadzone-pts", type=float, default=8.0)
    args = parser.parse_args(argv)

    result = run_opening_range_descriptive_study(
        symbol=args.symbol,
        start=args.start,
        end=args.end,
        holdout_start=args.holdout_start,
        context_deadzone_pts=args.context_deadzone_pts,
    )
    write_opening_range_descriptive_outputs(result, args.output_dir)
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
