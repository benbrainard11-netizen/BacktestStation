"""Schema-safe feature loader for exported anchor matrices.

Invariants enforced here:

1. Only columns listed in `schema['feature_columns']` are eligible.
2. Any column starting with `LABEL_COLUMN_PREFIX` is rejected on
   principle, even if it leaked into `feature_columns` by mistake.
   Prompt B rule: "Never use `label.*` columns as model inputs."
3. Encoding mirrors `backend/scripts/ml/snapshot_walk_forward.py`
   (`pd.get_dummies(dummy_na=True)` then float64) so the GPU runner's
   inputs are byte-identical in shape to the CPU LightGBM baseline.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .gpu_train_constants import LABEL_COLUMN_PREFIX, MANUAL_CELL_COLUMN


def load_schema(path: Path) -> dict[str, Any]:
    """Read a `<matrix>.schema.json` file into a dict."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def schema_safe_feature_columns(
    schema: dict[str, Any],
    *,
    include_manual_cell: bool = False,
) -> list[str]:
    """Return `schema['feature_columns']` with all label-leak risks dropped.

    The schema is treated as advisory: any column whose name starts with
    `LABEL_COLUMN_PREFIX` is removed even if the schema author put it in
    `feature_columns`. This is a defense-in-depth check, not a normal
    expectation.
    """
    declared = list(schema.get("feature_columns") or [])
    safe = [c for c in declared if not c.startswith(LABEL_COLUMN_PREFIX)]
    if not include_manual_cell:
        safe = [c for c in safe if c != MANUAL_CELL_COLUMN]
    return safe


def assert_no_label_leak(columns: list[str]) -> None:
    """Raise if any column in `columns` starts with `LABEL_COLUMN_PREFIX`."""
    leaks = [c for c in columns if c.startswith(LABEL_COLUMN_PREFIX)]
    if leaks:
        raise ValueError(
            "label-prefixed columns must never reach the model input: "
            f"{leaks[:5]}{'...' if len(leaks) > 5 else ''}"
        )


def select_usable_features(
    train_df: pd.DataFrame,
    feature_cols: list[str],
) -> tuple[list[str], list[str], list[str]]:
    """Drop all-NaN and constant columns from `feature_cols` using train data.

    Returns `(usable, categorical, dropped)`.
    """
    selected = [c for c in feature_cols if c in train_df.columns]
    usable: list[str] = []
    dropped: list[str] = []
    for col in selected:
        s = train_df[col]
        if s.notna().sum() == 0 or s.nunique(dropna=True) <= 1:
            dropped.append(col)
            continue
        usable.append(col)
    categorical = [
        c
        for c in usable
        if pd.api.types.is_object_dtype(train_df[c])
        or pd.api.types.is_string_dtype(train_df[c])
        or pd.api.types.is_categorical_dtype(train_df[c])
    ]
    return usable, categorical, dropped


def encode_like_train(
    source: pd.DataFrame,
    usable: list[str],
    categorical: list[str],
    train_columns: list[str] | None = None,
) -> pd.DataFrame:
    """One-hot + numeric coerce, reindexed to the train column set.

    Mirrors `snapshot_walk_forward.py:_encode_like_train` exactly so the
    GPU runner can be compared apples-to-apples against the CPU baseline.
    """
    x = source[usable].copy()
    x = pd.get_dummies(x, columns=categorical, dummy_na=True)
    for col in x.columns:
        if x[col].dtype == bool:
            x[col] = x[col].astype(np.int8)
        elif pd.api.types.is_object_dtype(x[col]):
            x[col] = pd.to_numeric(x[col], errors="coerce")
    x = x.astype("float64")
    if train_columns is not None:
        x = x.reindex(columns=train_columns, fill_value=0.0)
    return x


def coerce_binary_label(s: pd.Series) -> pd.Series:
    """Coerce a label column to nullable Int64 with {0,1} values."""
    if s.dtype == bool:
        return s.astype("Int64")
    return pd.to_numeric(s, errors="coerce").astype("Int64")
