"""Tests for the walk-forward fold planner.

Locks in the (train ≤ test_year - 2, val = test_year - 1, test =
test_year) semantics required by Prompt B and matches the existing
CPU LightGBM walk-forward boundaries.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts.ml.gpu_train_constants import (
    MIN_TEST_CLASS,
    MIN_TEST_ROWS,
    MIN_TRAIN_CLASS,
    MIN_TRAIN_ROWS,
    YEAR_COLUMN,
)
from scripts.ml.gpu_train_walk_forward import (
    build_fold,
    check_fold,
    extract_years,
)


def test_build_fold_partitions_years_correctly():
    years = np.array([2018, 2019, 2020, 2021, 2022, 2023])
    fold = build_fold(years, test_year=2022)
    assert fold.test_year == 2022
    assert fold.val_year == 2021
    assert fold.train_end_year == 2020
    assert list(fold.train_mask) == [True, True, True, False, False, False]
    assert list(fold.val_mask) == [False, False, False, True, False, False]
    assert list(fold.test_mask) == [False, False, False, False, True, False]


def test_build_fold_train_end_offset_two_val_offset_one():
    """Regression: matches snapshot_walk_forward.py:_run_fold offsets."""
    years = np.arange(2015, 2026)
    fold = build_fold(years, test_year=2025)
    assert fold.train_end_year == 2023
    assert fold.val_year == 2024


def test_check_fold_skips_when_train_below_minimum():
    years = np.array([2020] * 10 + [2021] * 10 + [2022] * 10)
    y = np.array([0, 1] * 15)  # balanced, but tiny
    fold = build_fold(years, test_year=2022)
    feas = check_fold(fold, y)
    assert not feas.ok
    assert feas.reason == "skip_small_split"


def test_check_fold_skips_when_train_class_imbalanced():
    rng = np.random.default_rng(0)
    years = np.concatenate(
        [
            np.full(MIN_TRAIN_ROWS * 2, 2020),
            np.full(MIN_TEST_ROWS * 2, 2021),
            np.full(MIN_TEST_ROWS * 2, 2022),
        ]
    )
    y_train = np.zeros(MIN_TRAIN_ROWS * 2, dtype=int)
    y_train[: MIN_TRAIN_CLASS - 1] = 1  # one short of the threshold
    y_val = rng.integers(0, 2, MIN_TEST_ROWS * 2)
    y_test = rng.integers(0, 2, MIN_TEST_ROWS * 2)
    y = np.concatenate([y_train, y_val, y_test])
    fold = build_fold(years, test_year=2022)
    feas = check_fold(fold, y)
    assert not feas.ok
    assert feas.reason == "skip_train_imbalance"


def test_check_fold_skips_when_test_class_imbalanced():
    n_train = MIN_TRAIN_ROWS * 2
    n_val = MIN_TEST_ROWS
    n_test = MIN_TEST_ROWS * 2
    years = np.concatenate(
        [
            np.full(n_train, 2020),
            np.full(n_val, 2021),
            np.full(n_test, 2022),
        ]
    )
    y_train = np.concatenate([np.zeros(n_train // 2, dtype=int), np.ones(n_train // 2, dtype=int)])
    y_val = np.zeros(n_val, dtype=int)
    # MIN_TEST_CLASS minus 1 positives → fails the test-imbalance check.
    y_test = np.zeros(n_test, dtype=int)
    y_test[: MIN_TEST_CLASS - 1] = 1
    y = np.concatenate([y_train, y_val, y_test])
    fold = build_fold(years, test_year=2022)
    feas = check_fold(fold, y)
    assert not feas.ok
    assert feas.reason == "skip_test_imbalance"


def test_check_fold_accepts_healthy_split():
    n_train = MIN_TRAIN_ROWS * 4
    n_val = MIN_TEST_ROWS * 4
    n_test = MIN_TEST_ROWS * 4
    years = np.concatenate(
        [
            np.full(n_train, 2020),
            np.full(n_val, 2021),
            np.full(n_test, 2022),
        ]
    )
    rng = np.random.default_rng(42)
    y = rng.integers(0, 2, n_train + n_val + n_test)
    fold = build_fold(years, test_year=2022)
    feas = check_fold(fold, y)
    assert feas.ok
    assert feas.reason == "ok"
    assert feas.n_train == n_train
    assert feas.n_val == n_val
    assert feas.n_test == n_test


def test_extract_years_reads_ts_year_column():
    df = pd.DataFrame({YEAR_COLUMN: [2020, 2021, 2022], "other": [1, 2, 3]})
    years = extract_years(df)
    assert list(years.astype(int)) == [2020, 2021, 2022]


def test_extract_years_raises_when_column_missing():
    df = pd.DataFrame({"other": [1, 2, 3]})
    with pytest.raises(KeyError, match=YEAR_COLUMN):
        extract_years(df)
