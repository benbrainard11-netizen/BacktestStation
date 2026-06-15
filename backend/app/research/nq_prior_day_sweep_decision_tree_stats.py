"""Walk-forward statistics for the NQ prior-day sweep decision-tree study."""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.research.nq_liquidity_sweep_outcomes_stats_metrics import auc, cliffs_delta
from app.research.nq_prior_day_sweep_decision_tree_types import (
    CONT,
    REV,
    DecisionTreeStudyConfig,
)

CATEGORICAL_FACTORS = [
    "level_type",
    "overnight_trend_vs_sweep",
    "overnight_range_location_vs_sweep",
    "rth_gap_vs_sweep",
    "time_of_day_bucket",
    "pre60_dir_aggr_ratio_band",
]

NUMERIC_FACTORS = [
    "directional_overnight_trend_pts",
    "directional_rth_gap_pts",
    "directional_rth_open_overnight_location",
    "sweep_minutes_after_rth_open",
    "pre_60s_directional_aggressive_trade_ratio",
]

COMBINATION_FACTORS = [
    ("level_type", "overnight_trend_vs_sweep"),
    ("level_type", "overnight_range_location_vs_sweep"),
    ("level_type", "rth_gap_vs_sweep"),
    ("level_type", "time_of_day_bucket"),
    ("level_type", "pre60_dir_aggr_ratio_band"),
    ("overnight_trend_vs_sweep", "rth_gap_vs_sweep"),
    ("overnight_range_location_vs_sweep", "rth_gap_vs_sweep"),
    ("overnight_range_location_vs_sweep", "pre60_dir_aggr_ratio_band"),
    ("rth_gap_vs_sweep", "pre60_dir_aggr_ratio_band"),
]


def add_combination_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for first, second in COMBINATION_FACTORS:
        if first in out.columns and second in out.columns:
            out[combo_name(first, second)] = out[first].astype(str) + " + " + out[
                second
            ].astype(str)
    return out


def combination_names() -> list[str]:
    return [combo_name(first, second) for first, second in COMBINATION_FACTORS]


