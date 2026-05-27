"""Walk-forward training orchestrator for tsfm_milk_v0.

For each (model, fold) combination:
  1. Load train + val phase data from out/dataset/
  2. Instantiate the forecaster
  3. fit() on train, optionally using val for early stopping
  4. predict_proba() on val and test
  5. Serialize predictions to out/predictions/{model}/fold_{fid}_{phase}.parquet
  6. Save the trained model to out/models/{model}/fold_{fid}/

Usage:
  python train_walkforward.py --models naive lightgbm --folds 1 2 3 4 5 6
  python train_walkforward.py --models naive            # just naive, all folds
  python train_walkforward.py                           # everything

Available models (v0):
  - naive            (NaiveBaseline)
  - lightgbm         (LightGBMBaselineForecaster)

Available later (v0.5+):
  - ttm              (TTMForecaster — not yet implemented)
  - moirai           (MoiraiForecaster — not yet implemented)

Output schema for predictions parquet (evaluate.py expects this exactly):
  ts_decision, symbol, fold_id, phase, model_name, entry_price,
  {h}_p_flat, {h}_p_up, {h}_p_down, {h}_label, {h}_realized_logret
where {h} ∈ {h_15m, h_30m, h_60m, h_90m, h_240m}.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time as time_mod
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

THIS_FILE = Path(__file__).resolve()
EXPERIMENT_DIR = THIS_FILE.parent
REPO_ROOT = EXPERIMENT_DIR.parents[1]

sys.path.insert(0, str(EXPERIMENT_DIR))

from forecaster import (  # noqa: E402
    CLASS_CODES,
    HORIZON_KEYS,
    SYMBOL_ORDER,
    Forecaster,
)

CLASS_FLAT = CLASS_CODES["flat"]
CLASS_UP = CLASS_CODES["up"]
CLASS_DOWN = CLASS_CODES["down"]

SYMBOL_SHORT = {"ES.c.0": "ES", "NQ.c.0": "NQ", "YM.c.0": "YM", "RTY.c.0": "RTY"}


# ---------------------------------------------------------------------------
# Dataset loading
# ---------------------------------------------------------------------------


def horizon_min_from_key(h_key: str) -> int:
    """h_15m -> 15"""
    return int(h_key.replace("h_", "").replace("m", ""))


def load_phase(dataset_dir: Path, fold_id, phase: str) -> tuple[np.ndarray, dict[str, np.ndarray], pd.DataFrame]:
    """Load one (fold, phase) into (inputs_tensor, labels_dict, meta_df).

    Returns:
      inputs: shape (N, lookback, n_channels), float32
      labels: dict[h_key, (N, n_symbols)] int8 — only valid where label != -1
      meta_df: DataFrame with ts_event, entry prices, forward returns, labels per symbol/horizon
    """
    sub = dataset_dir / f"fold_{fold_id}_{phase}"
    if not sub.exists():
        raise FileNotFoundError(f"Phase folder not found: {sub}")
    meta = pd.read_parquet(sub / "meta.parquet")
    inputs = np.load(sub / "inputs.npy")

    labels: dict[str, np.ndarray] = {}
    for h_key in HORIZON_KEYS:
        h = horizon_min_from_key(h_key)
        cols = []
        for sym in SYMBOL_ORDER:
            s = SYMBOL_SHORT[sym]
            col_name = f"{s}_label_h{h}"
            if col_name not in meta.columns:
                raise KeyError(f"missing column {col_name} in meta")
            cols.append(meta[col_name].to_numpy(dtype=np.int8))
        labels[h_key] = np.stack(cols, axis=1)  # (N, n_symbols)

    return inputs, labels, meta


# ---------------------------------------------------------------------------
# Predictions serialization
# ---------------------------------------------------------------------------


def serialize_predictions(
    *,
    proba: dict[str, np.ndarray],   # h_key -> (N, n_symbols, n_classes)
    meta: pd.DataFrame,
    fold_id,
    phase: str,
    model_name: str,
    model_version: str,
) -> pd.DataFrame:
    """Convert ForecastBatch.proba + meta into one row per (anchor, symbol) for evaluate.py."""
    n = meta.shape[0]
    n_symbols = len(SYMBOL_ORDER)

    # Build long-format rows: each anchor row × 4 symbols = 4 output rows.
    blocks = []
    for sym_idx, sym in enumerate(SYMBOL_ORDER):
        s = SYMBOL_SHORT[sym]
        block: dict[str, np.ndarray | list] = {
            "ts_decision": meta["ts_event"].to_numpy(),
            "symbol": [sym] * n,
            "fold_id": [str(fold_id)] * n,
            "phase": [phase] * n,
            "model_name": [model_name] * n,
            "model_version": [model_version] * n,
            "entry_price": meta[f"{s}_entry_price"].to_numpy(),
        }
        for h_key in HORIZON_KEYS:
            h = horizon_min_from_key(h_key)
            arr = proba[h_key]  # (N, n_symbols, n_classes)
            block[f"{h_key}_p_flat"] = arr[:, sym_idx, CLASS_FLAT].astype(np.float32)
            block[f"{h_key}_p_up"] = arr[:, sym_idx, CLASS_UP].astype(np.float32)
            block[f"{h_key}_p_down"] = arr[:, sym_idx, CLASS_DOWN].astype(np.float32)
            block[f"{h_key}_label"] = meta[f"{s}_label_h{h}"].to_numpy(dtype=np.int8)
            block[f"{h_key}_realized_logret"] = meta[f"{s}_fwd_logret_h{h}"].to_numpy(dtype=np.float32)
        blocks.append(pd.DataFrame(block))

    return pd.concat(blocks, ignore_index=True)


# ---------------------------------------------------------------------------
# Model factory
# ---------------------------------------------------------------------------


def make_forecaster(model_name: str) -> Forecaster:
    """Instantiate a Forecaster by short name."""
    if model_name == "naive":
        from baseline_naive import NaiveBaseline
        return NaiveBaseline()
    if model_name == "lightgbm":
        from baseline_lightgbm import LightGBMBaselineForecaster
        return LightGBMBaselineForecaster(n_estimators=200, last_window=60, learning_rate=0.05)
    if model_name == "ttm":
        try:
            from ttm_forecaster import TTMForecaster  # type: ignore
        except (ImportError, NotImplementedError):
            raise NotImplementedError(
                "ttm_forecaster not yet implemented. Skip or train other models first."
            )
        return TTMForecaster()
    if model_name == "moirai":
        raise NotImplementedError("moirai_forecaster is v0.5 work.")
    raise ValueError(f"unknown model: {model_name}")


# ---------------------------------------------------------------------------
# Train one (model, fold) combination
# ---------------------------------------------------------------------------


def train_one(
    *,
    model_name: str,
    fold_id,
    dataset_dir: Path,
    preds_dir: Path,
    models_dir: Path,
    run_timestamp: str,
) -> dict:
    """Train a single (model, fold). Returns a summary dict."""
    t0 = time_mod.time()
    print(f"\n  [{model_name}] fold {fold_id}: loading data...", flush=True)

    train_inputs, train_labels, train_meta = load_phase(dataset_dir, fold_id, "train")
    val_inputs, val_labels, val_meta = load_phase(dataset_dir, fold_id, "val")
    test_inputs, test_labels, test_meta = load_phase(dataset_dir, fold_id, "test")
    print(
        f"  [{model_name}] fold {fold_id}: train={len(train_meta):,} val={len(val_meta):,} "
        f"test={len(test_meta):,}",
        flush=True,
    )

    forecaster = make_forecaster(model_name)
    model_version = f"{forecaster.name}__{run_timestamp}__fold{fold_id}"

    print(f"  [{model_name}] fold {fold_id}: fitting...", flush=True)
    t_fit = time_mod.time()
    forecaster.fit(
        train_inputs=train_inputs,
        train_labels=train_labels,
        val_inputs=val_inputs,
        val_labels=val_labels,
        train_ts=train_meta["ts_event"].to_numpy(),
        val_ts=val_meta["ts_event"].to_numpy(),
    )
    print(f"  [{model_name}] fold {fold_id}: fit done in {time_mod.time()-t_fit:.1f}s", flush=True)

    # Save model
    model_subdir = models_dir / model_name / f"fold_{fold_id}"
    model_subdir.mkdir(parents=True, exist_ok=True)
    forecaster.save(model_subdir)

    # Predict on val and test
    t_pred = time_mod.time()
    val_out = forecaster.predict_proba(val_inputs, val_meta["ts_event"].to_numpy())
    test_out = forecaster.predict_proba(test_inputs, test_meta["ts_event"].to_numpy())
    print(
        f"  [{model_name}] fold {fold_id}: predict done in {time_mod.time()-t_pred:.1f}s",
        flush=True,
    )

    # Serialize + write
    preds_subdir = preds_dir / model_name
    preds_subdir.mkdir(parents=True, exist_ok=True)

    val_df = serialize_predictions(
        proba=val_out.proba, meta=val_meta, fold_id=fold_id, phase="val",
        model_name=model_name, model_version=model_version,
    )
    val_path = preds_subdir / f"fold_{fold_id}_val.parquet"
    val_df.to_parquet(val_path, index=False)

    test_df = serialize_predictions(
        proba=test_out.proba, meta=test_meta, fold_id=fold_id, phase="test",
        model_name=model_name, model_version=model_version,
    )
    test_path = preds_subdir / f"fold_{fold_id}_test.parquet"
    test_df.to_parquet(test_path, index=False)

    elapsed = time_mod.time() - t0
    summary = {
        "model_name": model_name,
        "fold_id": str(fold_id),
        "model_version": model_version,
        "n_train": int(len(train_meta)),
        "n_val": int(len(val_meta)),
        "n_test": int(len(test_meta)),
        "val_pred_rows": int(len(val_df)),
        "test_pred_rows": int(len(test_df)),
        "val_pred_path": str(val_path.relative_to(EXPERIMENT_DIR)),
        "test_pred_path": str(test_path.relative_to(EXPERIMENT_DIR)),
        "model_dir": str(model_subdir.relative_to(EXPERIMENT_DIR)),
        "elapsed_sec": round(elapsed, 1),
        "status": "ok",
    }
    print(
        f"  [{model_name}] fold {fold_id}: WROTE val={len(val_df):,}rows test={len(test_df):,}rows "
        f"(total {elapsed:.1f}s)",
        flush=True,
    )
    return summary


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--models", nargs="+", default=["naive", "lightgbm"],
                   help="Models to train. Default: naive lightgbm")
    p.add_argument("--folds", nargs="+", default=["1", "2", "3", "4", "5", "6"],
                   help="Fold IDs to train. Default: 1-6")
    p.add_argument("--dataset-dir", default=str(EXPERIMENT_DIR / "out" / "dataset"))
    p.add_argument("--preds-dir", default=str(EXPERIMENT_DIR / "out" / "predictions"))
    p.add_argument("--models-dir", default=str(EXPERIMENT_DIR / "out" / "models"))
    p.add_argument("--continue-on-error", action="store_true",
                   help="Don't stop the whole run if one (model, fold) fails")
    args = p.parse_args(argv)

    dataset_dir = Path(args.dataset_dir).resolve()
    preds_dir = Path(args.preds_dir).resolve()
    models_dir = Path(args.models_dir).resolve()
    preds_dir.mkdir(parents=True, exist_ok=True)
    models_dir.mkdir(parents=True, exist_ok=True)

    if not dataset_dir.exists():
        print(f"ERROR: dataset_dir {dataset_dir} does not exist. Run build_dataset.py first.")
        return 1

    run_timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    print(f"=== train_walkforward starting (run_timestamp={run_timestamp}) ===")
    print(f"  models: {args.models}")
    print(f"  folds:  {args.folds}")
    print(f"  dataset_dir: {dataset_dir.relative_to(EXPERIMENT_DIR)}")
    print(f"  preds_dir:   {preds_dir.relative_to(EXPERIMENT_DIR)}")
    print(f"  models_dir:  {models_dir.relative_to(EXPERIMENT_DIR)}")

    summaries: list[dict] = []
    t_total = time_mod.time()

    for model_name in args.models:
        print(f"\n=== model {model_name} ===")
        for fold_id in args.folds:
            try:
                s = train_one(
                    model_name=model_name,
                    fold_id=fold_id,
                    dataset_dir=dataset_dir,
                    preds_dir=preds_dir,
                    models_dir=models_dir,
                    run_timestamp=run_timestamp,
                )
                summaries.append(s)
            except Exception as e:
                print(
                    f"  [{model_name}] fold {fold_id}: FAILED -- {type(e).__name__}: {e}",
                    flush=True,
                )
                summaries.append({
                    "model_name": model_name,
                    "fold_id": str(fold_id),
                    "status": "error",
                    "error": f"{type(e).__name__}: {e}",
                    "traceback": traceback.format_exc()[-800:],
                })
                if not args.continue_on_error:
                    return 2

    total_sec = time_mod.time() - t_total
    print(f"\n=== train_walkforward done in {total_sec:.1f}s ===")
    n_ok = sum(1 for s in summaries if s.get("status") == "ok")
    n_err = sum(1 for s in summaries if s.get("status") == "error")
    print(f"  ok={n_ok}  errors={n_err}")

    summary_path = preds_dir / f"train_summary_{run_timestamp}.json"
    summary_path.write_text(
        json.dumps({"run_timestamp": run_timestamp, "total_sec": total_sec, "runs": summaries}, indent=2, default=str),
        encoding="utf-8",
    )
    print(f"  summary written: {summary_path.relative_to(EXPERIMENT_DIR)}")
    return 0 if n_err == 0 else 3


if __name__ == "__main__":
    raise SystemExit(main())
