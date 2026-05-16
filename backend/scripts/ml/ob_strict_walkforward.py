"""GPU walk-forward verification on 247's new OB strict release.

Same pattern as sweep_strict_walkforward — multi-year walk-forward
on the 10 strict OB labels (5 behaviors × 2 horizons). Compares GPU
XGB AUC to 247's CPU baseline.
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
    assert_no_label_leak, coerce_binary_label,
    load_schema, schema_safe_feature_columns,
)
from scripts.ml.gpu_train_walk_forward import extract_years
from scripts.ml.gpu_train_xgb import resolve_device
from scripts.ml.gpu_train_constants import DEFAULT_TEST_YEARS

UTC = timezone.utc
ROOT = Path(r"C:\Users\benbr\BacktestStation")
EXPORT = Path(r"D:\BacktestStationData\strategy_lab_core_2026_05_16_strict_order_block")
ANCHORS = EXPORT / "data" / "ml" / "anchors"
MATRIX = ANCHORS / "ob_snapshots_xctx_strict.parquet"
SCHEMA = ANCHORS / "ob_snapshots_xctx_strict.schema.json"
SUMMARY_CSV = ANCHORS / "ob_walk_forward_strict_context_summary.csv"

OUT_DIR = ROOT / "experiments" / "backtests" / "2026-05-16_ob_strict_walkforward"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def _parse_summary(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            try:
                rows.append({
                    "snapshot": r["snapshot"], "side": r["side"], "label": r["label"],
                    "cpu_mean_auc": float(r["mean_test_auc"]),
                    "cpu_min_auc": float(r["min_test_auc"]),
                    "cpu_top_lift": float(r["mean_top_bucket_lift"]),
                    "cpu_base_rate": float(r["mean_base_rate"]),
                })
            except (KeyError, ValueError):
                continue
    return rows


def _run_one(df, schema, label, side, snapshot, device):
    feature_pool = schema_safe_feature_columns(schema, include_manual_cell=False)
    assert_no_label_leak(feature_pool)
    work = filter_matrix(df, snapshot=snapshot, side=side, event_type="all")
    if label not in work.columns:
        return {"status": "label_missing"}
    y_series = coerce_binary_label(work[label])
    work = work.loc[y_series.notna()].copy()
    if len(work) < 100:
        return {"status": "too_few_rows", "n_filtered": int(len(work))}
    y = y_series.loc[work.index].astype(int).to_numpy()
    years = extract_years(work)
    folds = []
    for ty in DEFAULT_TEST_YEARS:
        result = run_fold(df=work, years=years, y=y, label=label,
                          feature_pool=feature_pool, test_year=ty, device=device)
        if result["status"] != "ok":
            continue
        rec = result["record"]
        folds.append({
            "auc_test": rec["auc_test"],
            "top_lift": rec["top_bucket_lift_vs_base"],
            "base_rate": rec["base_rate_test"],
        })
    if not folds:
        return {"status": "no_folds_ok"}
    aucs = [r["auc_test"] for r in folds]
    return {
        "status": "ok",
        "n_filtered": int(len(work)),
        "n_folds_ok": len(folds),
        "gpu_mean_auc": float(np.mean(aucs)),
        "gpu_min_auc": float(np.min(aucs)),
        "gpu_top_lift": float(np.mean([r["top_lift"] for r in folds])),
        "gpu_base_rate": float(np.mean([r["base_rate"] for r in folds])),
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for h in list(logging.root.handlers):
        logging.root.removeHandler(h)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.FileHandler(OUT_DIR / "sweep.log", encoding="utf-8"), logging.StreamHandler(sys.stdout)],
    )

    device_info = resolve_device("auto")
    logging.info(f"device={device_info.resolved} xgb={device_info.xgboost_version}")
    configs = _parse_summary(SUMMARY_CSV)
    logging.info(f"configs to verify: {len(configs)}")

    schema = load_schema(SCHEMA)
    df = pd.read_parquet(MATRIX)
    logging.info(f"loaded {MATRIX.name}: rows={len(df):,} cols={len(df.columns):,}")

    fields = ["matrix", "snapshot", "side", "label", "n_filtered", "n_folds_ok",
              "gpu_mean_auc", "gpu_min_auc", "gpu_top_lift", "gpu_base_rate",
              "cpu_mean_auc", "cpu_min_auc", "cpu_top_lift", "cpu_base_rate",
              "delta_mean_auc", "delta_top_lift", "status", "elapsed_s"]
    cf = (OUT_DIR / "scoreboard.csv").open("w", newline="", encoding="utf-8")
    writer = csv.DictWriter(cf, fieldnames=fields)
    writer.writeheader()

    t0 = time.time()
    for i, cfg in enumerate(configs, 1):
        t1 = time.time()
        try:
            out = _run_one(df, schema, cfg["label"], cfg["side"], cfg["snapshot"], device_info.resolved)
        except Exception as exc:
            logging.exception(f"FAIL {cfg['label']}: {exc}")
            out = {"status": f"error: {type(exc).__name__}"}
        elapsed = time.time() - t1
        row = {
            "matrix": MATRIX.stem, "snapshot": cfg["snapshot"], "side": cfg["side"], "label": cfg["label"],
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
            logging.info(f"  [{i}/{len(configs)}] {cfg['side']:>8}|{cfg['label'][:60]:<60} "
                        f"AUC GPU={out['gpu_mean_auc']:.3f} CPU={cfg['cpu_mean_auc']:.3f} "
                        f"d={(out['gpu_mean_auc']-cfg['cpu_mean_auc']):+.3f} ({elapsed:.0f}s)")
    cf.close()
    logging.info(f"DONE in {(time.time()-t0)/60:.1f} min")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
