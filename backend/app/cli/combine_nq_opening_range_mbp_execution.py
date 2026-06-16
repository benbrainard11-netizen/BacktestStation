"""Combine chunked NQ OR middle-third MBP execution study outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from app.research.nq_opening_range_mbp_execution import (
    write_opening_range_mbp_execution_outputs,
)
from app.research.nq_opening_range_mbp_execution_stats import (
    json_safe,
    monthly_summary,
    outcome_summary,
    stability_summary,
    study_summary,
    variant_summary,
    walk_forward_summary,
)
from app.research.nq_opening_range_mbp_execution_types import (
    OpeningRangeMbpExecutionConfig,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--chunk-dir", type=Path, action="append", required=True)
    parser.add_argument("--symbol", default="NQ.c.0")
    parser.add_argument("--holdout-start", default="2026-02-01")
    args = parser.parse_args(argv)

    config = OpeningRangeMbpExecutionConfig(
        symbol=args.symbol,
        holdout_start=args.holdout_start,
    )
    result = combine_chunks(args.chunk_dir, config)
    write_opening_range_mbp_execution_outputs(result, args.output_dir)
    print(json.dumps(json_safe(result["summary"]), indent=2))
    return 0


def combine_chunks(
    chunk_dirs: list[Path],
    config: OpeningRangeMbpExecutionConfig,
) -> dict[str, object]:
    source_events = concat_csv(chunk_dirs, "or_middle_third_source_events.csv")
    mbp_events = concat_csv(chunk_dirs, "or_middle_third_mbp_events.csv")
    attempts = concat_csv(chunk_dirs, "or_middle_third_mbp_attempts.csv")
    trades = attempts.loc[attempts["status"] == "filled"].copy()
    for frame in (source_events, mbp_events, attempts, trades):
        if "is_holdout" in frame.columns:
            frame["is_holdout"] = frame["is_holdout"].astype(str).str.lower().eq("true")
    outcomes = outcome_summary(mbp_events)
    variants = variant_summary(attempts)
    monthly = monthly_summary(attempts)
    walk = walk_forward_summary(attempts, config)
    stability = stability_summary(variants, walk)
    return {
        "source_events": source_events,
        "mbp_events": mbp_events,
        "attempts": attempts,
        "trades": trades,
        "outcome_summary": outcomes,
        "variant_summary": variants,
        "monthly_summary": monthly,
        "walk_forward": walk,
        "stability_summary": stability,
        "summary": study_summary(mbp_events, attempts, outcomes, stability, config),
        "config": config.__dict__,
    }


def concat_csv(chunk_dirs: list[Path], filename: str) -> pd.DataFrame:
    frames = []
    for chunk_dir in chunk_dirs:
        path = chunk_dir / filename
        if path.exists():
            frames.append(pd.read_csv(path))
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True).drop_duplicates().reset_index(drop=True)


if __name__ == "__main__":
    raise SystemExit(main())
