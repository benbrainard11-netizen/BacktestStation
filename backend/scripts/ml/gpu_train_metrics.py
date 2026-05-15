"""Per-fold metrics for the GPU runner.

Kept separate from the runner orchestration so the metrics are easy to
unit-test and the runner stays under the 300-line floor.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .gpu_train_constants import TOP_BUCKET_PCT


@dataclass
class FoldMetrics:
    """Numeric summary for one fold."""

    n_train: int
    n_val: int
    n_test: int
    pos_train: int
    pos_test: int
    base_rate_test: float
    auc_train: float | None
    auc_val: float | None
    auc_test: float | None
    accuracy_test: float
    majority_accuracy_test: float
    top_bucket_n: int
    top_bucket_rate: float
    top_bucket_lift_vs_base: float
    best_iteration: int


def _safe_auc(y_true: np.ndarray, proba: np.ndarray) -> float | None:
    if len(y_true) == 0 or len(np.unique(y_true)) < 2:
        return None
    from sklearn.metrics import roc_auc_score

    return float(roc_auc_score(y_true, proba))


def _top_bucket_indices(proba: np.ndarray, pct: float) -> np.ndarray:
    if len(proba) == 0:
        return np.zeros(0, dtype=bool)
    top_n = max(1, int(np.ceil(len(proba) * pct)))
    top_idx = np.argsort(-proba)[:top_n]
    out = np.zeros(len(proba), dtype=bool)
    out[top_idx] = True
    return out


def compute_fold_metrics(
    *,
    y_train: np.ndarray,
    y_val: np.ndarray,
    y_test: np.ndarray,
    p_train: np.ndarray,
    p_val: np.ndarray,
    p_test: np.ndarray,
    best_iteration: int,
    top_pct: float = TOP_BUCKET_PCT,
) -> FoldMetrics:
    """Bundle all per-fold metrics into one record for the summary CSV."""
    pred_test = (p_test >= 0.5).astype(int)
    base_rate = float(y_test.mean()) if len(y_test) else 0.0
    majority = int(np.round(y_train.mean())) if len(y_train) else 0
    majority_acc = float((y_test == majority).mean()) if len(y_test) else 0.0
    accuracy = float((pred_test == y_test).mean()) if len(y_test) else 0.0

    top_mask = _top_bucket_indices(p_test, top_pct)
    top_n = int(top_mask.sum())
    if top_n > 0:
        top_rate = float(y_test[top_mask].mean())
    else:
        top_rate = 0.0
    lift = top_rate - base_rate

    return FoldMetrics(
        n_train=int(len(y_train)),
        n_val=int(len(y_val)),
        n_test=int(len(y_test)),
        pos_train=int(y_train.sum()),
        pos_test=int(y_test.sum()),
        base_rate_test=base_rate,
        auc_train=_safe_auc(y_train, p_train),
        auc_val=_safe_auc(y_val, p_val) if len(y_val) else None,
        auc_test=_safe_auc(y_test, p_test),
        accuracy_test=accuracy,
        majority_accuracy_test=majority_acc,
        top_bucket_n=top_n,
        top_bucket_rate=top_rate,
        top_bucket_lift_vs_base=lift,
        best_iteration=int(best_iteration),
    )
