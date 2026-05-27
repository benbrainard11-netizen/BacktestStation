"""Forecaster abstract base class — the model-swap interface.

Pipeline stages 1-4 (data, labels, splits, embargo) and 6-7 (eval, integration)
are model-agnostic. Only stage 5 (training) varies per Forecaster implementation.

Swap models by implementing this ABC. See PLAN.md §4.

Implementations expected in v0:
  - baseline_naive.NaiveBaseline             — marginal class freq
  - baseline_lightgbm.LightGBMBaselineForecaster — per (symbol, horizon) head
  - ttm_forecaster.TTMForecaster             — v0 primary (IBM Granite TTM)
  - moirai_forecaster.MoiraiForecaster       — v0.5 challenger
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

import numpy as np


HORIZON_KEYS: tuple[str, ...] = ("h_15m", "h_30m", "h_60m", "h_90m", "h_240m")
SYMBOL_ORDER: tuple[str, ...] = ("ES.c.0", "NQ.c.0", "YM.c.0", "RTY.c.0")
CLASS_CODES: dict[str, int] = {"flat": 0, "up": 1, "down": 2}


@dataclass(frozen=True)
class ForecastBatch:
    """One forward-pass output for N anchor rows.

    proba[horizon_key] has shape (N, n_symbols, n_classes) = (N, 4, 3).

    n_classes is fixed at 3: [flat, up, down] in the order of CLASS_CODES values.
    """

    horizons: tuple[str, ...]
    symbols: tuple[str, ...]
    proba: dict[str, np.ndarray]  # {"h_15m": (N, 4, 3), "h_30m": (N, 4, 3), ...}
    ts: np.ndarray                # shape (N,) — anchor timestamps (np.datetime64[ns])
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        for h in self.horizons:
            if h not in self.proba:
                raise ValueError(f"missing proba for horizon {h}")
            arr = self.proba[h]
            if arr.ndim != 3 or arr.shape[1:] != (len(self.symbols), 3):
                raise ValueError(
                    f"proba[{h}].shape = {arr.shape}; expected (N, {len(self.symbols)}, 3)"
                )


class Forecaster(ABC):
    """Pluggable forecaster interface. Subclass to add a model.

    Contract:
      - fit() trains on one fold's (train, val) data.
      - predict_proba() returns calibrated 3-class probabilities at every horizon.
      - save() / load() roundtrip a trained model to/from disk.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Short identifier, e.g., "ttm_v0", "lgbm_baseline"."""
        ...

    @abstractmethod
    def fit(
        self,
        *,
        train_inputs: np.ndarray,           # (N_train, lookback, n_channels)
        train_labels: Mapping[str, np.ndarray],  # {h_key: (N_train, n_symbols)} int class codes
        val_inputs: np.ndarray,             # (N_val, lookback, n_channels)
        val_labels: Mapping[str, np.ndarray],
        train_ts: np.ndarray,
        val_ts: np.ndarray,
        **kwargs,
    ) -> None:
        """Train on this fold's train+val data. May early-stop on val."""
        ...

    @abstractmethod
    def predict_proba(
        self,
        inputs: np.ndarray,                 # (N, lookback, n_channels)
        ts: np.ndarray,                     # (N,) anchor timestamps
    ) -> ForecastBatch:
        """Return calibrated 3-class probabilities at every horizon."""
        ...

    @abstractmethod
    def save(self, path: Path) -> None:
        """Persist trained state to a directory."""
        ...

    @classmethod
    @abstractmethod
    def load(cls, path: Path) -> "Forecaster":
        """Load a previously-saved Forecaster from disk."""
        ...
