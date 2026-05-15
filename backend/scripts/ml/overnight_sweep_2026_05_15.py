"""Large GPU XGB sweep across every walk-forward summary in the export.

For each (matrix, snapshot, side, label) config that 247/cloud already ran
on CPU LightGBM, re-run on GPU XGBoost and collect a unified scoreboard.

Designed for one ~2-3 hour run in-process: each matrix is loaded once,
then all its (label, side, snapshot) configs are evaluated against the
in-memory dataframe so we don't pay 30 GB+ of repeated parquet IO.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

# Reuse the runner's modules.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from scripts.ml.gpu_train_pipeline import file_sha256, filter_matrix, git_sha, run_fold
from scripts.ml.gpu_train_schema_safe import (
    assert_no_label_leak,
    coerce_binary_label,
    load_schema,
    schema_safe_feature_columns,
)
from scripts.ml.gpu_train_walk_forward import extract_years
from scripts.ml.gpu_train_xgb import resolve_device
from scripts.ml.gpu_train_constants import DEFAULT_TEST_YEARS

UTC = timezone.utc
ROOT = Path(r"C:\Users\benbr\BacktestStation")
EXPORT_ROOT = Path(r"D:\BacktestStationData\strategy_lab_core_2026_05_14_context_layers")
ANCHORS = EXPORT_ROOT / "data" / "ml" / "anchors"
OUT_DIR = ROOT / "experiments" / "gpu_runs" / "2026-05-15_full_scoreboard"

# Summary file -> matrix base name. We only take the widest (terminal) summary
# per event family to keep total wall time reasonable.
SUMMARY_TO_MATRIX: list[tuple[str, str]] = [
    ("forming_vp_walk_forward_gapctx_summary.csv", "forming_vp_snapshots_xctx_gapctx"),
    ("fvg_walk_forward_fvggeom_summary.csv", "fvg_snapshots_xctx_fvggeom_obgeom"),
    ("itr_snapshot_walk_forward_summary_xctx.csv", "itr_snapshots_xctx"),
    ("macro_snapshot_walk_forward_summary_xctx.csv", "macro_event_snapshots_xctx"),
    ("opening_gap_strict_context_walk_forward_summary.csv",
     "opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime_strict"),
    ("opening_gap_walk_forward_xctx_gapctx_obgeom_liqgeom_regime_summary.csv",
     "opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime"),
    ("smt_previous_day_walk_forward_fvggeom_obgeom_liqgeom_regime_summary.csv",
     "smt_previous_day_snapshots_xctx_fvggeom_obgeom_liqgeom_regime"),
    ("sweep_walk_forward_fvggeom_obgeom_liqgeom_regime_summary.csv",
     "sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime"),
    ("tp_walk_forward_fvggeom_summary.csv", "tp_snapshots_xctx_fvggeom_obgeom"),
    ("vp_walk_forward_v2_xctx_summary.csv", "vp_snapshots_xctx"),
]


def _parse_summary(path: Path) -> list[dict]:
    """Return list of dicts with snapshot/side/label/cpu_mean_auc/cpu_min_auc/cpu_top_lift/cpu_base_rate."""
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            try:
                rows.append({
                    "snapshot": r["snapshot"],
                    "side": r["side"],
                    "label": r["label"],
                    "cpu_mean_auc": float(r["mean_test_auc"]),
                    "cpu_min_auc": float(r["min_test_auc"]),
                    "cpu_top_lift": float(r["mean_top_bucket_lift"]),
                    "cpu_base_rate": float(r["mean_base_rate"]),
                })
            except (KeyError, ValueError):
                continue
    return rows


def _run_one(
    *,
    df: pd.DataFrame,
    label: str,
    side: str,
    snapshot: str,
    feature_pool: list[str],
    device: str,
) -> dict:
    """Run all 6 folds for one config. Return summary dict."""
    work = filter_matrix(df, snapshot=snapshot, side=side, event_type="all")
    if label not in work.columns:
        return {"status": "label_missing", "n_filtered": int(len(work))}
    y_series = coerce_binary_label(work[label])
    work = work.loc[y_series.notna()].copy()
    if len(work) < 100:
        return {"status": "too_few_rows", "n_filtered": int(len(work))}
    y = y_series.loc[work.index].astype(int).to_numpy()
    years = extract_years(work)
    fold_records: list[dict] = []
    for test_year in DEFAULT_TEST_YEARS:
        result = run_fold(
            df=work, years=years, y=y, label=label,
            feature_pool=feature_pool, test_year=test_year, device=device,
        )
        if result["status"] != "ok":
            continue
        rec = result["record"]
        fold_records.append({
            "test_year": rec["test_year"],
            "auc_test": rec["auc_test"],
            "top_rate": rec["top_bucket_rate"],
            "top_lift": rec["top_bucket_lift_vs_base"],
            "base_rate": rec["base_rate_test"],
        })
    if not fold_records:
        return {"status": "no_folds_ok", "n_filtered": int(len(work))}
    aucs = [r["auc_test"] for r in fold_records]
    lifts = [r["top_lift"] for r in fold_records]
    rates = [r["base_rate"] for r in fold_records]
    return {
        "status": "ok",
        "n_filtered": int(len(work)),
        "n_folds_ok": len(fold_records),
        "gpu_mean_auc": float(np.mean(aucs)),
        "gpu_min_auc": float(np.min(aucs)),
        "gpu_top_lift": float(np.mean(lifts)),
        "gpu_base_rate": float(np.mean(rates)),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit-per-matrix", type=int, default=None,
                        help="Cap configs per matrix (for debugging).")
    parser.add_argument("--max-rows-per-matrix-load", type=int, default=None,
                        help="(unused) sample rows during load for testing.")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    log_path = OUT_DIR / "sweep.log"
    out_csv = OUT_DIR / "scoreboard.csv"
    progress_path = OUT_DIR / "progress.json"

    for handler in list(logging.root.handlers):
        logging.root.removeHandler(handler)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.FileHandler(log_path, encoding="utf-8"), logging.StreamHandler(sys.stdout)],
    )

    device_info = resolve_device("auto")
    logging.info(f"device_resolved={device_info.resolved} xgboost={device_info.xgboost_version} cuda={device_info.cuda_available}")
    logging.info(f"output dir: {OUT_DIR}")

    fieldnames = [
        "matrix", "snapshot", "side", "label",
        "n_filtered", "n_folds_ok",
        "gpu_mean_auc", "gpu_min_auc", "gpu_top_lift", "gpu_base_rate",
        "cpu_mean_auc", "cpu_min_auc", "cpu_top_lift", "cpu_base_rate",
        "delta_mean_auc", "delta_top_lift",
        "status", "elapsed_s",
    ]
    csvfile = out_csv.open("w", newline="", encoding="utf-8")
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    csvfile.flush()

    overall_start = time.time()
    total_done = 0
    total_planned = 0

    # First pass — count planned configs.
    plan: list[tuple[str, Path, list[dict]]] = []
    for summary_name, matrix_name in SUMMARY_TO_MATRIX:
        summary_path = ANCHORS / summary_name
        matrix_path = ANCHORS / (matrix_name + ".parquet")
        schema_path = ANCHORS / (matrix_name + ".schema.json")
        if not (summary_path.exists() and matrix_path.exists() and schema_path.exists()):
            logging.warning(f"SKIP {matrix_name}: missing summary/matrix/schema")
            continue
        configs = _parse_summary(summary_path)
        if args.limit_per_matrix:
            configs = configs[: args.limit_per_matrix]
        plan.append((matrix_name, matrix_path, schema_path, configs))
        total_planned += len(configs)
    logging.info(f"planned: {total_planned} configs across {len(plan)} matrices")
    progress_path.write_text(json.dumps({"total_planned": total_planned, "done": 0}, indent=2))

    for matrix_name, matrix_path, schema_path, configs in plan:
        logging.info(f"=== MATRIX {matrix_name} ({len(configs)} configs) ===")
        t0 = time.time()
        schema = load_schema(schema_path)
        feature_pool = schema_safe_feature_columns(schema, include_manual_cell=False)
        assert_no_label_leak(feature_pool)
        df_full = pd.read_parquet(matrix_path)
        logging.info(f"  loaded matrix: rows={len(df_full):,} cols={len(df_full.columns):,} ({(time.time()-t0):.1f}s)")

        for i, cfg in enumerate(configs, 1):
            cfg_t0 = time.time()
            tag = f"{matrix_name} | {cfg['snapshot']} | {cfg['side']} | {cfg['label']}"
            try:
                out = _run_one(
                    df=df_full, label=cfg["label"], side=cfg["side"], snapshot=cfg["snapshot"],
                    feature_pool=feature_pool, device=device_info.resolved,
                )
            except Exception as exc:
                logging.exception(f"FAIL {tag}: {exc}")
                out = {"status": f"error: {type(exc).__name__}", "n_filtered": 0}
            elapsed = time.time() - cfg_t0

            row = {
                "matrix": matrix_name,
                "snapshot": cfg["snapshot"],
                "side": cfg["side"],
                "label": cfg["label"],
                "cpu_mean_auc": cfg["cpu_mean_auc"],
                "cpu_min_auc": cfg["cpu_min_auc"],
                "cpu_top_lift": cfg["cpu_top_lift"],
                "cpu_base_rate": cfg["cpu_base_rate"],
                "n_filtered": out.get("n_filtered", 0),
                "n_folds_ok": out.get("n_folds_ok", 0),
                "gpu_mean_auc": out.get("gpu_mean_auc"),
                "gpu_min_auc": out.get("gpu_min_auc"),
                "gpu_top_lift": out.get("gpu_top_lift"),
                "gpu_base_rate": out.get("gpu_base_rate"),
                "delta_mean_auc": (
                    out["gpu_mean_auc"] - cfg["cpu_mean_auc"]
                    if out.get("gpu_mean_auc") is not None else None
                ),
                "delta_top_lift": (
                    out["gpu_top_lift"] - cfg["cpu_top_lift"]
                    if out.get("gpu_top_lift") is not None else None
                ),
                "status": out["status"],
                "elapsed_s": round(elapsed, 1),
            }
            writer.writerow(row)
            csvfile.flush()
            total_done += 1

            if out["status"] == "ok":
                logging.info(
                    f"  [{i}/{len(configs)}] OK {cfg['side']:>10}|{cfg['snapshot']:<16}|{cfg['label'][:60]:<60} "
                    f"AUC GPU={out['gpu_mean_auc']:.3f} CPU={cfg['cpu_mean_auc']:.3f} d={(out['gpu_mean_auc']-cfg['cpu_mean_auc']):+.3f} "
                    f"({elapsed:.0f}s)"
                )
            else:
                logging.info(
                    f"  [{i}/{len(configs)}] SKIP {cfg['side']:>10}|{cfg['snapshot']:<16}|{cfg['label'][:60]:<60} "
                    f"status={out['status']} ({elapsed:.0f}s)"
                )

            if total_done % 10 == 0:
                progress_path.write_text(json.dumps({
                    "total_planned": total_planned,
                    "done": total_done,
                    "current_matrix": matrix_name,
                    "elapsed_s_so_far": round(time.time() - overall_start, 1),
                }, indent=2))

        # free the matrix before loading the next one.
        del df_full
        logging.info(f"  matrix {matrix_name} complete in {(time.time()-t0)/60:.1f} min")

    csvfile.close()
    total_elapsed = time.time() - overall_start
    progress_path.write_text(json.dumps({
        "total_planned": total_planned,
        "done": total_done,
        "elapsed_s_total": round(total_elapsed, 1),
        "finished_at": datetime.now(UTC).isoformat(),
    }, indent=2))
    logging.info(f"=== DONE in {total_elapsed/60:.1f} min ({total_done} configs) ===")
    logging.info(f"scoreboard: {out_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
