"""Summary tables for the NQ opening-range descriptive study."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

LABELS = ("continuation_breakout", "failed_breakout_reversal", "ambiguous", "no_break")
CONTEXT_FACTORS = (
    "first_break_side",
    "opening_drive_alignment",
    "overnight_trend_bucket",
    "overnight_trend_alignment",
    "overnight_inventory_bucket",
    "rth_gap_bucket",
    "gap_alignment",
    "opening_drive_direction",
    "opening_drive_close_bucket",
    "time_of_break_bucket",
)


def baseline_summary(events: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for scope, frame in scopes(events):
        rows.append(_rate_row(scope, "all", "all", frame))
        for side, group in frame.groupby("first_break_side", dropna=False, sort=True):
            rows.append(_rate_row(scope, "first_break_side", str(side), group))
    return pd.DataFrame(rows)


def context_summary(events: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for scope, frame in scopes(events):
        baseline = _continuation_rate(frame)
        for factor in CONTEXT_FACTORS:
            if factor not in frame.columns:
                continue
            for category, group in frame.groupby(factor, dropna=False, sort=True):
                row = _rate_row(scope, factor, str(category), group)
                row["baseline_continuation_rate"] = baseline
                row["continuation_rate_delta"] = row["continuation_rate"] - baseline
                row["effect_direction"] = direction(row["continuation_rate_delta"])
                row["factor_cramers_v"] = cramers_v(frame, factor)
                rows.append(row)
    return pd.DataFrame(rows)


def context_consistency(context: pd.DataFrame) -> pd.DataFrame:
    if context.empty:
        return pd.DataFrame()
    in_sample = context.loc[context["scope"] == "in_sample"]
    holdout = context.loc[context["scope"] == "holdout"]
    merged = in_sample.merge(holdout, on=["factor", "category"], suffixes=("_is", "_ho"))
    if merged.empty:
        return merged
    merged["same_direction"] = merged["effect_direction_is"] == merged["effect_direction_ho"]
    merged["read"] = [
        consistency_read(same, n_is, n_ho, d_is, d_ho)
        for same, n_is, n_ho, d_is, d_ho in zip(
            merged["same_direction"],
            merged["labeled_count_is"],
            merged["labeled_count_ho"],
            merged["effect_direction_is"],
            merged["effect_direction_ho"],
            strict=False,
        )
    ]
    rank = {"directionally_consistent": 0, "inconsistent": 1, "flat": 2, "too_sparse": 3}
    merged["read_rank"] = merged["read"].map(rank).fillna(9)
    return merged.sort_values(
        ["read_rank", "factor", "category"],
        ascending=[True, True, True],
    ).reset_index(drop=True)


def monthly_summary(events: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    if events.empty:
        return pd.DataFrame()
    for month, group in events.groupby("month", sort=True):
        row = _rate_row("month", "month", month, group)
        row["month"] = month
        rows.append(row)
    return pd.DataFrame(rows)


def _rate_row(scope: str, factor: str, category: str, frame: pd.DataFrame) -> dict[str, object]:
    counts = {label: int((frame["outcome_label"] == label).sum()) for label in LABELS}
    labeled = counts["continuation_breakout"] + counts["failed_breakout_reversal"]
    total = int(len(frame))
    if "first_break_side" in frame:
        high_first = int((frame["first_break_side"] == "high").sum())
        low_first = int((frame["first_break_side"] == "low").sum())
    else:
        high_first = 0
        low_first = 0
    return {
        "scope": scope,
        "factor": factor,
        "category": category,
        "sessions": total,
        "labeled_count": labeled,
        "continuations": counts["continuation_breakout"],
        "reversals": counts["failed_breakout_reversal"],
        "ambiguous": counts["ambiguous"],
        "no_break": counts["no_break"],
        "continuation_rate": counts["continuation_breakout"] / labeled if labeled else np.nan,
        "reversal_rate": counts["failed_breakout_reversal"] / labeled if labeled else np.nan,
        "high_first_rate": high_first / total if total else np.nan,
        "low_first_rate": low_first / total if total else np.nan,
    }


def _continuation_rate(frame: pd.DataFrame) -> float:
    labeled = frame.loc[frame["outcome_label"].isin(LABELS[:2])]
    if labeled.empty:
        return np.nan
    return float((labeled["outcome_label"] == "continuation_breakout").mean())


def cramers_v(frame: pd.DataFrame, factor: str) -> float:
    labeled = frame.loc[frame["outcome_label"].isin(LABELS[:2])]
    if labeled.empty:
        return np.nan
    table = pd.crosstab(labeled[factor].astype(str), labeled["outcome_label"])
    if table.shape[0] < 2 or table.shape[1] < 2:
        return np.nan
    chi2, _, _, _ = stats.chi2_contingency(table, correction=False)
    total = table.to_numpy().sum()
    denom = min(table.shape[0] - 1, table.shape[1] - 1)
    return float(np.sqrt((chi2 / total) / denom)) if total and denom else np.nan


def consistency_read(
    same: bool,
    n_is: int,
    n_ho: int,
    direction_is: str,
    direction_ho: str,
) -> str:
    if n_is < 10 or n_ho < 10:
        return "too_sparse"
    if direction_is == "flat" or direction_ho == "flat":
        return "flat"
    return "directionally_consistent" if same else "inconsistent"


def direction(value: float) -> str:
    if pd.isna(value) or abs(float(value)) < 1e-12:
        return "flat"
    if value > 0:
        return "higher_continuation"
    return "lower_continuation"


def scopes(df: pd.DataFrame) -> list[tuple[str, pd.DataFrame]]:
    return [
        ("full", df.copy()),
        ("in_sample", df.loc[~df["is_holdout"]].copy()),
        ("holdout", df.loc[df["is_holdout"]].copy()),
    ]
