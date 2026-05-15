"""GPU XGB on FVG strict labels, per event_type (timeframe).

Hypothesis: the FVG strict matrix mixes 15m/1h/4h/daily FVG events; the
sweep on event_type=all averages them. Splitting by event_type may
expose per-timeframe signal that's hidden in the average.

For each of the 4 labels 247 promoted to walk-forward summary, run GPU
XGB with side=all and one event_type at a time, then compare to the
event_type=all baseline we already have.
"""

from __future__ import annotations

import csv
import logging
import sys
import time
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

ROOT = Path(r"C:\Users\benbr\BacktestStation")
EXPORT = Path(r"D:\BacktestStationData\strategy_lab_core_2026_05_15_strict_reactions")
ANCHORS = EXPORT / "data" / "ml" / "anchors"
MATRIX = ANCHORS / "fvg_snapshots_xctx_fvggeom_obgeom_strict.parquet"
SCHEMA = ANCHORS / "fvg_snapshots_xctx_fvggeom_obgeom_strict.schema.json"
OUT_DIR = ROOT / "experiments" / "gpu_runs" / "2026-05-15_fvg_per_timeframe"

LABELS = [
    "label.strict.forward_10c.after_tap_failed_1x_against",
    "label.strict.no_touch_continuation",
    "label.strict.forward_10c.after_tap_1x_clean",
    "label.strict.tap_wick_rejected",
]
EVENT_TYPES = ["15m_fvg", "1h_fvg", "4h_fvg", "daily_fvg", "all"]


def _run_one(df, label, snapshot, side, event_type, feature_pool, device):
    work = filter_matrix(df, snapshot=snapshot, side=side, event_type=event_type)
    if label not in work.columns:
        return {"status": "label_missing", "n_filtered": int(len(work))}
    y_series = coerce_binary_label(work[label])
    work = work.loc[y_series.notna()].copy()
    if len(work) < 200:
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
        fold_records.append((rec["auc_test"], rec["top_bucket_lift_vs_base"], rec["base_rate_test"]))
    if not fold_records:
        return {"status": "no_folds_ok", "n_filtered": int(len(work))}
    aucs = [r[0] for r in fold_records]
    lifts = [r[1] for r in fold_records]
    rates = [r[2] for r in fold_records]
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
    schema = load_schema(SCHEMA)
    feature_pool = schema_safe_feature_columns(schema, include_manual_cell=False)
    assert_no_label_leak(feature_pool)
    logging.info(f"loading {MATRIX.name}")
    df = pd.read_parquet(MATRIX)
    logging.info(f"  rows={len(df):,} cols={len(df.columns):,}")

    fieldnames = ["matrix", "snapshot", "side", "event_type", "label",
                  "n_filtered", "n_folds_ok",
                  "gpu_mean_auc", "gpu_min_auc", "gpu_top_lift", "gpu_base_rate",
                  "status", "elapsed_s"]
    cf = out_csv.open("w", newline="", encoding="utf-8")
    writer = csv.DictWriter(cf, fieldnames=fieldnames)
    writer.writeheader()

    sw = time.time()
    total = len(LABELS) * len(EVENT_TYPES)
    i = 0
    for label in LABELS:
        for et in EVENT_TYPES:
            i += 1
            t0 = time.time()
            try:
                out = _run_one(df=df, label=label, snapshot="at_fire", side="all",
                               event_type=et, feature_pool=feature_pool, device=device_info.resolved)
            except Exception as exc:
                logging.exception(f"FAIL {label}/{et}: {exc}")
                out = {"status": f"error: {type(exc).__name__}", "n_filtered": 0}
            elapsed = time.time() - t0
            row = {
                "matrix": MATRIX.stem,
                "snapshot": "at_fire",
                "side": "all",
                "event_type": et,
                "label": label,
                "n_filtered": out.get("n_filtered", 0),
                "n_folds_ok": out.get("n_folds_ok", 0),
                "gpu_mean_auc": out.get("gpu_mean_auc"),
                "gpu_min_auc": out.get("gpu_min_auc"),
                "gpu_top_lift": out.get("gpu_top_lift"),
                "gpu_base_rate": out.get("gpu_base_rate"),
                "status": out["status"],
                "elapsed_s": round(elapsed, 1),
            }
            writer.writerow(row)
            cf.flush()
            if out["status"] == "ok":
                logging.info(
                    f"  [{i}/{total}] OK {et:>10} {label[:50]:<50} "
                    f"AUC={out['gpu_mean_auc']:.3f} lift={out['gpu_top_lift']:+.3f} "
                    f"base={out['gpu_base_rate']:.3f} n={out['n_filtered']:>6} ({elapsed:.0f}s)"
                )
            else:
                logging.info(f"  [{i}/{total}] SKIP {et} {label[:50]} status={out['status']}")
    cf.close()
    logging.info(f"=== DONE in {(time.time()-sw)/60:.1f} min ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