def categorical_decision_table(
    df: pd.DataFrame,
    factors: list[str],
    config: DecisionTreeStudyConfig,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for factor in factors:
        if factor in df.columns:
            rows.extend(_walk_forward_rows(df, factor, config))
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    out["oos_delta"] = out["oos_continuation_rate"] - out["oos_baseline_rate"]
    out["oos_failure_rate"] = 1.0 - out["oos_continuation_rate"]
    out["oos_failure_rate_change"] = out["oos_failure_rate"] - (
        1.0 - out["oos_baseline_rate"]
    )
    out["stability_rate"] = out["folds_improved_vs_test_baseline"] / out[
        "folds_evaluated"
    ].where(out["folds_evaluated"] > 0)
    out["historical_direction"] = out["median_train_delta"].map(direction_from_delta)
    out["verdict"] = out.apply(_verdict, axis=1)
    return out.sort_values(
        ["oos_delta", "stability_rate", "oos_sample_size"],
        ascending=[False, False, False],
    ).reset_index(drop=True)


def factor_rankings_from_decision_table(table: pd.DataFrame) -> pd.DataFrame:
    if table.empty:
        return table
    rows = []
    for factor, group in table.groupby("factor"):
        candidates = group.loc[group["median_train_delta"] > 0].copy()
        if candidates.empty:
            candidates = group.copy()
        best = candidates.sort_values(
            ["oos_delta", "stability_rate", "oos_sample_size"],
            ascending=[False, False, False],
        ).iloc[0]
        sample_score = min(float(best["oos_sample_size"]) / 50.0, 1.0)
        rank_score = (
            0.50 * max(float(best["oos_delta"]), 0.0)
            + 0.30 * float(best["stability_rate"])
            + 0.20 * sample_score
        )
        rows.append(_ranking_row(factor, best, rank_score))
    out = pd.DataFrame(rows).sort_values(
        ["rank_score", "oos_delta", "oos_sample_size"],
        ascending=[False, False, False],
    )
    out.insert(0, "rank", range(1, len(out) + 1))
    return out.reset_index(drop=True)


def numeric_factor_stats(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for feature in NUMERIC_FACTORS:
        if feature not in df.columns:
            continue
        frame = df[["session_date", "fixed_outcome_label", feature]].copy()
        frame[feature] = pd.to_numeric(frame[feature], errors="coerce")
        frame = frame.loc[frame[feature].notna()]
        cont = frame.loc[frame["fixed_outcome_label"] == CONT, feature].to_numpy(float)
        rev = frame.loc[frame["fixed_outcome_label"] == REV, feature].to_numpy(float)
        if len(cont) == 0 or len(rev) == 0:
            continue
        feature_auc = auc(cont, rev)
        med_diff = float(np.median(cont) - np.median(rev))
        monthly = _monthly_numeric_rows(frame, feature)
        rows.append(_numeric_row(feature, frame, cont, rev, feature_auc, med_diff, monthly))
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(
        ["separation_auc", "months_same_direction", "sample_size"],
        ascending=[False, False, False],
    ).reset_index(drop=True)


def monthly_outcomes(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for month, group in df.groupby("month", sort=True):
        cont = int((group["fixed_outcome_label"] == CONT).sum())
        rev = int((group["fixed_outcome_label"] == REV).sum())
        total = cont + rev
        rows.append(
            {
                "month": month,
                "sample_size": total,
                "continuations": cont,
                "reversals": rev,
                "continuation_rate": cont / total if total else np.nan,
                "failure_rate": rev / total if total else np.nan,
            }
        )
    return pd.DataFrame(rows)


def direction_from_delta(value: float) -> str:
    if value > 0:
        return "improved_continuation"
    if value < 0:
        return "worsened_continuation"
    return "flat"


def combo_name(first: str, second: str) -> str:
    return f"{first}__x__{second}"


def _walk_forward_rows(
    df: pd.DataFrame,
    factor: str,
    config: DecisionTreeStudyConfig,
) -> list[dict[str, object]]:
    months = sorted(df["month"].dropna().unique())
    by_category: dict[str, list[dict[str, float]]] = {}
    for idx in range(config.min_train_months, len(months)):
        train = df.loc[df["month"].isin(months[:idx])]
        test = df.loc[df["month"] == months[idx]]
        _collect_factor_fold(by_category, train, test, factor, config)
    return [_category_summary(factor, category, rows) for category, rows in by_category.items()]


def _collect_factor_fold(
    by_category: dict[str, list[dict[str, float]]],
    train: pd.DataFrame,
    test: pd.DataFrame,
    factor: str,
    config: DecisionTreeStudyConfig,
) -> None:
    if train.empty or test.empty:
        return
    train_base = _continuation_rate(train)
    test_base = _continuation_rate(test)
    for category in sorted(train[factor].dropna().astype(str).unique()):
        train_cat = train.loc[train[factor].astype(str) == category]
        test_cat = test.loc[test[factor].astype(str) == category]
        if len(train_cat) < config.min_category_train_sample or test_cat.empty:
            continue
        train_rate = _continuation_rate(train_cat)
        test_rate = _continuation_rate(test_cat)
        by_category.setdefault(category, []).append(
            {
                "test_sample": float(len(test_cat)),
                "test_cont": float((test_cat["fixed_outcome_label"] == CONT).sum()),
                "test_rev": float((test_cat["fixed_outcome_label"] == REV).sum()),
                "test_base_cont": float((test["fixed_outcome_label"] == CONT).sum()),
                "test_base_total": float(len(test)),
                "train_delta": train_rate - train_base,
                "test_delta": test_rate - test_base,
            }
        )


def _category_summary(
    factor: str,
    category: str,
    fold_rows: list[dict[str, float]],
) -> dict[str, object]:
    sample = sum(row["test_sample"] for row in fold_rows)
    cont = sum(row["test_cont"] for row in fold_rows)
    base_cont = sum(row["test_base_cont"] for row in fold_rows)
    base_total = sum(row["test_base_total"] for row in fold_rows)
    return {
        "factor": factor,
        "category": category,
        "folds_evaluated": len(fold_rows),
        "oos_sample_size": int(sample),
        "oos_continuations": int(cont),
        "oos_reversals": int(sum(row["test_rev"] for row in fold_rows)),
        "oos_continuation_rate": cont / sample if sample else np.nan,
        "oos_baseline_rate": base_cont / base_total if base_total else np.nan,
        "median_train_delta": float(np.median([row["train_delta"] for row in fold_rows])),
        "folds_improved_vs_test_baseline": int(
            sum(row["test_delta"] > 0 for row in fold_rows)
        ),
    }


def _ranking_row(factor: str, best: pd.Series, rank_score: float) -> dict[str, object]:
    return {
        "factor": factor,
        "best_context": best["category"],
        "best_historical_direction": best["historical_direction"],
        "oos_sample_size": int(best["oos_sample_size"]),
        "oos_continuation_rate": float(best["oos_continuation_rate"]),
        "oos_baseline_rate": float(best["oos_baseline_rate"]),
        "oos_delta": float(best["oos_delta"]),
        "oos_failure_rate": float(best["oos_failure_rate"]),
        "folds_evaluated": int(best["folds_evaluated"]),
        "stability_rate": float(best["stability_rate"]),
        "rank_score": float(rank_score),
        "verdict": best["verdict"],
    }


def _numeric_row(
    feature: str,
    frame: pd.DataFrame,
    cont: np.ndarray,
    rev: np.ndarray,
    feature_auc: float,
    med_diff: float,
    monthly: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "feature": feature,
        "sample_size": int(len(frame)),
        "continuation_count": int(len(cont)),
        "reversal_count": int(len(rev)),
        "continuation_median": float(np.median(cont)),
        "reversal_median": float(np.median(rev)),
        "median_difference": med_diff,
        "auc": feature_auc,
        "separation_auc": max(feature_auc, 1.0 - feature_auc),
        "cliffs_delta": cliffs_delta(cont, rev),
        "effect_direction": direction_from_delta(med_diff),
        "months_evaluated": len(monthly),
        "months_same_direction": _same_direction_months(monthly, med_diff),
        "monthly_auc_values": "; ".join(
            f"{row['month']}:{row['auc']:.3f}" for row in monthly
        ),
    }


def _monthly_numeric_rows(df: pd.DataFrame, feature: str) -> list[dict[str, object]]:
    rows = []
    frame = df.copy()
    frame["month"] = pd.to_datetime(frame["session_date"]).dt.to_period("M").astype(str)
    for month, group in frame.groupby("month", sort=True):
        cont = group.loc[group["fixed_outcome_label"] == CONT, feature].to_numpy(float)
        rev = group.loc[group["fixed_outcome_label"] == REV, feature].to_numpy(float)
        if len(cont) and len(rev):
            rows.append(
                {
                    "month": month,
                    "auc": auc(cont, rev),
                    "median_difference": float(np.median(cont) - np.median(rev)),
                }
            )
    return rows


def _same_direction_months(rows: list[dict[str, object]], global_diff: float) -> int:
    direction = direction_from_delta(global_diff)
    if direction == "flat":
        return 0
    return sum(direction_from_delta(float(row["median_difference"])) == direction for row in rows)


def _continuation_rate(df: pd.DataFrame) -> float:
    return float((df["fixed_outcome_label"] == CONT).sum() / len(df)) if len(df) else np.nan


def _verdict(row: pd.Series) -> str:
    if row["oos_sample_size"] < 20:
        return "too_sparse"
    if row["median_train_delta"] > 0 and row["oos_delta"] > 0.05 and row["stability_rate"] >= 0.60:
        return "historically_improved"
    if row["median_train_delta"] < 0 and row["oos_delta"] < -0.05 and row["stability_rate"] <= 0.40:
        return "historically_worsened"
    return "mixed_or_weak"
