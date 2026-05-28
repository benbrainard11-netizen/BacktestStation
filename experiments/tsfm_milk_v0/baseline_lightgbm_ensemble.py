"""LightGBMEnsembleForecaster — average N LightGBM models with different seeds.

Variance averaging is the cheapest reliable accuracy gain in ML. For each
(symbol, horizon), train N LightGBM classifiers with different random_state
and average their predicted probabilities.

Uses the SAME hyperparameters per horizon as `lightgbm_tuned` (loaded from
config/tuned_lightgbm_hps.yaml when present). The only thing that varies
across ensemble members is the random seed, which propagates through:
  - bagging fraction sampling
  - feature fraction sampling
  - LightGBM's internal histogram tie-breaking

Expected lift on top of tuned LightGBM: +5-15% on sum_net_R, +0.5-1pp AUC.
Reliable. Marginal but cheap.

Implements the Forecaster ABC.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

import numpy as np

from forecaster import CLASS_CODES, HORIZON_KEYS, SYMBOL_ORDER, ForecastBatch, Forecaster


class LightGBMEnsembleForecaster(Forecaster):
    """N seeded LightGBM ensemble. Wraps N LightGBMBaselineForecaster instances."""

    def __init__(
        self,
        *,
        n_seeds: int = 5,
        seeds: list[int] | None = None,
        last_window: int = 60,
        tuned_hps_by_horizon: dict | None = None,
    ) -> None:
        self.n_seeds = n_seeds
        self.seeds = seeds or [42 + i * 1000 for i in range(n_seeds)]
        if len(self.seeds) != self.n_seeds:
            raise ValueError(f"len(seeds)={len(self.seeds)} != n_seeds={self.n_seeds}")
        self.last_window = last_window
        self.tuned_hps_by_horizon = tuned_hps_by_horizon or {}
        self._members: list = []

    @property
    def name(self) -> str:
        return f"lightgbm_ens_n{self.n_seeds}"

    def _make_member(self, seed: int):
        # Local import to keep module-level import cheap
        from baseline_lightgbm import LightGBMBaselineForecaster
        return LightGBMBaselineForecaster(
            last_window=self.last_window,
            tuned_hps_by_horizon=self.tuned_hps_by_horizon,
            random_state=seed,
        )

    def fit(
        self,
        *,
        train_inputs: np.ndarray,
        train_labels: Mapping[str, np.ndarray],
        val_inputs: np.ndarray,
        val_labels: Mapping[str, np.ndarray],
        train_ts: np.ndarray | None = None,
        val_ts: np.ndarray | None = None,
        **kwargs,
    ) -> None:
        self._members = []
        for i, seed in enumerate(self.seeds):
            print(f"      [ens member {i + 1}/{self.n_seeds}] seed={seed}", flush=True)
            member = self._make_member(seed)
            member.fit(
                train_inputs=train_inputs,
                train_labels=train_labels,
                val_inputs=val_inputs,
                val_labels=val_labels,
                train_ts=train_ts,
                val_ts=val_ts,
            )
            self._members.append(member)

    def predict_proba(self, inputs: np.ndarray, ts: np.ndarray) -> ForecastBatch:
        if not self._members:
            raise RuntimeError("LightGBMEnsembleForecaster.predict_proba before fit()")
        n = inputs.shape[0]
        n_symbols = len(SYMBOL_ORDER)
        n_classes = len(CLASS_CODES)

        # Accumulate average across members
        avg_proba: dict[str, np.ndarray] = {
            h: np.zeros((n, n_symbols, n_classes), dtype=np.float64) for h in HORIZON_KEYS
        }
        for member in self._members:
            member_batch = member.predict_proba(inputs, ts)
            for h in HORIZON_KEYS:
                avg_proba[h] += member_batch.proba[h]

        # Normalize and cast back to float32
        for h in HORIZON_KEYS:
            avg_proba[h] = (avg_proba[h] / float(self.n_seeds)).astype(np.float32)

        return ForecastBatch(
            horizons=HORIZON_KEYS,
            symbols=SYMBOL_ORDER,
            proba=avg_proba,
            ts=ts,
            metadata={"model_name": self.name, "n_seeds": self.n_seeds, "seeds": self.seeds},
        )

    def save(self, path: Path) -> None:
        if not self._members:
            raise RuntimeError("Cannot save before fit()")
        path.mkdir(parents=True, exist_ok=True)
        meta = {
            "n_seeds": self.n_seeds,
            "seeds": self.seeds,
            "last_window": self.last_window,
            "tuned_hps_by_horizon": self.tuned_hps_by_horizon,
        }
        (path / "meta.json").write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8")
        for i, member in enumerate(self._members):
            member.save(path / f"member_{i}_seed{self.seeds[i]}")

    @classmethod
    def load(cls, path: Path) -> "LightGBMEnsembleForecaster":
        from baseline_lightgbm import LightGBMBaselineForecaster

        meta = json.loads((path / "meta.json").read_text(encoding="utf-8"))
        obj = cls(
            n_seeds=meta["n_seeds"],
            seeds=meta["seeds"],
            last_window=meta["last_window"],
            tuned_hps_by_horizon=meta.get("tuned_hps_by_horizon", {}),
        )
        obj._members = []
        for i, seed in enumerate(obj.seeds):
            sub = path / f"member_{i}_seed{seed}"
            obj._members.append(LightGBMBaselineForecaster.load(sub))
        return obj
