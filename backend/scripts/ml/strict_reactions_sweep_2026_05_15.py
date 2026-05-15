"""GPU XGB sweep over the 2026-05-15 strict-reactions release.

Targets two CPU walk-forward summaries that 247 pushed in commit 1909d5f:

  fvg_walk_forward_strict_context_summary.csv         (4 configs)
  opening_gap_walk_forward_strict_context_summary.csv (12 configs)

Pulls the matching matrix + schema for each summary, loads the matrix
once, and runs GPU XGB across every (snapshot, side, label) row. Writes
a unified scoreboard CSV with GPU vs CPU comparisons.
"""

from __future__ import annotations

import csv
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from scripts.ml.gpu_train_pipeline import filter_matrix, run_fold
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
EXPORT_ROOT = Path(r"D:\BacktestStationData\strategy_lab_core_2026_05_15_strict_reactions")
ANCHORS = EXPORT_ROOT / "data" / "ml" / "anchors"
OUT_DIR = ROOT / "experiments" / "gpu_runs" / "2026-05-15_strict_reactions"

SUMMARY_TO_MATRIX: list[tuple[str, str]] = [
    ("fvg_walk_forward_strict_context_summary.csv",
     "fvg_snapshots_xctx_fvggeom_obgeom_strict"),
    ("opening_gap_walk_forward_strict_context_summary.csv",
     "opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime_strict"),
]


def _parse_summary(path: Path) -> list[dict]:
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


def _run_one(*, df, label, side, snapshot, feature_pool, device):
    work = filter_matrix(df, snapshot=snapshot, side=side, event_type="all")
    if label not in work.columns:
        return {"status": "label_missing", "n_filtered": int(len(work))}
    y_series = coerce_binary_label(work[label])
    work = work.loc[y_series.notna()].copy()
    if len(work) < 100:
        return {"status": "too_few_rows", "n_filtered": int(len(work))}
    y = y_series.loc[work.index].astype(int).to_numpy()
    years = extract_years(work)
    fold_records = []
    for test_year in DEFAULT_TEST_YEARS:
        result = run_fold(df=work, years=years, y=y, label=label,
                          feature_pool=feature_pool, test_year=test_year, device=device)
        if result["status"] != "ok":
            continue
        rec = result["record"]
        fold_records.append({
            "auc_test": rec["auc_test"],
            "top_lift": rec["top_bucket_lift_vs_base"],
            "base_rate": rec["base_rate_test"],
        })
    if not fold_records:
        return {"status": "no_folds_ok", "n_filtered": int(len(work))}
    return {
        "status": "ok",
        "n_filtered": int(len(work)),
        "n_folds_ok": len(fold_records),
        "gpu_mean_auc": float(np.mean([r["auc_test"] for r in fold_records])),
        "gpu_min_auc": float(np.min([r["auc_test"] for r in fold_records])),
        "gpu_top_lift": float(np.mean([r["top_lift"] for r in fold_records])),
        "gpu_base_rate": float(np.mean([r["base_rate"] for r in fold_records])),
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    log_path = OUT_DIR / "sweep.log"
    out_csv = OUT_DIR / "scoreboard.csv"
    for h in list(logging.root.handlers):
        logging.root.removeHandler(h)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.FileHandler(log_path, encoding="utf-8"), logging.StreamHandler(sys.stdout)],
    )

    device_info = resolve_device("auto")
    logging.info(f"device={device_info.resolved} xgb={device_info.xgboost_version}")

    fieldnames = [
        "matrix", "snapshot", "side", "label",
        "n_filtered", "n_folds_ok",
        "gpu_mean_auc", "gpu_min_auc", "gpu_top_lift", "gpu_base_rate",
        "cpu_mean_auc", "cpu_min_auc", "cpu_top_lift", "cpu_base_rate",
        "delta_mean_auc", "delta_top_lift",
        "status", "elapsed_s",
    ]
    cf = out_csv.open("w", newline="", encoding="utf-8")
    writer = csv.DictWriter(cf, fieldnames=fieldnames)
    writer.writeheader()

    overall_t0 = time.time()
    for summary_name, matrix_name in SUMMARY_TO_MATRIX:
        s_path = ANCHORS / summary_name
        m_path = ANCHORS / (matrix_name + ".parquet")
        sc_path = ANCHORS / (matrix_name + ".schema.json")
        if not (s_path.exists() and m_path.exists() and sc_path.exists()):
            logging.warning(f"SKIP {matrix_name}: missing files")
            continue
        configs = _parse_summary(s_path)
        logging.info(f"=== {matrix_name} ({len(configs)} configs) ===")
        t0 = time.time()
        schema = load_schema(sc_path)
        feature_pool = schema_safe_feature_columns(schema, include_manual_cell=False)
        assert_no_label_leak(feature_pool)
        df = pd.read_parquet(m_path)
        logging.info(f"  loaded: rows={len(df):,} cols={len(df.columns):,} ({(time.time()-t0):.1f}s)")

        for i, cfg in enumerate(configs, 1):
            t1 = time.time()
            try:
                out = _run_one(df=df, label=cfg["label"], side=cfg["side"], snapshot=cfg["snapshot"],
                               feature_pool=feature_pool, device=device_info.resolved)
            except Exception as exc:
                logging.exception(f"FAIL {cfg['label']}: {exc}")
                out = {"status": f"error: {type(exc).__name__}", "n_filtered": 0}
            elapsed = time.time() - t1
            row = {
                "matrix": matrix_name,
                "snapshot": cfg["snapshot"], "side": cfg["side"], "label": cfg["label"],
                "cpu_mean_auc": cfg["cpu_mean_auc"], "cpu_min_auc": cfg["cpu_min_auc"],
                "cpu_top_lift": cfg["cpu_top_lift"], "cpu_base_rate": cfg["cpu_base_rate"],
                "n_filtered": out.get("n_filtered", 0), "n_folds_ok": out.get("n_folds_ok", 0),
                "gpu_mean_auc": out.get("gpu_mean_auc"), "gpu_min_auc": out.get("gpu_min_auc"),
                "gpu_top_lift": out.get("gpu_top_lift"), "gpu_base_rate": out.get("gpu_base_rate"),
                "delta_mean_auc": (out["gpu_mean_auc"] - cfg["cpu_mean_auc"]) if out.get("gpu_mean_auc") is not None else None,
                "delta_top_lift": (out["gpu_top_lift"] - cfg["cpu_top_lift"]) if out.get("gpu_top_lift") is not None else None,
                "status": out["status"], "elapsed_s": round(elapsed, 1),
            }
            writer.writerow(row)
            cf.flush()
            if out["status"] == "ok":
                logging.info(
                    f"  [{i}/{len(configs)}] OK {cfg['side']:>12}|{cfg['label'][:60]:<60} "
                    f"AUC GPU={out['gpu_mean_auc']:.3f} CPU={cfg['cpu_mean_auc']:.3f} "
                    f"d={(out['gpu_mean_auc']-cfg['cpu_mean_auc']):+.3f} "
                    f"lift GPU={out['gpu_top_lift']:+.3f} CPU={cfg['cpu_top_lift']:+.3f} ({elapsed:.0f}s)"
                )
            else:
                logging.info(f"  [{i}/{len(configs)}] SKIP status={out['status']}")
        del df
        logging.info(f"  matrix done in {(time.time()-t0)/60:.1f} min")
    cf.close()
    logging.info(f"=== DONE in {(time.time()-overall_t0)/60:.1f} min ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
