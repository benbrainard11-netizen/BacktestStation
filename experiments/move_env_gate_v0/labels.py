"""Label helpers for move-occurrence and bad-environment gates.

These labels assume the source table already measured forward outcomes after the
decision time. This module does not read future prices directly; it only converts
existing honest forward columns into the v0 gate targets.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

REQUIRED_FORWARD_COLUMNS = ("mfe_R", "mae_R", "realized_R")


def attach_move_env_labels(
    df: pd.DataFrame,
    *,
    target_r: float = 1.0,
    bad_r: float = 1.0,
) -> pd.DataFrame:
    """Attach MOVE/BAD_ENV/CHOP labels from entry-relative R columns.

    y_move:
        Either side moved at least one barrier unit. This is the "movement is
        coming" target, not a directional target.
    y_favorable_move:
        The candidate's favorable barrier was touched at any point.
    y_bad_env:
        The stop-side barrier won first. This is the skip/downsize target.
    y_chop:
        Neither favorable nor adverse barrier was touched before timeout.
    """
    missing = [c for c in REQUIRED_FORWARD_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"source is missing required forward columns: {missing}")

    out = df.copy()
    mfe = pd.to_numeric(out["mfe_R"], errors="coerce")
    mae = pd.to_numeric(out["mae_R"], errors="coerce")
    realized = pd.to_numeric(out["realized_R"], errors="coerce")

    out["y_move"] = ((mfe >= target_r) | (mae >= bad_r)).astype("int8")
    out["y_favorable_move"] = (mfe >= target_r).astype("int8")
    out["y_bad_env"] = (realized <= -bad_r).astype("int8")
    out["y_chop"] = ((mfe < target_r) & (mae < bad_r)).astype("int8")
    out["y_timeout_mark"] = ((realized > -bad_r) & (realized < target_r)).astype("int8")
    out["label_target_r"] = float(target_r)
    out["label_bad_r"] = float(bad_r)
    out["label_source"] = "entry_relative_mfe_mae_realized_R"
    return out


def label_summary(df: pd.DataFrame) -> dict[str, float | int]:
    """Return compact label diagnostics for manifests and reports."""
    cols = ["y_move", "y_favorable_move", "y_bad_env", "y_chop"]
    out: dict[str, float | int] = {"rows": int(len(df))}
    for col in cols:
        if col in df:
            out[f"{col}_rate"] = float(np.nanmean(pd.to_numeric(df[col])))
    if "realized_R" in df:
        r = pd.to_numeric(df["realized_R"], errors="coerce")
        out["mean_realized_R"] = float(r.mean())
    return out

