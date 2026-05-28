"""LightGBMBaselineForecaster — per (symbol, horizon) 3-class classifier.

Per (symbol, horizon), train one LightGBM 3-way classifier on a flattened
feature vector derived from the multivariate lookback tensor. Total models
per fold: n_symbols × n_horizons = 4 × 5 = 20.

This is the strong baseline. If TTM (v0 primary) can't beat this, TSFM is
the wrong tool for this dataset and we ship LightGBM.

Feature extraction (per anchor row, returns a flat vector of ~96 features):
  For each of the n_channels channels:
    - last value (1)
    - mean over last 60 (1)
    - std over last 60 (1)

That's 32 channels × 3 = 96 features. Plus we add a few cross-channel
interactions if helpful (held to be added later).

Implements the Forecaster ABC.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

import numpy as np

from forecaster import (
    CLASS_CODES,
    HORIZON_KEYS,
    SYMBOL_ORDER,
    ForecastBatch,
    Forecaster,
)

# Lightgbm is heavy; defer import until fit/load.


def _flatten_features(inputs: np.ndarray, last_window: int = 60) -> np.ndarray:
    """Reduce (N, lookback, n_channels) → (N, n_channels * 3) feature matrix.

    Per channel: [last_value, mean_last_W, std_last_W].
    """
    if inputs.ndim != 3:
        raise ValueError(f"inputs.ndim={inputs.ndim}, expected 3")
    n, lookback, n_channels = inputs.shape
    if last_window > lookback:
        last_window = lookback

    tail = inputs[:, -last_window:, :]  # (N, W, C)
    feat_last = inputs[:, -1, :]                  # (N, C)
    feat_mean = tail.mean(axis=1)                 # (N, C)
    feat_std = tail.std(axis=1)                   # (N, C)
    out = np.concatenate([feat_last, feat_mean, feat_std], axis=1)
    return out.astype(np.float32)


class LightGBMBaselineForecaster(Forecaster):
    """One LightGBM 3-class classifier per (symbol, horizon).

    Per-horizon hyperparameter overrides can be supplied via the
    `tuned_hps_by_horizon` dict (keyed by HORIZON_KEYS). When present, the
    per-horizon dict replaces the constructor defaults for that horizon.
    Schema matches tune_lightgbm.py's output.
    """

    def __init__(
        self,
        *,
        last_window: int = 60,
        n_estimators: int = 200,
        learning_rate: float = 0.05,
        num_leaves: int = 31,
        min_child_samples: int = 20,
        reg_alpha: float = 0.0,
        reg_lambda: float = 0.0,
        feature_fraction: float = 1.0,
        bagging_fraction: float = 1.0,
        bagging_freq: int = 0,
        device: str = "cpu",
        random_state: int = 42,
        tuned_hps_by_horizon: dict | None = None,
    ) -> None:
        self.last_window = last_window
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.num_leaves = num_leaves
        self.min_child_samples = min_child_samples
        self.reg_alpha = reg_alpha
        self.reg_lambda = reg_lambda
        self.feature_fraction = feature_fraction
        self.bagging_fraction = bagging_fraction
        self.bagging_freq = bagging_freq
        self.device = device
        self.random_state = random_state
        self.tuned_hps_by_horizon = tuned_hps_by_horizon or {}
        # _models[horizon][symbol_idx] = trained model
        self._models: dict[str, list] = {}

    def _params_for_horizon(self, h_key: str) -> dict:
        """Return LightGBM kwargs for one horizon, applying tuned overrides if present."""
        base = {
            "objective": "multiclass",
            "num_class": len(CLASS_CODES),
            "n_estimators": self.n_estimators,
            "learning_rate": self.learning_rate,
            "num_leaves": self.num_leaves,
            "min_child_samples": self.min_child_samples,
            "reg_alpha": self.reg_alpha,
            "reg_lambda": self.reg_lambda,
            "feature_fraction": self.feature_fraction,
            "bagging_fraction": self.bagging_fraction,
            "bagging_freq": self.bagging_freq,
            "device": self.device,
            "random_state": self.random_state,
            "n_jobs": -1,
            "verbose": -1,
        }
        tuned = self.tuned_hps_by_horizon.get(h_key)
        if tuned and isinstance(tuned, dict):
            override = tuned.get("best_params", tuned)  # accept either flat or nested
            for k, v in override.items():
                if k == "last_window":
                    continue
                base[k] = v
        return base

    @property
    def name(self) -> str:
        return f"lgbm_baseline_v0_lw{self.last_window}"

    def fit(
        self,
        *,
        train_inputs: np.ndarray,
        train_labels: Mapping[str, np.ndarray],
        val_inputs: np.ndarray | None = None,
        val_labels: Mapping[str, np.ndarray] | None = None,
        train_ts: np.ndarray | None = None,
        val_ts: np.ndarray | None = None,
        **kwargs,
    ) -> None:
        import lightgbm as lgb

        X_train = _flatten_features(train_inputs, last_window=self.last_window)
        X_val = (
            _flatten_features(val_inputs, last_window=self.last_window)
            if val_inputs is not None
            else None
        )

        n_classes = len(CLASS_CODES)
        n_symbols = len(SYMBOL_ORDER)

        self._models = {h: [None] * n_symbols for h in HORIZON_KEYS}

        for h in HORIZON_KEYS:
            if h not in train_labels:
                raise ValueError(f"missing horizon labels for {h}")
            y_train_all = train_labels[h]
            y_val_all = val_labels[h] if val_labels is not None and h in val_labels else None
            if y_train_all.shape[1] != n_symbols:
                raise ValueError(
                    f"train_labels[{h}].shape={y_train_all.shape}, expected (N, {n_symbols})"
                )

            for s in range(n_symbols):
                y_train = y_train_all[:, s]
                mask_t = ~np.isnan(y_train) if np.issubdtype(y_train.dtype, np.floating) else np.ones_like(y_train, dtype=bool)
                if mask_t.sum() == 0:
                    print(f"  WARN: {h} {SYMBOL_ORDER[s]} has no labels; skipping")
                    continue
                y_train = y_train[mask_t].astype(np.int32)
                X_train_s = X_train[mask_t]

                eval_set = None
                eval_names = None
                if X_val is not None and y_val_all is not None:
                    y_val = y_val_all[:, s]
                    mask_v = ~np.isnan(y_val) if np.issubdtype(y_val.dtype, np.floating) else np.ones_like(y_val, dtype=bool)
                    if mask_v.sum() > 0:
                        eval_set = [(X_val[mask_v], y_val[mask_v].astype(np.int32))]
                        eval_names = ["val"]

                params = self._params_for_horizon(h)
                clf = lgb.LGBMClassifier(**params)
                clf.fit(
                    X_train_s, y_train,
                    eval_set=eval_set,
                    eval_names=eval_names,
                    callbacks=[lgb.early_stopping(20, verbose=False)] if eval_set else None,
                )
                self._models[h][s] = clf

    def predict_proba(self, inputs: np.ndarray, ts: np.ndarray) -> ForecastBatch:
        if not self._models:
            raise RuntimeError("LightGBMBaselineForecaster.predict_proba before fit()")
        X = _flatten_features(inputs, last_window=self.last_window)
        n = X.shape[0]
        n_symbols = len(SYMBOL_ORDER)
        n_classes = len(CLASS_CODES)

        proba: dict[str, np.ndarray] = {}
        for h in HORIZON_KEYS:
            out = np.zeros((n, n_symbols, n_classes), dtype=np.float32)
            for s in range(n_symbols):
                model = self._models[h][s]
                if model is None:
                    # No trained model → uniform
                    out[:, s, :] = 1.0 / n_classes
                else:
                    p = model.predict_proba(X)  # (n, n_classes)
                    # Make sure shape lines up if model only saw some classes
                    if p.shape[1] != n_classes:
                        full = np.zeros((n, n_classes), dtype=np.float32)
                        for i, c in enumerate(model.classes_):
                            full[:, int(c)] = p[:, i]
                        out[:, s, :] = full
                    else:
                        out[:, s, :] = p
            proba[h] = out

        return ForecastBatch(
            horizons=HORIZON_KEYS,
            symbols=SYMBOL_ORDER,
            proba=proba,
            ts=ts,
            metadata={"model_name": self.name, "last_window": self.last_window},
        )

    def save(self, path: Path) -> None:
        import joblib

        if not self._models:
            raise RuntimeError("Cannot save before fit()")
        path.mkdir(parents=True, exist_ok=True)
        meta = {
            "last_window": self.last_window,
            "n_estimators": self.n_estimators,
            "learning_rate": self.learning_rate,
            "num_leaves": self.num_leaves,
            "device": self.device,
            "random_state": self.random_state,
        }
        (path / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        for h, models in self._models.items():
            for s, m in enumerate(models):
                if m is None:
                    continue
                joblib.dump(m, path / f"model_{h}_{SYMBOL_ORDER[s]}.joblib")

    @classmethod
    def load(cls, path: Path) -> "LightGBMBaselineForecaster":
        import joblib

        meta = json.loads((path / "meta.json").read_text(encoding="utf-8"))
        obj = cls(**meta)
        obj._models = {h: [None] * len(SYMBOL_ORDER) for h in HORIZON_KEYS}
        for h in HORIZON_KEYS:
            for s, sym in enumerate(SYMBOL_ORDER):
                p = path / f"model_{h}_{sym}.joblib"
                if p.exists():
                    obj._models[h][s] = joblib.load(p)
        return obj


def main() -> int:
    """Self-test on synthetic data."""
    rng = np.random.default_rng(42)
    n_train, n_val = 800, 200
    n_symbols = len(SYMBOL_ORDER)
    n_channels = 32
    lookback = 120  # smaller for self-test speed

    train_inputs = rng.standard_normal((n_train, lookback, n_channels)).astype(np.float32)
    val_inputs = rng.standard_normal((n_val, lookback, n_channels)).astype(np.float32)
    # Inject a weak signal: class depends on last value of channel 0
    def _make_labels(inputs):
        last_ch0 = inputs[:, -1, 0]
        labels = {}
        for h in HORIZON_KEYS:
            y = np.zeros((inputs.shape[0], n_symbols), dtype=np.int64)
            for s in range(n_symbols):
                shift = (s - n_symbols // 2) * 0.1
                y[:, s] = np.where(last_ch0 + shift > 0.3, 1, np.where(last_ch0 + shift < -0.3, 2, 0))
            labels[h] = y
        return labels

    train_labels = _make_labels(train_inputs)
    val_labels = _make_labels(val_inputs)
    train_ts = np.arange(n_train, dtype=np.int64)
    val_ts = np.arange(n_val, dtype=np.int64) + n_train

    model = LightGBMBaselineForecaster(n_estimators=50, last_window=60)
    model.fit(
        train_inputs=train_inputs,
        train_labels=train_labels,
        val_inputs=val_inputs,
        val_labels=val_labels,
        train_ts=train_ts,
        val_ts=val_ts,
    )
    out = model.predict_proba(val_inputs, val_ts)
    print(f"name: {model.name}")
    for h in HORIZON_KEYS:
        dist = out.proba[h][0, 0]
        print(f"  {h}: first-row first-sym dist = {dist}, sum = {dist.sum():.3f}")

    # Quick accuracy on val
    for h in HORIZON_KEYS:
        preds = np.argmax(out.proba[h], axis=2)  # (N, n_symbols)
        acc = (preds == val_labels[h]).mean()
        print(f"  {h}: val accuracy = {acc:.3f}  (should be > 0.33 since signal injected)")

    print("self-test OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
