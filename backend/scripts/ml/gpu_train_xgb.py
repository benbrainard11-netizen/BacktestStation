"""Thin XGBoost wrapper for the GPU runner.

Encapsulates:
- device resolution (`cuda` if available, else `cpu`)
- DMatrix / QuantileDMatrix construction
- training with early stopping
- prediction + feature-importance extraction

XGBoost is imported lazily so the rest of the runner — schema-safe
loader, fold builder, tests — runs in environments without it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from .gpu_train_constants import (
    COLSAMPLE_BYTREE,
    DEVICE_AUTO,
    DEVICE_CPU,
    DEVICE_CUDA,
    EARLY_STOPPING_ROUNDS,
    LEARNING_RATE,
    MAX_DEPTH,
    MIN_CHILD_WEIGHT,
    NUM_BOOST_ROUND,
    SEED,
    SUBSAMPLE,
    TREE_METHOD,
)


@dataclass(frozen=True)
class DeviceInfo:
    """What device the runner actually trained on."""

    requested: str
    resolved: str
    xgboost_version: str
    cuda_available: bool


def resolve_device(requested: str) -> DeviceInfo:
    """Pick `cuda` if CUDA-enabled XGBoost is importable, else `cpu`.

    `requested` may be `auto`, `cuda`, or `cpu`. `auto` honors CUDA
    availability; explicit `cuda` raises if CUDA isn't available so a
    silent CPU fallback can never hide a misconfiguration.
    """
    import xgboost as xgb

    build = xgb.build_info() if hasattr(xgb, "build_info") else {}
    cuda_ok = bool(build.get("USE_CUDA"))
    version = getattr(xgb, "__version__", "unknown")

    if requested == DEVICE_AUTO:
        resolved = DEVICE_CUDA if cuda_ok else DEVICE_CPU
    elif requested == DEVICE_CUDA:
        if not cuda_ok:
            raise RuntimeError(
                "xgboost reports USE_CUDA=False; rebuild with CUDA or "
                f"pass --device {DEVICE_CPU}"
            )
        resolved = DEVICE_CUDA
    elif requested == DEVICE_CPU:
        resolved = DEVICE_CPU
    else:
        raise ValueError(
            f"unknown device {requested!r}; expected one of "
            f"{DEVICE_AUTO}/{DEVICE_CUDA}/{DEVICE_CPU}"
        )

    return DeviceInfo(
        requested=requested,
        resolved=resolved,
        xgboost_version=version,
        cuda_available=cuda_ok,
    )


def default_params(device: str) -> dict[str, Any]:
    """Hyperparameters mirroring the LightGBM baseline + device flag."""
    return {
        "objective": "binary:logistic",
        "eval_metric": "logloss",
        "tree_method": TREE_METHOD,
        "device": device,
        "learning_rate": LEARNING_RATE,
        "max_depth": MAX_DEPTH,
        "min_child_weight": MIN_CHILD_WEIGHT,
        "subsample": SUBSAMPLE,
        "colsample_bytree": COLSAMPLE_BYTREE,
        "seed": SEED,
        "verbosity": 0,
    }


@dataclass
class FoldOutputs:
    """What `train_one_fold` returns to the runner."""

    p_train: np.ndarray
    p_val: np.ndarray
    p_test: np.ndarray
    best_iteration: int
    feature_importance: dict[str, float]


def _build_dmatrix(x: np.ndarray, y: np.ndarray | None, *, feature_names: list[str]):
    """Use `QuantileDMatrix` for GPU efficiency; falls back to DMatrix.

    `QuantileDMatrix` works for both CPU and GPU `hist` and uses less
    memory than a plain `DMatrix`. Imported lazily so the rest of the
    module remains import-safe without xgboost installed.
    """
    import xgboost as xgb

    cls = getattr(xgb, "QuantileDMatrix", xgb.DMatrix)
    return cls(x, label=y, feature_names=feature_names)


def train_one_fold(
    *,
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_val: np.ndarray | None,
    y_val: np.ndarray | None,
    x_test: np.ndarray,
    feature_names: list[str],
    device: str,
    num_boost_round: int = NUM_BOOST_ROUND,
    early_stopping_rounds: int = EARLY_STOPPING_ROUNDS,
) -> FoldOutputs:
    """Train one fold and return per-split predictions + importances."""
    import xgboost as xgb

    dtrain = _build_dmatrix(x_train, y_train, feature_names=feature_names)
    evals: list[tuple[Any, str]] = [(dtrain, "train")]
    dval = None
    use_es = False
    if x_val is not None and y_val is not None and len(np.unique(y_val)) > 1:
        dval = _build_dmatrix(x_val, y_val, feature_names=feature_names)
        evals.append((dval, "val"))
        use_es = True

    params = default_params(device)
    booster = xgb.train(
        params,
        dtrain,
        num_boost_round=num_boost_round,
        evals=evals,
        early_stopping_rounds=early_stopping_rounds if use_es else None,
        verbose_eval=False,
    )

    best_it = int(getattr(booster, "best_iteration", num_boost_round - 1))
    iteration_range = (0, best_it + 1)

    p_train = booster.predict(dtrain, iteration_range=iteration_range)
    p_val = (
        booster.predict(dval, iteration_range=iteration_range)
        if dval is not None
        else np.zeros(0, dtype=np.float64)
    )
    dtest = _build_dmatrix(x_test, None, feature_names=feature_names)
    p_test = booster.predict(dtest, iteration_range=iteration_range)

    importance = booster.get_score(importance_type="gain")

    return FoldOutputs(
        p_train=np.asarray(p_train, dtype=np.float64),
        p_val=np.asarray(p_val, dtype=np.float64),
        p_test=np.asarray(p_test, dtype=np.float64),
        best_iteration=best_it,
        feature_importance=dict(importance),
    )
