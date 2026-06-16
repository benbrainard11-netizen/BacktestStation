"""Combine sharded NQ prior-day sweep strategy prototype outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from app.research.nq_prior_day_sweep_strategy_prototype import (
    write_prior_day_sweep_strategy_outputs,
)
from app.research.nq_prior_day_sweep_strategy_prototype_combine import (
    combine_prior_day_sweep_strategy_outputs,
)
from app.research.nq_prior_day_sweep_strategy_prototype_types import (
    PriorDaySweepPrototypeConfig,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, action="append", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--symbol", default="NQ.c.0")
    parser.add_argument("--sequencing-source", choices=["bars", "mbp1"], default="mbp1")
    parser.add_argument("--commission-per-contract", type=float, default=2.0)
    parser.add_argument("--slippage-ticks", type=int, default=1)
    parser.add_argument("--variant-id", action="append", default=[])
    args = parser.parse_args(argv)

    config = PriorDaySweepPrototypeConfig(
        symbol=args.symbol,
        sequencing_source=args.sequencing_source,
        commission_per_contract=args.commission_per_contract,
        slippage_ticks=args.slippage_ticks,
        variant_ids=tuple(args.variant_id),
    )
    result = combine_prior_day_sweep_strategy_outputs(args.input_dir, config)
    write_prior_day_sweep_strategy_outputs(result, args.output_dir)
    print(json.dumps(_json_safe(result["study_summary"]), indent=2))
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
