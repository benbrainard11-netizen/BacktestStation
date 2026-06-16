"""Holdout and walk-forward context validation for the frozen OR study."""

from __future__ import annotations

import math

import pandas as pd

CONTINUATION = "continuation_breakout"
REVERSAL = "failed_breakout_reversal"
OUTCOME_LABELS = (CONTINUATION, REVERSAL)

VALIDATION_FACTORS = (
    "opening_drive_alignment",
    "first_break_side",
    "overnight_inventory_bucket",
    "overnight_trend_alignment",
    "overnight_trend_bucket",
    "gap_alignment",
    "rth_gap_bucket",
    "opening_drive_close_bucket",
    "time_of_break_bucket",
)

MIN_HOLDOUT_LABELED = 10
MIN_WALK_FORWARD_FOLDS = 3
MIN_DIRECTIONAL_FOLD_RATE = 0.60
MEANINGFUL_DELTA = 0.05


def build_context_validation(events: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    walk_forward = walk_forward_validation(events)
    summary = context_validation_summary(events, walk_forward)
    return summary, walk_forward


def walk_forward_validation(events: pd.DataFrame) -> pd.DataFrame:
    labeled = labeled_events(events)
    if labeled.empty:
        return pd.DataFrame()
    months = sorted(labeled["month"].dropna().astype(str).unique())
    categories = factor_categories(labeled)
    rows: list[dict[str, object]] = []
    for month in months[1:]:
        train = labeled.loc[labeled["month"] < month]
        test = labeled.loc[labeled["month"] == month]
        if train.empty or test.empty:
            continue
        train_baseline = continuation_rate(train)
        test_baseline = continuation_rate(test)
        for factor, factor_categories_ in categories.items():
            for category in factor_categories_:
                train_group = train.loc[train[factor].astype(str) == category]
                test_group = test.loc[test[factor].astype(str) == category]
                train_delta = continuation_rate(train_group) - train_baseline
                test_delta = continuation_rate(test_group) - test_baseline
                rows.append(
                    {
                        "validation_month": month,
                        "factor": factor,
                        "category": category,
                        "train_labeled": int(len(train_group)),
                        "train_continuation_rate": continuation_rate(train_group),
                        "train_baseline_rate": train_baseline,
                        "train_delta": train_delta,
                        "train_effect_direction": effect_direction(train_delta),
                        "test_labeled": int(len(test_group)),
                        "test_continuation_rate": continuation_rate(test_group),
                        "test_baseline_rate": test_baseline,
                        "test_delta": test_delta,
                        "test_effect_direction": effect_direction(test_delta),
                        "same_direction": same_direction(train_delta, test_delta),
                    }
                )
    return pd.DataFrame(rows)


def context_validation_summary(
    events: pd.DataFrame,
    walk_forward: pd.DataFrame,
) -> pd.DataFrame:
    labeled = labeled_events(events)
    if labeled.empty:
        return pd.DataFrame()
    in_sample = labeled.loc[~labeled["is_holdout"]]
    holdout = labeled.loc[labeled["is_holdout"]]
    categories = factor_categories(labeled)
    rows: list[dict[str, object]] = []
    for factor, factor_categories_ in categories.items():
        for category in factor_categories_:
            full_group = group(labeled, factor, category)
            is_group = group(in_sample, factor, category)
            ho_group = group(holdout, factor, category)
            wf_group = walk_forward_group(walk_forward, factor, category)
            row = {
                "factor": factor,
                "category": category,
                **scope_fields("full", full_group, labeled),
                **scope_fields("in_sample", is_group, in_sample),
                **scope_fields("holdout", ho_group, holdout),
                **walk_forward_fields(wf_group),
            }
            row["read"] = stability_read(row)
            row["read_rank"] = read_rank(str(row["read"]))
            rows.append(row)
    return pd.DataFrame(rows).sort_values(
        ["read_rank", "factor", "category"],
        ascending=[True, True, True],
    )


def labeled_events(events: pd.DataFrame) -> pd.DataFrame:
    if events.empty:
        return events.copy()
    return events.loc[events["outcome_label"].isin(OUTCOME_LABELS)].copy()


def factor_categories(events: pd.DataFrame) -> dict[str, list[str]]:
    categories: dict[str, list[str]] = {}
    for factor in VALIDATION_FACTORS:
        if factor in events.columns:
            values = events[factor].dropna().astype(str).unique()
            categories[factor] = sorted(values)
    return categories


def group(events: pd.DataFrame, factor: str, category: str) -> pd.DataFrame:
    if events.empty:
        return events.copy()
    return events.loc[events[factor].astype(str) == category]


def scope_fields(
    prefix: str,
    frame: pd.DataFrame,
    baseline_frame: pd.DataFrame,
) -> dict[str, object]:
    rate = continuation_rate(frame)
    baseline = continuation_rate(baseline_frame)
    delta = rate - baseline
    return {
        f"{prefix}_labeled": int(len(frame)),
        f"{prefix}_continuations": int((frame["outcome_label"] == CONTINUATION).sum()),
        f"{prefix}_continuation_rate": rate,
        f"{prefix}_baseline_rate": baseline,
        f"{prefix}_delta": delta,
        f"{prefix}_delta_pp": delta * 100 if math.isfinite(delta) else math.nan,
        f"{prefix}_effect_direction": effect_direction(delta),
    }


def walk_forward_fields(wf_group: pd.DataFrame) -> dict[str, object]:
    usable = wf_group.loc[wf_group["test_labeled"] > 0] if not wf_group.empty else wf_group
    deltas = usable["test_delta"] if not usable.empty else pd.Series(dtype=float)
    positive = int((deltas > 0).sum()) if not deltas.empty else 0
    negative = int((deltas < 0).sum()) if not deltas.empty else 0
    same = int(usable["same_direction"].fillna(False).sum()) if not usable.empty else 0
    folds = int(len(usable))
    same_rate = same / folds if folds else math.nan
    mean_delta = float(deltas.mean()) if not deltas.empty else math.nan
    mean_direction = effect_direction(mean_delta)
    if mean_direction == "higher_continuation":
        directional_folds = positive
    elif mean_direction == "lower_continuation":
        directional_folds = negative
    else:
        directional_folds = 0
    return {
        "walk_forward_folds": folds,
        "walk_forward_test_labeled": int(usable["test_labeled"].sum()) if folds else 0,
        "walk_forward_positive_folds": positive,
        "walk_forward_negative_folds": negative,
        "walk_forward_directional_folds": directional_folds,
        "walk_forward_directional_fold_rate": directional_folds / folds if folds else math.nan,
        "walk_forward_same_direction_folds": same,
        "walk_forward_same_direction_rate": same_rate,
        "walk_forward_mean_delta": mean_delta,
        "walk_forward_mean_delta_pp": mean_delta * 100 if math.isfinite(mean_delta) else math.nan,
        "walk_forward_median_delta": float(deltas.median()) if not deltas.empty else math.nan,
        "walk_forward_effect_direction": mean_direction,
    }


def walk_forward_group(walk_forward: pd.DataFrame, factor: str, category: str) -> pd.DataFrame:
    if walk_forward.empty:
        return walk_forward.copy()
    return walk_forward.loc[
        walk_forward["factor"].eq(factor) & walk_forward["category"].eq(category)
    ].copy()


def continuation_rate(frame: pd.DataFrame) -> float:
    if frame.empty:
        return math.nan
    return float((frame["outcome_label"] == CONTINUATION).mean())


def effect_direction(delta: float) -> str:
    if not math.isfinite(delta) or abs(delta) < 1e-12:
        return "flat"
    return "higher_continuation" if delta > 0 else "lower_continuation"


def same_direction(train_delta: float, test_delta: float) -> bool | None:
    train = effect_direction(train_delta)
    test = effect_direction(test_delta)
    if train == "flat" or test == "flat":
        return None
    return train == test


def stability_read(row: dict[str, object]) -> str:
    holdout_labeled = int(row["holdout_labeled"])
    folds = int(row["walk_forward_folds"])
    if holdout_labeled < MIN_HOLDOUT_LABELED or folds < MIN_WALK_FORWARD_FOLDS:
        return "too_sparse"
    directions = [
        row["in_sample_effect_direction"],
        row["holdout_effect_direction"],
        row["walk_forward_effect_direction"],
    ]
    if "flat" in directions or len(set(directions)) > 1:
        return "inconsistent"
    if float(row["walk_forward_directional_fold_rate"]) < MIN_DIRECTIONAL_FOLD_RATE:
        return "inconsistent"
    holdout_delta = abs(float(row["holdout_delta"]))
    wf_delta = abs(float(row["walk_forward_mean_delta"]))
    if holdout_delta >= MEANINGFUL_DELTA and wf_delta >= MEANINGFUL_DELTA:
        return "stable_improver" if directions[0] == "higher_continuation" else "stable_worsener"
    return (
        "directionally_consistent_improver"
        if directions[0] == "higher_continuation"
        else "directionally_consistent_worsener"
    )


def read_rank(read: str) -> int:
    return {
        "stable_improver": 0,
        "stable_worsener": 1,
        "directionally_consistent_improver": 2,
        "directionally_consistent_worsener": 3,
        "inconsistent": 4,
        "too_sparse": 5,
    }.get(read, 9)
