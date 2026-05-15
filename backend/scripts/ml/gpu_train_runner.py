"""GPU XGBoost training runner for exported anchor matrices.

CLI orchestrator. Each invocation trains one (matrix, label, side,
snapshot) combination across all eligible walk-forward folds and writes
the artifact set described in Prompt B.

Reads matrix + schema once, filters once, then iterates folds in-memory
— no re-reads per fold. Heavy lifting lives in `gpu_train_pipeline.py`;
this module is the CLI + I/O entry point only.

Run from the GPU host (RTX 5080) with xgboost>=2.1 (CUDA build) and
the unzipped strategy-lab export available on disk.

Example:
    python -m scripts.ml.gpu_train_runner \\
        --matrix path/to/sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime.parquet \\
        --schema path/to/sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime.schema.json \\
        --label  label.manipulation_range_reaction.range_expanded_2x_manipulation \\
        --side   low --snapshot at_fire \\
        --output-dir experiments/gpu_runs/2026-05-15_sweep_context_layers/low_at_fire \\
        --quick
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd

from .gpu_train_constants import (
    DEFAULT_TEST_YEARS,
    DEVICE_AUTO,
    DEVICE_CPU,
    DEVICE_CUDA,
    SEED,
    TOP_BUCKET_PCT,
)
from .gpu_train_outputs import (
    aggregate_top_features,
    ensure_output_dir,
    write_config,
    write_feature_importance,
    write_folds_parquet,
    write_metrics_summary,
    write_predictions,
    write_readme,
)
from .gpu_train_pipeline import file_sha256, filter_matrix, git_sha, run_fold
from .gpu_train_schema_safe import (
    assert_no_label_leak,
    coerce_binary_label,
    load_schema,
    schema_safe_feature_columns,
)
from .gpu_train_walk_forward import extract_years
from .gpu_train_xgb import resolve_device


def _parse_test_years(arg: str | None) -> tuple[int, ...]:
    if not arg:
        return DEFAULT_TEST_YEARS
    parts = [p.strip() for p in arg.split(",") if p.strip()]
    return tuple(int(p) for p in parts)


def _make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--side", choices=["low", "high", "all"], default="low")
    parser.add_argument("--snapshot", choices=["at_fire", "at_period_close"], default="at_fire")
    parser.add_argument("--event-type", default="all")
    parser.add_argument(
        "--device",
        choices=[DEVICE_AUTO, DEVICE_CUDA, DEVICE_CPU],
        default=DEVICE_AUTO,
    )
    parser.add_argument(
        "--test-years",
        default=None,
        help="comma-separated, e.g. 2020,2021,2022. Defaults to "
        f"{','.join(str(y) for y in DEFAULT_TEST_YEARS)}",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="run only the first test year (smoke-test path)",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--include-manual-cell", action="store_true")
    parser.add_argument("--top-pct", type=float, default=TOP_BUCKET_PCT)
    return parser


def _load_inputs(args: argparse.Namespace) -> tuple[dict[str, Any], pd.DataFrame, list[str]]:
    schema = load_schema(args.schema)
    feature_pool = schema_safe_feature_columns(schema, include_manual_cell=args.include_manual_cell)
    assert_no_label_leak(feature_pool)

    df = pd.read_parquet(args.matrix)
    df = filter_matrix(
        df,
        snapshot=args.snapshot,
        side=args.side,
        event_type=args.event_type,
    )
    if args.label not in df.columns:
        raise KeyError(f"label column not present in matrix: {args.label}")
    return schema, df, feature_pool


def _build_config(
    args: argparse.Namespace,
    device_info,
    feature_pool: list[str],
    n_rows: int,
    test_years: tuple[int, ...],
) -> dict[str, Any]:
    return {
        "matrix": str(args.matrix),
        "matrix_sha256": file_sha256(args.matrix),
        "schema": str(args.schema),
        "label": args.label,
        "side": args.side,
        "snapshot": args.snapshot,
        "event_type": args.event_type,
        "device_requested": device_info.requested,
        "device_resolved": device_info.resolved,
        "xgboost_version": device_info.xgboost_version,
        "cuda_available": device_info.cuda_available,
        "seed": SEED,
        "test_years": list(test_years),
        "include_manual_cell": args.include_manual_cell,
        "top_pct": args.top_pct,
        "n_feature_pool": len(feature_pool),
        "filtered_rows": n_rows,
        "git_sha": git_sha(),
    }


def main() -> int:
    args = _make_parser().parse_args()
    _schema, df, feature_pool = _load_inputs(args)

    y_series = coerce_binary_label(df[args.label])
    df = df.loc[y_series.notna()].copy()
    y = y_series.loc[df.index].astype(int).to_numpy()
    years = extract_years(df)

    device_info = resolve_device(args.device)
    test_years = _parse_test_years(args.test_years)
    if args.quick:
        test_years = test_years[:1]

    output_dir = ensure_output_dir(args.output_dir)
    config = _build_config(args, device_info, feature_pool, int(len(df)), test_years)
    write_config(output_dir, config)

    fold_records: list[dict[str, Any]] = []
    prediction_frames: list[pd.DataFrame] = []
    importance_rows: list[dict[str, Any]] = []
    fold_metric_pairs: list[tuple[int, Any]] = []
    for test_year in test_years:
        result = run_fold(
            df=df,
            years=years,
            y=y,
            label=args.label,
            feature_pool=feature_pool,
            test_year=test_year,
            device=device_info.resolved,
        )
        if result["status"] != "ok":
            fold_records.append(
                {
                    "test_year": result["test_year"],
                    "status": result["status"],
                    "n_train": result.get("n_train"),
                    "n_val": result.get("n_val"),
                    "n_test": result.get("n_test"),
                }
            )
            continue
        fold_records.append(result["record"])
        prediction_frames.append(result["predictions"])
        importance_rows.extend(result["importance"])
        fold_metric_pairs.append((test_year, result["metrics"]))

    write_metrics_summary(output_dir, fold_records)
    write_folds_parquet(output_dir, fold_records)
    write_predictions(output_dir, prediction_frames)
    write_feature_importance(output_dir, importance_rows)
    write_readme(
        output_dir,
        config=config,
        fold_metrics=fold_metric_pairs,
        top_features=aggregate_top_features(importance_rows),
    )
    print(f"wrote {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
