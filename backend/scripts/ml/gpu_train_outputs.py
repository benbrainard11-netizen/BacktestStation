"""Output writers for the GPU runner.

Splits artifact writing out of the orchestration script so the runner
stays small. Files written per Prompt B:

- config.json
- metrics_summary.csv
- folds.parquet
- predictions.parquet
- feature_importance.csv
- README.md
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from .gpu_train_metrics import FoldMetrics


def ensure_output_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_config(output_dir: Path, config: dict[str, Any]) -> Path:
    """Write `config.json` with every reproducibility-relevant input."""
    path = output_dir / "config.json"
    payload = dict(config)
    payload["written_at"] = datetime.now(UTC).isoformat()
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def write_metrics_summary(output_dir: Path, fold_records: list[dict[str, Any]]) -> Path:
    """One row per fold with the FoldMetrics fields + identifying keys."""
    path = output_dir / "metrics_summary.csv"
    df = pd.DataFrame(fold_records)
    df.to_csv(path, index=False)
    return path


def write_folds_parquet(output_dir: Path, fold_records: list[dict[str, Any]]) -> Path:
    """Same content as the CSV but parquet, for downstream joins."""
    path = output_dir / "folds.parquet"
    df = pd.DataFrame(fold_records)
    df.to_parquet(path, index=False)
    return path


def write_predictions(output_dir: Path, prediction_records: list[pd.DataFrame]) -> Path:
    """All per-row test predictions stacked across folds."""
    path = output_dir / "predictions.parquet"
    if prediction_records:
        df = pd.concat(prediction_records, ignore_index=True)
    else:
        df = pd.DataFrame(columns=["fold_test_year", "row_index", "y_true", "p_test"])
    df.to_parquet(path, index=False)
    return path


def write_feature_importance(output_dir: Path, importance_records: list[dict[str, Any]]) -> Path:
    """One row per (fold, feature) with gain. Aggregated mean appended."""
    path = output_dir / "feature_importance.csv"
    if not importance_records:
        pd.DataFrame(columns=["fold_test_year", "feature", "gain"]).to_csv(path, index=False)
        return path
    df = pd.DataFrame(importance_records)
    df = df.sort_values(["fold_test_year", "gain"], ascending=[True, False])
    df.to_csv(path, index=False)
    return path


def aggregate_top_features(
    importance_records: list[dict[str, Any]], top_n: int = 25
) -> list[tuple[str, float]]:
    """Mean gain per feature across all folds it appeared in."""
    sums: dict[str, float] = defaultdict(float)
    counts: dict[str, int] = defaultdict(int)
    for rec in importance_records:
        sums[rec["feature"]] += float(rec["gain"])
        counts[rec["feature"]] += 1
    means = sorted(
        ((feat, sums[feat] / counts[feat]) for feat in sums),
        key=lambda kv: -kv[1],
    )
    return means[:top_n]


def write_readme(
    output_dir: Path,
    *,
    config: dict[str, Any],
    fold_metrics: list[tuple[int, FoldMetrics]],
    top_features: list[tuple[str, float]],
) -> Path:
    """Human-readable summary that compares against the CPU baseline.

    `fold_metrics` is a list of `(test_year, FoldMetrics)` pairs so the
    table header column can be filled without mutating the dataclass.
    """
    path = output_dir / "README.md"
    lines: list[str] = []
    lines.append("# GPU XGBoost run — sweep context-layers")
    lines.append("")
    lines.append(f"_Generated `{datetime.now(UTC).isoformat()}`._")
    lines.append("")
    lines.append("## Setup")
    lines.append("")
    for key in [
        "matrix",
        "schema",
        "label",
        "side",
        "snapshot",
        "event_type",
        "device_resolved",
        "xgboost_version",
        "cuda_available",
        "seed",
        "git_sha",
    ]:
        if key in config:
            lines.append(f"- {key}: `{config[key]}`")
    lines.append("")
    lines.append("## Per-fold metrics")
    lines.append("")
    lines.append(
        "| test_year | n_train | n_test | base_rate | auc_train | auc_val | "
        "auc_test | top_n | top_rate | top_lift | best_iter |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for test_year, m in fold_metrics:
        lines.append(_fold_row(test_year, m))
    lines.append("")
    if fold_metrics:
        auc_values = [m.auc_test for _, m in fold_metrics if m.auc_test is not None]
        if auc_values:
            mean = sum(auc_values) / len(auc_values)
            mn = min(auc_values)
            lines.append(f"**Mean test AUC across folds:** `{mean:.3f}`  ")
            lines.append(f"**Min-fold test AUC:** `{mn:.3f}`")
            lines.append("")
    lines.append("## Top mean-gain features (across folds)")
    lines.append("")
    lines.append("| rank | feature | mean_gain |")
    lines.append("|---|---|---|")
    for rank, (feat, gain) in enumerate(top_features, start=1):
        lines.append(f"| {rank} | `{feat}` | {gain:.1f} |")
    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append(
        "Compare the mean test AUC to the CPU LightGBM baseline reported "
        "in `docs/ML_CONTEXT_LAYER_RESULTS.md` for the same matrix/label/"
        "side/snapshot. The two runners share encoding (`pd.get_dummies("
        "dummy_na=True)`), split rules (`train ≤ test_year-2 / val = "
        "test_year-1 / test = test_year`), and hyperparameter shape, so "
        "the delta isolates device + library."
    )
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _fold_row(test_year: int, m: FoldMetrics) -> str:
    return (
        f"| {test_year} | "
        f"{m.n_train} | {m.n_test} | "
        f"{m.base_rate_test:.3f} | "
        f"{_fmt(m.auc_train)} | {_fmt(m.auc_val)} | {_fmt(m.auc_test)} | "
        f"{m.top_bucket_n} | {m.top_bucket_rate:.3f} | "
        f"{m.top_bucket_lift_vs_base:+.3f} | {m.best_iteration} |"
    )


def _fmt(value: float | None) -> str:
    return "-" if value is None else f"{value:.3f}"


def fold_records_to_dict(
    test_year: int,
    fold_metrics: FoldMetrics,
    extras: dict[str, Any],
) -> dict[str, Any]:
    """Flatten FoldMetrics + identifying keys for tabular output."""
    record = dict(extras)
    record["test_year"] = test_year
    record.update(asdict(fold_metrics))
    return record
