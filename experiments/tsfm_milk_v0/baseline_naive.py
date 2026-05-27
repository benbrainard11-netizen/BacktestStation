"""NaiveBaseline — predicts marginal class frequency from training data.

Sanity floor. If a real model can't beat this consistently, it's broken.

Memorize per (horizon, symbol) class fractions on training data; broadcast
those fractions as predicted probabilities for every prediction request.

Implements the Forecaster ABC from forecaster.py.
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


class NaiveBaseline(Forecaster):
    """Marginal class frequency baseline.

    fit() computes empirical class fractions per (horizon, symbol) on train data.
    predict_proba() returns those fractions broadcast over all N input rows.
    """

    def __init__(self) -> None:
        # _freqs[horizon_key] is a (n_symbols, n_classes) array of probabilities.
        self._freqs: dict[str, np.ndarray] | None = None

    @property
    def name(self) -> str:
        return "naive_baseline_v0"

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
        n_classes = len(CLASS_CODES)
        n_symbols = len(SYMBOL_ORDER)

        freqs: dict[str, np.ndarray] = {}
        for h in HORIZON_KEYS:
            if h not in train_labels:
                raise ValueError(f"NaiveBaseline.fit missing horizon labels for {h}")
            arr = train_labels[h]
            if arr.ndim != 2 or arr.shape[1] != n_symbols:
                raise ValueError(
                    f"train_labels[{h}].shape={arr.shape}, expected (N, {n_symbols})"
                )

            counts = np.zeros((n_symbols, n_classes), dtype=np.float64)
            for s in range(n_symbols):
                col = arr[:, s]
                valid = col[~np.isnan(col)] if np.issubdtype(col.dtype, np.floating) else col
                if len(valid) == 0:
                    # No data → uniform distribution
                    counts[s] = 1.0 / n_classes
                    continue
                for c in range(n_classes):
                    counts[s, c] = float((valid == c).sum())
                total = counts[s].sum()
                if total <= 0:
                    counts[s] = 1.0 / n_classes
                else:
                    counts[s] = counts[s] / total
            freqs[h] = counts

        self._freqs = freqs

    def predict_proba(self, inputs: np.ndarray, ts: np.ndarray) -> ForecastBatch:
        if self._freqs is None:
            raise RuntimeError("NaiveBaseline.predict_proba called before fit()")
        n = inputs.shape[0]
        n_symbols = len(SYMBOL_ORDER)
        n_classes = len(CLASS_CODES)
        proba: dict[str, np.ndarray] = {}
        for h in HORIZON_KEYS:
            # Broadcast (n_symbols, n_classes) → (n, n_symbols, n_classes)
            proba[h] = np.tile(self._freqs[h][None, :, :], (n, 1, 1)).astype(np.float32)
        return ForecastBatch(
            horizons=HORIZON_KEYS,
            symbols=SYMBOL_ORDER,
            proba=proba,
            ts=ts,
            metadata={"model_name": self.name},
        )

    def save(self, path: Path) -> None:
        if self._freqs is None:
            raise RuntimeError("Cannot save NaiveBaseline before fit()")
        path.mkdir(parents=True, exist_ok=True)
        payload = {h: arr.tolist() for h, arr in self._freqs.items()}
        (path / "freqs.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "NaiveBaseline":
        obj = cls()
        payload = json.loads((path / "freqs.json").read_text(encoding="utf-8"))
        obj._freqs = {h: np.array(v, dtype=np.float64) for h, v in payload.items()}
        return obj


def main() -> int:
    """Self-test on synthetic data."""
    n = 1000
    n_symbols = len(SYMBOL_ORDER)
    n_channels = 32
    lookback = 240

    rng = np.random.default_rng(42)
    train_inputs = rng.standard_normal((n, lookback, n_channels)).astype(np.float32)
    # Bias labels toward class 0 for testing
    train_labels = {
        h: rng.choice([0, 1, 2], size=(n, n_symbols), p=[0.5, 0.25, 0.25]).astype(np.int64)
        for h in HORIZON_KEYS
    }
    train_ts = np.arange(n, dtype=np.int64)

    model = NaiveBaseline()
    model.fit(train_inputs=train_inputs, train_labels=train_labels, train_ts=train_ts)

    # Predict on a small batch
    test_inputs = rng.standard_normal((50, lookback, n_channels)).astype(np.float32)
    test_ts = np.arange(50, dtype=np.int64)
    out = model.predict_proba(test_inputs, test_ts)

    print(f"name: {model.name}")
    for h in HORIZON_KEYS:
        # First row's first symbol's distribution
        dist = out.proba[h][0, 0]
        print(f"  {h}: first-row first-sym dist = {dist}, sum = {dist.sum():.3f}")
    print("self-test OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
