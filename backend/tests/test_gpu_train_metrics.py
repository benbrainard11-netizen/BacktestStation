"""Tests for the per-fold metrics aggregator."""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("sklearn")  # AUC needs scikit-learn

from scripts.ml.gpu_train_metrics import compute_fold_metrics


def _record(y_test, p_test, *, y_train=None):
    if y_train is None:
        y_train = np.array([0, 1, 0, 1] * 25)
    return compute_fold_metrics(
        y_train=y_train,
        y_val=np.array([], dtype=int),
        y_test=np.asarray(y_test),
        p_train=np.zeros(len(y_train)),
        p_val=np.array([]),
        p_test=np.asarray(p_test),
        best_iteration=0,
    )


def test_perfect_predictions_auc_one_and_top_bucket_lift_positive():
    y_test = np.array([0, 0, 0, 1, 1, 1, 1, 1, 1, 1])
    p_test = np.array([0.0, 0.1, 0.2, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 1.0])
    m = _record(y_test, p_test)
    assert m.auc_test == pytest.approx(1.0)
    assert m.base_rate_test == pytest.approx(0.7)
    assert m.top_bucket_n >= 1
    assert m.top_bucket_rate >= m.base_rate_test
    assert m.top_bucket_lift_vs_base >= 0


def test_random_predictions_auc_near_half():
    rng = np.random.default_rng(0)
    n = 2000
    y_test = rng.integers(0, 2, n)
    p_test = rng.random(n)
    m = _record(y_test, p_test, y_train=np.array([0, 1] * 500))
    assert m.auc_test is not None
    assert 0.4 < m.auc_test < 0.6


def test_majority_accuracy_uses_train_distribution():
    y_train = np.zeros(100, dtype=int)
    y_train[:10] = 1  # majority class is 0
    y_test = np.array([0, 0, 0, 1])
    p_test = np.array([0.1, 0.2, 0.3, 0.9])
    m = compute_fold_metrics(
        y_train=y_train,
        y_val=np.array([], dtype=int),
        y_test=y_test,
        p_train=np.zeros(len(y_train)),
        p_val=np.array([]),
        p_test=p_test,
        best_iteration=0,
    )
    # 3 of 4 test rows are 0, majority class is 0 → accuracy 0.75.
    assert m.majority_accuracy_test == pytest.approx(0.75)


def test_top_bucket_size_at_least_one_for_nonempty_test():
    y_test = np.array([0, 1, 0, 1])
    p_test = np.array([0.1, 0.2, 0.3, 0.4])
    m = _record(y_test, p_test)
    assert m.top_bucket_n >= 1


def test_empty_test_yields_zeroed_top_bucket():
    m = compute_fold_metrics(
        y_train=np.array([0, 1]),
        y_val=np.array([], dtype=int),
        y_test=np.array([], dtype=int),
        p_train=np.array([0.4, 0.6]),
        p_val=np.array([]),
        p_test=np.array([]),
        best_iteration=0,
    )
    assert m.top_bucket_n == 0
    assert m.top_bucket_rate == 0.0
    assert m.auc_test is None
