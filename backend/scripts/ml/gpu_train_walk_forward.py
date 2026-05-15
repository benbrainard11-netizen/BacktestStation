"""Walk-forward fold planner for the GPU XGBoost runner.

For each test year, defines:
- train mask:  year <= test_year - TRAIN_END_OFFSET
- val mask:    year == test_year - VAL_OFFSET
- test mask:   year == test_year

Boundary semantics match
`backend/scripts/ml/snapshot_walk_forward.py:_run_fold` so the GPU
runner produces fold splits identical to the CPU LightGBM baseline.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .gpu_train_constants import (
    MIN_TEST_CLASS,
    MIN_TEST_ROWS,
    MIN_TRAIN_CLASS,
    MIN_TRAIN_ROWS,
    TRAIN_END_OFFSET,
    VAL_OFFSET,
    YEAR_COLUMN,
)


@dataclass(frozen=True)
class FoldSplit:
    """A single walk-forward fold's masks and bookkeeping."""

    test_year: int
    train_end_year: int
    val_year: int
    train_mask: np.ndarray
    val_mask: np.ndarray
    test_mask: np.ndarray


def build_fold(years: np.ndarray, test_year: int) -> FoldSplit:
    """Build the (train, val, test) masks for a single walk-forward fold."""
    train_end = test_year - TRAIN_END_OFFSET
    val_year = test_year - VAL_OFFSET
    return FoldSplit(
        test_year=test_year,
        train_end_year=train_end,
        val_year=val_year,
        train_mask=years <= train_end,
        val_mask=years == val_year,
        test_mask=years == test_year,
    )


def extract_years(df: pd.DataFrame) -> np.ndarray:
    """Read the `ts.year` column as a numeric numpy array."""
    if YEAR_COLUMN not in df.columns:
        raise KeyError(f"matrix is missing required column {YEAR_COLUMN!r}")
    return pd.to_numeric(df[YEAR_COLUMN], errors="coerce").to_numpy()


@dataclass(frozen=True)
class FoldFeasibility:
    """Why a fold can or can't be trained."""

    ok: bool
    reason: str
    n_train: int
    n_val: int
    n_test: int


def check_fold(
    fold: FoldSplit,
    y: np.ndarray,
    *,
    min_train: int = MIN_TRAIN_ROWS,
    min_test: int = MIN_TEST_ROWS,
    min_class_train: int = MIN_TRAIN_CLASS,
    min_class_test: int = MIN_TEST_CLASS,
) -> FoldFeasibility:
    """Apply the same skip rules used by the LightGBM walk-forward."""
    n_train = int(fold.train_mask.sum())
    n_val = int(fold.val_mask.sum())
    n_test = int(fold.test_mask.sum())

    if n_train < min_train or n_test < min_test:
        return FoldFeasibility(
            ok=False,
            reason="skip_small_split",
            n_train=n_train,
            n_val=n_val,
            n_test=n_test,
        )

    y_train = y[fold.train_mask]
    train_pos = int(y_train.sum())
    train_neg = n_train - train_pos
    if min(train_pos, train_neg) < min_class_train:
        return FoldFeasibility(
            ok=False,
            reason="skip_train_imbalance",
            n_train=n_train,
            n_val=n_val,
            n_test=n_test,
        )

    y_test = y[fold.test_mask]
    test_pos = int(y_test.sum())
    test_neg = n_test - test_pos
    if min(test_pos, test_neg) < min_class_test:
        return FoldFeasibility(
            ok=False,
            reason="skip_test_imbalance",
            n_train=n_train,
            n_val=n_val,
            n_test=n_test,
        )

    return FoldFeasibility(
        ok=True,
        reason="ok",
        n_train=n_train,
        n_val=n_val,
        n_test=n_test,
    )
