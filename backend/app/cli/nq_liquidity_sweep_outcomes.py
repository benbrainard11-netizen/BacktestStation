"""Run the NQ liquidity sweep outcome study."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from app.research.nq_liquidity_sweep_outcomes_chunked import run_chunked_study
from app.research.nq_liquidity_sweep_outcomes_types import LiquiditySweepStudyConfig


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", default="NQ.c.0")
    parser.add_argument("--start", type=_parse_date, required=True)
    parser.add_argument("--end", type=_parse_date, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--bootstrap-iterations", type=int, default=300)
    parser.add_argument("--permutation-iterations", type=int, default=300)
    args = parser.parse_args(argv)
    if args.start >= args.end:
        parser.error("--start must be before --end")
    _setup_logging()

    config = LiquiditySweepStudyConfig(
        symbol=args.symbol,
        bootstrap_iterations=args.bootstrap_iterations,
        permutation_iterations=args.permutation_iterations,
    )
    result = run_chunked_study(
        symbol=args.symbol,
        start=args.start,
        end=args.end,
        config=config,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    _write_outputs(result, args.output_dir, config)
    payload = {
        "output_dir": str(args.output_dir),
        "summary": result["summary"],
        "top5_features": _df_preview(result["top5_features"]),
    }
    print(json.dumps(_json_safe(payload), indent=2))
    return 0


def _write_outputs(
    result: dict[str, object],
    output_dir: Path,
    config: LiquiditySweepStudyConfig,
) -> None:
    mapping = {
        "events": "liquidity_sweep_events.csv",
        "features": "liquidity_sweep_features.csv",
        "feature_rankings": "liquidity_sweep_feature_rankings.csv",
        "top5_features": "liquidity_sweep_top5_features.csv",
        "feature_distributions": "liquidity_sweep_feature_distributions.csv",
        "monthly_stability": "liquidity_sweep_monthly_stability.csv",
        "examples": "liquidity_sweep_examples.csv",
        "feature_metadata": "liquidity_sweep_feature_metadata.csv",
        "sessions": "liquidity_sweep_sessions.csv",
        "daily_loads": "liquidity_sweep_daily_loads.csv",
    }
    for key, filename in mapping.items():
        value = result[key]
        assert isinstance(value, pd.DataFrame)
        value.to_csv(output_dir / filename, index=False)
    (output_dir / "liquidity_sweep_summary.json").write_text(
        json.dumps(_json_safe(result["summary"]), indent=2),
        encoding="utf-8",
    )
    (output_dir / "liquidity_sweep_config.json").write_text(
        json.dumps(_json_safe(asdict(config)), indent=2),
        encoding="utf-8",
    )


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        stream=sys.stderr,
    )


def _df_preview(value: object, *, limit: int = 5) -> list[dict[str, object]]:
    if isinstance(value, pd.DataFrame):
        return value.head(limit).to_dict(orient="records")
    return []


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, (date, pd.Timestamp)):
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
