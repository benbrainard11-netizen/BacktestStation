"""Optuna hyperparameter search for LightGBMBaselineForecaster.

Per horizon, search over (n_estimators, learning_rate, num_leaves, min_child_samples,
reg_alpha, reg_lambda, feature_fraction, bagging_fraction). Objective: mean val
ROC-AUC across the 4 symbols (pooled). Uses ONLY fold 4 (largest train set with
strong signal per our walk-forward findings) to keep search cost bounded.

After tuning, the best HPs per horizon get written to:
  config/tuned_lightgbm_hps.yaml

Then `train_walkforward.py --models lightgbm_tuned` will pick them up via the
factory in train_walkforward.py.

Usage:
  python tune_lightgbm.py --n-trials 30          (default: ~30 per horizon, ~1-1.5 hr total)
  python tune_lightgbm.py --n-trials 50          (more thorough, ~2-3 hr)
  python tune_lightgbm.py --horizons h_60m h_90m (just tune the best cells)
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

THIS_FILE = Path(__file__).resolve()
EXPERIMENT_DIR = THIS_FILE.parent
REPO_ROOT = EXPERIMENT_DIR.parents[1]

sys.path.insert(0, str(EXPERIMENT_DIR))

from forecaster import HORIZON_KEYS, SYMBOL_ORDER  # noqa: E402

SYMBOL_SHORT = {"ES.c.0": "ES", "NQ.c.0": "NQ", "YM.c.0": "YM", "RTY.c.0": "RTY"}


# ---------------------------------------------------------------------------
# Data loading (a thin version — train_walkforward has its own)
# ---------------------------------------------------------------------------


def _horizon_min_from_key(h_key: str) -> int:
    return int(h_key.replace("h_", "").replace("m", ""))


def load_fold_phase(dataset_dir: Path, fold_id, phase: str):
    sub = dataset_dir / f"fold_{fold_id}_{phase}"
    meta = pd.read_parquet(sub / "meta.parquet")
    inputs = np.load(sub / "inputs.npy")
    labels = {}
    for h in HORIZON_KEYS:
        h_min = _horizon_min_from_key(h)
        cols = []
        for sym in SYMBOL_ORDER:
            s = SYMBOL_SHORT[sym]
            cols.append(meta[f"{s}_label_h{h_min}"].to_numpy(dtype=np.int8))
        labels[h] = np.stack(cols, axis=1)
    return inputs, labels, meta


def _flatten_features(inputs: np.ndarray, last_window: int = 60) -> np.ndarray:
    """Same flattening as baseline_lightgbm.py — keep them in sync."""
    n, lookback, n_channels = inputs.shape
    last_window = min(last_window, lookback)
    tail = inputs[:, -last_window:, :]
    out = np.concatenate(
        [inputs[:, -1, :], tail.mean(axis=1), tail.std(axis=1)],
        axis=1,
    ).astype(np.float32)
    return out


# ---------------------------------------------------------------------------
# Optuna objective per horizon
# ---------------------------------------------------------------------------


def make_objective(*, train_X, train_y_per_sym, val_X, val_y_per_sym):
    """train_X/val_X: (N, n_features). train_y_per_sym: dict[symbol_idx, (N,)] int.

    Objective: mean val ROC-AUC OvR macro across the 4 symbols.
    """
    import lightgbm as lgb
    from sklearn.metrics import roc_auc_score

    def objective(trial):
        params = {
            "objective": "multiclass",
            "num_class": 3,
            "metric": "multi_logloss",
            "verbose": -1,
            "n_jobs": -1,
            "random_state": 42,
            "n_estimators": trial.suggest_int("n_estimators", 100, 800),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
            "num_leaves": trial.suggest_int("num_leaves", 15, 200),
            "min_child_samples": trial.suggest_int("min_child_samples", 5, 100),
            "reg_alpha": trial.suggest_float("reg_alpha", 0.0, 1.0),
            "reg_lambda": trial.suggest_float("reg_lambda", 0.0, 1.0),
            "feature_fraction": trial.suggest_float("feature_fraction", 0.5, 1.0),
            "bagging_fraction": trial.suggest_float("bagging_fraction", 0.5, 1.0),
            "bagging_freq": 5,
        }
        aucs = []
        for s_idx in train_y_per_sym:
            y_tr = train_y_per_sym[s_idx]
            y_va = val_y_per_sym[s_idx]
            mask_t = (y_tr != -1) if y_tr.dtype != np.int8 else (y_tr != -1)
            mask_v = (y_va != -1) if y_va.dtype != np.int8 else (y_va != -1)
            if mask_t.sum() < 100 or mask_v.sum() < 50:
                continue
            X_tr = train_X[mask_t]
            yt = y_tr[mask_t].astype(np.int32)
            X_va = val_X[mask_v]
            yv = y_va[mask_v].astype(np.int32)

            clf = lgb.LGBMClassifier(**params)
            clf.fit(
                X_tr, yt,
                eval_set=[(X_va, yv)],
                callbacks=[lgb.early_stopping(20, verbose=False)],
            )
            proba = clf.predict_proba(X_va)
            # Align proba columns by classes_
            if proba.shape[1] != 3:
                full = np.zeros((len(yv), 3), dtype=np.float32)
                for i, c in enumerate(clf.classes_):
                    full[:, int(c)] = proba[:, i]
                proba = full
            try:
                auc = roc_auc_score(yv, proba, multi_class="ovr", average="macro")
            except ValueError:
                continue
            aucs.append(auc)

        if not aucs:
            return 0.0
        return float(np.mean(aucs))

    return objective


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    import optuna

    p = argparse.ArgumentParser()
    p.add_argument("--n-trials", type=int, default=30, help="Optuna trials per horizon")
    p.add_argument("--horizons", nargs="+", default=list(HORIZON_KEYS),
                   help="Subset of horizons to tune")
    p.add_argument("--fold-id", default="4", help="Which fold to tune on (default fold 4, biggest train)")
    p.add_argument("--dataset-dir", default=str(EXPERIMENT_DIR / "out" / "dataset"))
    p.add_argument("--out-yaml", default=str(EXPERIMENT_DIR / "config" / "tuned_lightgbm_hps.yaml"))
    p.add_argument("--last-window", type=int, default=60, help="Match baseline_lightgbm.py")
    args = p.parse_args(argv)

    dataset_dir = Path(args.dataset_dir).resolve()
    out_yaml_path = Path(args.out_yaml).resolve()
    out_yaml_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"=== tune_lightgbm starting ===", flush=True)
    print(f"  fold:    {args.fold_id}", flush=True)
    print(f"  trials:  {args.n_trials} per horizon", flush=True)
    print(f"  horizons: {args.horizons}", flush=True)

    t_load = time.time()
    train_inputs, train_labels, _ = load_fold_phase(dataset_dir, args.fold_id, "train")
    val_inputs, val_labels, _ = load_fold_phase(dataset_dir, args.fold_id, "val")
    print(f"  loaded fold {args.fold_id}: train={len(train_inputs):,}  val={len(val_inputs):,}  ({time.time()-t_load:.1f}s)", flush=True)

    t_feat = time.time()
    train_X = _flatten_features(train_inputs, last_window=args.last_window)
    val_X = _flatten_features(val_inputs, last_window=args.last_window)
    print(f"  flattened features: train_X={train_X.shape}  val_X={val_X.shape}  ({time.time()-t_feat:.1f}s)", flush=True)

    best_per_horizon: dict = {}
    total_t = time.time()

    optuna.logging.set_verbosity(optuna.logging.WARNING)

    for h_key in args.horizons:
        if h_key not in HORIZON_KEYS:
            print(f"  WARN: unknown horizon {h_key}, skipping")
            continue
        h_idx = HORIZON_KEYS.index(h_key)
        print(f"\n=== tuning {h_key} ===", flush=True)

        train_y_per_sym = {s: train_labels[h_key][:, s] for s in range(len(SYMBOL_ORDER))}
        val_y_per_sym = {s: val_labels[h_key][:, s] for s in range(len(SYMBOL_ORDER))}

        objective = make_objective(
            train_X=train_X,
            train_y_per_sym=train_y_per_sym,
            val_X=val_X,
            val_y_per_sym=val_y_per_sym,
        )

        sampler = optuna.samplers.TPESampler(seed=42)
        study = optuna.create_study(direction="maximize", sampler=sampler)
        t_h = time.time()
        study.optimize(
            objective,
            n_trials=args.n_trials,
            show_progress_bar=False,
            gc_after_trial=True,
        )
        elapsed_h = time.time() - t_h

        best = study.best_params
        best["last_window"] = args.last_window  # remember the flatten window used during search
        best_score = float(study.best_value)
        best_per_horizon[h_key] = {
            "best_params": best,
            "best_val_auc": best_score,
            "n_trials": args.n_trials,
            "tuned_on_fold": args.fold_id,
        }
        print(f"  {h_key}: best val_auc={best_score:.4f} ({elapsed_h:.1f}s, {elapsed_h / max(1, args.n_trials):.1f}s/trial)", flush=True)
        for k, v in best.items():
            print(f"    {k}: {v}")

    # Write yaml
    summary = {
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "tuned_on_fold": args.fold_id,
        "n_trials_per_horizon": args.n_trials,
        "feature_flatten_window": args.last_window,
        "horizons": best_per_horizon,
    }
    with out_yaml_path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(summary, fh, sort_keys=False, default_flow_style=False)
    print(f"\nWrote {out_yaml_path.relative_to(EXPERIMENT_DIR)}")

    # JSON sidecar for easy diff
    out_json_path = out_yaml_path.with_suffix(".json")
    out_json_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print(f"Wrote {out_json_path.relative_to(EXPERIMENT_DIR)}")

    total_elapsed = time.time() - total_t
    print(f"\n=== tune_lightgbm done in {total_elapsed:.1f}s ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
