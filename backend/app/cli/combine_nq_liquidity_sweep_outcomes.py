"""Combine NQ liquidity sweep outcome study shard outputs."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from app.research.nq_liquidity_sweep_outcomes_stats import analyze_sweep_features
from app.research.nq_liquidity_sweep_outcomes_types import LiquiditySweepStudyConfig


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", action="append", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--symbol", default="NQ.c.0")
    parser.add_argument("--bootstrap-iterations", type=int, default=300)
    parser.add_argument("--permutation-iterations", type=int, default=300)
    args = parser.parse_args(argv)

    config = LiquiditySweepStudyConfig(
        symbol=args.symbol,
        bootstrap_iterations=args.bootstrap_iterations,
        permutation_iterations=args.permutation_iterations,
    )
    result = combine_outputs(args.input_dir, config)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    _write_outputs(result, args.output_dir, config)
    print(json.dumps(_json_safe(result["summary"]), indent=2))
    return 0


def combine_outputs(
    input_dirs: list[Path],
    config: LiquiditySweepStudyConfig,
) -> dict[str, object]:
    events = _concat(input_dirs, "liquidity_sweep_events.csv")
    features = _concat(input_dirs, "liquidity_sweep_features.csv")
    sessions = _concat(input_dirs, "liquidity_sweep_sessions.csv")
    daily_loads = _concat(input_dirs, "liquidity_sweep_daily_loads.csv")
    analysis = analyze_sweep_features(events=events, features=features, config=config)
    return {
        "events": events,
        "features": features,
        "sessions": sessions,
        "daily_loads": daily_loads,
        **analysis,
    }


def _concat(input_dirs: list[Path], filename: str) -> pd.DataFrame:
    frames = []
    for input_dir in input_dirs:
        path = input_dir / filename
        if path.exists():
            frames.append(pd.read_csv(path))
    return pd.concat(frames, ignore_index=True, sort=False) if frames else pd.DataFrame()


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


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
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
