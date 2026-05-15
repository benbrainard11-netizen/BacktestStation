"""Per-fold training pipeline for the GPU runner.

Pulled out of `gpu_train_runner.py` so each file stays under the
300-line readability floor (CLAUDE.md rule #10). The runner imports
`run_fold` and the helper hashers; this module never reads CLI args.
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .gpu_train_constants import (
    EVENT_TYPE_COLUMN,
    SIDE_COLUMN,
    SNAPSHOT_COLUMN,
)
from .gpu_train_metrics import compute_fold_metrics
from .gpu_train_outputs import fold_records_to_dict
from .gpu_train_schema_safe import (
    assert_no_label_leak,
    encode_like_train,
    select_usable_features,
)
from .gpu_train_walk_forward import build_fold, check_fold
from .gpu_train_xgb import train_one_fold


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_sha() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            cwd=Path(__file__).resolve().parent,
        )
        return out.stdout.strip()
    except Exception:
        return "unknown"


def filter_matrix(
    df: pd.DataFrame,
    *,
    snapshot: str,
    side: str,
    event_type: str,
) -> pd.DataFrame:
    """Apply the matrix-level filters once before fold iteration."""
    mask = df[SNAPSHOT_COLUMN] == snapshot
    if side != "all":
        mask &= df[SIDE_COLUMN] == side
    if event_type != "all":
        mask &= df[EVENT_TYPE_COLUMN] == event_type
    return df.loc[mask].copy()


def _skip_record(test_year: int, reason: str, feas) -> dict[str, Any]:
    return {
        "status": reason,
        "test_year": test_year,
        "n_train": feas.n_train,
        "n_val": feas.n_val,
        "n_test": feas.n_test,
    }


def run_fold(
    *,
    df: pd.DataFrame,
    years: np.ndarray,
    y: np.ndarray,
    label: str,
    feature_pool: list[str],
    test_year: int,
    device: str,
) -> dict[str, Any]:
    """Train one fold; return a record describing the result or skip reason."""
    fold = build_fold(years, test_year)
    feas = check_fold(fold, y)
    if not feas.ok:
        return _skip_record(test_year, feas.reason, feas)

    train_df = df.loc[fold.train_mask]
    val_df = df.loc[fold.val_mask]
    test_df = df.loc[fold.test_mask]

    usable, categorical, _ = select_usable_features(train_df, feature_pool)
    if not usable:
        return _skip_record(test_year, "skip_no_features", feas)

    x_train = encode_like_train(train_df, usable, categorical)
    feature_names = list(x_train.columns)
    assert_no_label_leak(feature_names)
    x_val = encode_like_train(val_df, usable, categorical, feature_names)
    x_test = encode_like_train(test_df, usable, categorical, feature_names)

    outputs = train_one_fold(
        x_train=x_train.to_numpy(),
        y_train=y[fold.train_mask],
        x_val=x_val.to_numpy() if len(x_val) else None,
        y_val=y[fold.val_mask] if len(x_val) else None,
        x_test=x_test.to_numpy(),
        feature_names=feature_names,
        device=device,
    )
    metrics = compute_fold_metrics(
        y_train=y[fold.train_mask],
        y_val=y[fold.val_mask],
        y_test=y[fold.test_mask],
        p_train=outputs.p_train,
        p_val=outputs.p_val,
        p_test=outputs.p_test,
        best_iteration=outputs.best_iteration,
    )

    predictions = pd.DataFrame(
        {
            "fold_test_year": test_year,
            "row_index": test_df.index.to_numpy(),
            "y_true": y[fold.test_mask],
            "p_test": outputs.p_test,
        }
    )
    importance_rows = [
        {"fold_test_year": test_year, "feature": feat, "gain": float(gain)}
        for feat, gain in outputs.feature_importance.items()
    ]
    extras = {
        "label": label,
        "n_features_used": len(feature_names),
        "best_iteration": outputs.best_iteration,
    }
    return {
        "status": "ok",
        "test_year": test_year,
        "metrics": metrics,
        "record": fold_records_to_dict(test_year, metrics, extras),
        "predictions": predictions,
        "importance": importance_rows,
    }
