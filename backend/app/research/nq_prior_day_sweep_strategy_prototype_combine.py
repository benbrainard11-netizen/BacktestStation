"""Combine sharded prior-day sweep prototype outputs."""

from __future__ import annotations

from dataclasses import asdict, replace
from pathlib import Path

import pandas as pd

from app.research.nq_prior_day_sweep_strategy_prototype_setup import variant_rows
from app.research.nq_prior_day_sweep_strategy_prototype_stats import (
    monthly_summary,
    study_summary,
    variant_summary,
    walk_forward_summary,
)
from app.research.nq_prior_day_sweep_strategy_prototype_types import (
    PriorDaySweepPrototypeConfig,
)

QUALIFIED_FILENAME = "prior_day_sweep_strategy_qualified_events.csv"
ATTEMPTS_FILENAME = "prior_day_sweep_strategy_attempts.csv"


def combine_prior_day_sweep_strategy_outputs(
    input_dirs: list[Path],
    config: PriorDaySweepPrototypeConfig | None = None,
) -> dict[str, object]:
    """Combine non-overlapping shard output folders and recompute summaries."""

    if not input_dirs:
        raise ValueError("at least one input directory is required")

    cfg = config or PriorDaySweepPrototypeConfig()
    qualified = _concat_csvs(input_dirs, QUALIFIED_FILENAME)
    attempts = _concat_csvs(input_dirs, ATTEMPTS_FILENAME)
    _reject_overlapping_shards(qualified, attempts)

    attempts = _normalize_attempts(attempts)
    qualified = _normalize_qualified(qualified)
    if not cfg.variant_ids:
        cfg = replace(cfg, variant_ids=tuple(sorted(attempts["variant_id"].unique())))

    trades = attempts.loc[attempts["status"] == "filled"].copy()
    variants = pd.DataFrame(variant_rows(cfg.variant_ids))
    summary = variant_summary(attempts, cfg)
    monthly = monthly_summary(attempts)
    walk = walk_forward_summary(attempts, cfg)

    return {
        "qualified_events": qualified,
        "attempts": attempts,
        "trades": trades,
        "variants": variants,
        "variant_summary": summary,
        "monthly_summary": monthly,
        "walk_forward": walk,
        "study_summary": study_summary(qualified, attempts, summary, walk, cfg),
        "config": asdict(cfg),
    }


def _concat_csvs(input_dirs: list[Path], filename: str) -> pd.DataFrame:
    frames = []
    missing = []
    for input_dir in input_dirs:
        path = input_dir / filename
        if not path.exists():
            missing.append(str(path))
            continue
        frames.append(pd.read_csv(path))
    if missing:
        raise FileNotFoundError(f"missing shard files: {', '.join(missing)}")
    if not frames:
        raise ValueError(f"no {filename} files found")
    return pd.concat(frames, ignore_index=True)


def _reject_overlapping_shards(qualified: pd.DataFrame, attempts: pd.DataFrame) -> None:
    event_dupes = int(qualified.duplicated(["event_id"]).sum())
    attempt_dupes = int(attempts.duplicated(["event_id", "variant_id"]).sum())
    if event_dupes or attempt_dupes:
        raise ValueError(
            "input shards appear to overlap: "
            f"{event_dupes} duplicate events, {attempt_dupes} duplicate attempts"
        )


def _normalize_qualified(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "sweep_ts" in out.columns:
        out["sweep_ts"] = pd.to_datetime(out["sweep_ts"], utc=True, errors="coerce")
    return _sort_frame(out, ["sweep_ts", "event_id"])


def _normalize_attempts(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for column in ("sweep_ts", "entry_ts", "exit_ts"):
        if column in out.columns:
            out[column] = pd.to_datetime(out[column], utc=True, errors="coerce")
    return _sort_frame(out, ["sweep_ts", "event_id", "variant_id"])


def _sort_frame(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    existing = [column for column in columns if column in df.columns]
    if not existing:
        return df.reset_index(drop=True)
    return df.sort_values(existing).reset_index(drop=True)
