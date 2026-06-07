"""Statistical helper functions for NQ sweep outcome feature ranking."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy import stats

from app.research.nq_liquidity_sweep_outcomes_types import LiquiditySweepStudyConfig

CONT = "continuation_breakout"
REV = "failed_breakout_reversal"


def auc(pos: np.ndarray, neg: np.ndarray) -> float:
    values = np.concatenate([pos, neg])
    labels = np.concatenate([np.ones(len(pos)), np.zeros(len(neg))])
    ranks = stats.rankdata(values, method="average")
    pos_rank_sum = ranks[labels == 1].sum()
    return float((pos_rank_sum - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def cliffs_delta(pos: np.ndarray, neg: np.ndarray) -> float:
    comparisons = pos[:, None] - neg[None, :]
    greater = np.sum(comparisons > 0)
    less = np.sum(comparisons < 0)
    return float((greater - less) / comparisons.size)


def cohens_d(pos: np.ndarray, neg: np.ndarray) -> float:
    if len(pos) < 2 or len(neg) < 2:
        return math.nan
    pooled = math.sqrt((np.var(pos, ddof=1) + np.var(neg, ddof=1)) / 2)
    return float((np.mean(pos) - np.mean(neg)) / pooled) if pooled > 0 else 0.0


def bootstrap_auc_ci(
    labeled: pd.DataFrame,
    feature: str,
    config: LiquiditySweepStudyConfig,
) -> tuple[float | None, float | None]:
    rng = np.random.default_rng(config.random_seed)
    dates = labeled["session_date"].dropna().unique()
    if len(dates) < 2:
        return None, None
    values = labeled[feature].to_numpy(float)
    labels = labeled["outcome_label"].to_numpy()
    session_dates = labeled["session_date"].to_numpy()
    date_indexes = {date: np.flatnonzero(session_dates == date) for date in dates}
    aucs: list[float] = []
    for _ in range(config.bootstrap_iterations):
        chosen = rng.choice(dates, size=len(dates), replace=True)
        sample_indexes = np.concatenate([date_indexes[d] for d in chosen])
        sample_labels = labels[sample_indexes]
        sample_values = values[sample_indexes]
        cont = sample_values[sample_labels == CONT]
        rev = sample_values[sample_labels == REV]
        if len(cont) and len(rev):
            aucs.append(auc(cont, rev))
    if not aucs:
        return None, None
    return float(np.quantile(aucs, 0.025)), float(np.quantile(aucs, 0.975))


def permutation_p(
    labeled: pd.DataFrame,
    feature: str,
    config: LiquiditySweepStudyConfig,
) -> float | None:
    rng = np.random.default_rng(config.random_seed)
    values = labeled[feature].to_numpy(float)
    labels = labeled["outcome_label"].to_numpy()
    observed = abs(median_diff(values, labels))
    if observed == 0:
        return 1.0
    hits = 0
    for _ in range(config.permutation_iterations):
        shuffled = rng.permutation(labels)
        if abs(median_diff(values, shuffled)) >= observed:
            hits += 1
    return float((hits + 1) / (config.permutation_iterations + 1))


def median_diff(values: np.ndarray, labels: np.ndarray) -> float:
    cont = values[labels == CONT]
    rev = values[labels == REV]
    return float(np.median(cont) - np.median(rev)) if len(cont) and len(rev) else 0.0


def stability(monthly: list[dict[str, object]], global_diff: float) -> dict[str, object]:
    global_dir = effect_direction(global_diff)
    evaluated = [row for row in monthly if row["effect_direction"] != "flat"]
    if not evaluated or global_dir == "flat":
        return {
            "same_direction_months": 0,
            "worst_month_auc": None,
            "best_month_auc": None,
            "stability_score": 0.0,
        }
    same = sum(row["effect_direction"] == global_dir for row in evaluated)
    sep = [float(row["monthly_separation_auc"]) for row in evaluated]
    return {
        "same_direction_months": int(same),
        "worst_month_auc": float(min(sep)),
        "best_month_auc": float(max(sep)),
        "stability_score": float(same / len(evaluated)),
    }


def rank_score(row: dict[str, object]) -> float:
    sample_score = min(float(row["sample_size_total"]) / 100.0, 1.0)
    return float(
        0.40 * float(row["separation_auc"])
        + 0.25 * abs(float(row["cliffs_delta"]))
        + 0.25 * float(row["stability_score"])
        + 0.10 * sample_score
    )


def ranking_reason(row: dict[str, object]) -> str:
    direction = (
        "higher continuation values"
        if row["median_difference"] >= 0
        else "lower continuation values"
    )
    return (
        f"{direction}; separation_auc={row['separation_auc']:.3f}; "
        f"cliffs_delta={row['cliffs_delta']:.3f}; "
        f"stability={row['stability_score']:.2f}; n={row['sample_size_total']}"
    )


def monthly_auc_string(rows: list[dict[str, object]]) -> str:
    return "; ".join(f"{row['month']}:{row['monthly_auc']:.3f}" for row in rows)


def monthly_direction_string(rows: list[dict[str, object]]) -> str:
    return "; ".join(f"{row['month']}:{row['effect_direction']}" for row in rows)


def effect_direction(diff: float) -> str:
    if diff > 0:
        return "continuation_higher"
    if diff < 0:
        return "reversal_higher"
    return "flat"
