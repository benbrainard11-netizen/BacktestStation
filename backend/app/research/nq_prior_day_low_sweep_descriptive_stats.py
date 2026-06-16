"""Descriptive winner/loss tables for prior-day low sweep attempts."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy import stats

from app.research.nq_liquidity_sweep_outcomes_stats_metrics import (
    auc,
    cliffs_delta,
    cohens_d,
)

CATEGORICAL_FACTORS = (
    "time_of_day_bucket",
    "overnight_range_location_vs_sweep",
    "overnight_range_location",
    "opening_drive_aligned",
    "reclaimed_0_30s",
)

NUMERIC_FEATURES = (
    "sweep_minutes_after_rth_open",
    "post_5_30s_trade_events_per_second",
    "sweep_distance_pts",
    "sweep_distance_ticks",
    "time_to_reclaim_seconds",
)


def categorical_distributions(trades: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for scope, frame in scopes(trades):
        wins_total = int((frame["trade_result"] == "win").sum())
        losses_total = int((frame["trade_result"] == "loss").sum())
        baseline = wins_total / (wins_total + losses_total) if wins_total + losses_total else np.nan
        for factor in CATEGORICAL_FACTORS:
            if factor not in frame.columns:
                continue
            factor_effect = categorical_factor_effect(frame, factor)
            values = frame[factor].fillna("missing").astype(str)
            for category, group in frame.groupby(values, sort=True):
                wins = int((group["trade_result"] == "win").sum())
                losses = int((group["trade_result"] == "loss").sum())
                trades_n = wins + losses
                winner_share = wins / wins_total if wins_total else np.nan
                loser_share = losses / losses_total if losses_total else np.nan
                share_diff = winner_share - loser_share
                win_rate = wins / trades_n if trades_n else np.nan
                rows.append(
                    {
                        "scope": scope,
                        "factor": factor,
                        "category": category,
                        "trades": trades_n,
                        "wins": wins,
                        "losses": losses,
                        "winner_share": winner_share,
                        "loser_share": loser_share,
                        "winner_minus_loser_share": share_diff,
                        "category_win_rate": win_rate,
                        "baseline_win_rate": baseline,
                        "win_rate_delta": win_rate - baseline,
                        "effect_direction": direction(share_diff),
                        **factor_effect,
                    }
                )
    return pd.DataFrame(rows)


def numeric_distributions(trades: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for scope, frame in scopes(trades):
        for feature in NUMERIC_FEATURES:
            if feature not in frame.columns:
                continue
            for result, group in frame.groupby("trade_result", sort=True):
                values = pd.to_numeric(group[feature], errors="coerce").dropna()
                if values.empty:
                    continue
                rows.append(
                    {
                        "scope": scope,
                        "feature": feature,
                        "trade_result": result,
                        "sample_size": int(len(values)),
                        "mean": float(values.mean()),
                        "median": float(values.median()),
                        "std": float(values.std()) if len(values) > 1 else 0.0,
                        "p10": float(values.quantile(0.10)),
                        "p25": float(values.quantile(0.25)),
                        "p75": float(values.quantile(0.75)),
                        "p90": float(values.quantile(0.90)),
                    }
                )
    return pd.DataFrame(rows)


def numeric_effects(trades: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for scope, frame in scopes(trades):
        for feature in NUMERIC_FEATURES:
            if feature not in frame.columns:
                continue
            feature_frame = frame.loc[frame[feature].notna()].copy()
            wins = feature_frame.loc[
                feature_frame["trade_result"] == "win", feature
            ].to_numpy(float)
            losses = feature_frame.loc[
                feature_frame["trade_result"] == "loss", feature
            ].to_numpy(float)
            if len(wins) == 0 or len(losses) == 0:
                continue
            median_diff = float(np.median(wins) - np.median(losses))
            feature_auc = auc(wins, losses)
            rows.append(
                {
                    "scope": scope,
                    "feature": feature,
                    "sample_size": int(len(wins) + len(losses)),
                    "wins": int(len(wins)),
                    "losses": int(len(losses)),
                    "win_median": float(np.median(wins)),
                    "loss_median": float(np.median(losses)),
                    "median_difference_win_minus_loss": median_diff,
                    "auc_win_higher": feature_auc,
                    "separation_auc": max(feature_auc, 1.0 - feature_auc),
                    "cliffs_delta": cliffs_delta(wins, losses),
                    "cohens_d": cohens_d(wins, losses),
                    "ks_stat": float(stats.ks_2samp(wins, losses).statistic),
                    "effect_direction": direction(median_diff),
                }
            )
    return pd.DataFrame(rows)


def effect_consistency(
    categorical: pd.DataFrame,
    numeric: pd.DataFrame,
) -> pd.DataFrame:
    rows = categorical_consistency(categorical) + numeric_consistency(numeric)
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    rank = {"directionally_consistent": 0, "inconsistent": 1, "flat": 2, "too_sparse": 3}
    out["read_rank"] = out["read"].map(rank).fillna(9)
    return out.sort_values(
        ["read_rank", "effect_type", "effect_name"],
        ascending=[True, True, True],
    ).reset_index(drop=True)


def categorical_consistency(categorical: pd.DataFrame) -> list[dict[str, object]]:
    if categorical.empty:
        return []
    in_sample = categorical.loc[categorical["scope"] == "in_sample"]
    holdout = categorical.loc[categorical["scope"] == "holdout"]
    merged = in_sample.merge(holdout, on=["factor", "category"], suffixes=("_is", "_ho"))
    rows: list[dict[str, object]] = []
    for row in merged.itertuples(index=False):
        same = row.effect_direction_is == row.effect_direction_ho
        sparse = row.trades_is < 10 or row.trades_ho < 10
        read = consistency_read(same, sparse, row.effect_direction_is, row.effect_direction_ho)
        rows.append(
            {
                "effect_type": "categorical",
                "effect_name": f"{row.factor}={row.category}",
                "in_sample_direction": row.effect_direction_is,
                "holdout_direction": row.effect_direction_ho,
                "same_direction": same,
                "in_sample_sample": int(row.trades_is),
                "holdout_sample": int(row.trades_ho),
                "in_sample_primary_effect": float(row.winner_minus_loser_share_is),
                "holdout_primary_effect": float(row.winner_minus_loser_share_ho),
                "in_sample_effect_size": float(row.factor_cramers_v_is),
                "holdout_effect_size": float(row.factor_cramers_v_ho),
                "read": read,
            }
        )
    return rows


def numeric_consistency(numeric: pd.DataFrame) -> list[dict[str, object]]:
    if numeric.empty:
        return []
    in_sample = numeric.loc[numeric["scope"] == "in_sample"]
    holdout = numeric.loc[numeric["scope"] == "holdout"]
    merged = in_sample.merge(holdout, on="feature", suffixes=("_is", "_ho"))
    rows: list[dict[str, object]] = []
    for row in merged.itertuples(index=False):
        same = row.effect_direction_is == row.effect_direction_ho
        sparse = row.sample_size_is < 20 or row.sample_size_ho < 20
        read = consistency_read(same, sparse, row.effect_direction_is, row.effect_direction_ho)
        rows.append(
            {
                "effect_type": "numeric",
                "effect_name": row.feature,
                "in_sample_direction": row.effect_direction_is,
                "holdout_direction": row.effect_direction_ho,
                "same_direction": same,
                "in_sample_sample": int(row.sample_size_is),
                "holdout_sample": int(row.sample_size_ho),
                "in_sample_primary_effect": float(row.median_difference_win_minus_loss_is),
                "holdout_primary_effect": float(row.median_difference_win_minus_loss_ho),
                "in_sample_effect_size": float(row.cliffs_delta_is),
                "holdout_effect_size": float(row.cliffs_delta_ho),
                "in_sample_auc": float(row.auc_win_higher_is),
                "holdout_auc": float(row.auc_win_higher_ho),
                "read": read,
            }
        )
    return rows


def categorical_factor_effect(frame: pd.DataFrame, factor: str) -> dict[str, float]:
    values = frame[factor].fillna("missing").astype(str)
    table = pd.crosstab(frame["trade_result"], values)
    if table.shape[0] < 2 or table.shape[1] < 2:
        return {"factor_cramers_v": math.nan, "factor_chi2_p_value": math.nan}
    chi2, p_value, _, _ = stats.chi2_contingency(table, correction=False)
    total = table.to_numpy().sum()
    denominator = min(table.shape[0] - 1, table.shape[1] - 1)
    cramer = math.sqrt((chi2 / total) / denominator) if total and denominator else math.nan
    return {"factor_cramers_v": float(cramer), "factor_chi2_p_value": float(p_value)}


def consistency_read(same: bool, sparse: bool, first: str, second: str) -> str:
    if sparse:
        return "too_sparse"
    if first == "flat" or second == "flat":
        return "flat"
    return "directionally_consistent" if same else "inconsistent"


def scopes(df: pd.DataFrame) -> list[tuple[str, pd.DataFrame]]:
    return [
        ("full", df.copy()),
        ("in_sample", df.loc[~df["is_holdout"]].copy()),
        ("holdout", df.loc[df["is_holdout"]].copy()),
    ]


def direction(value: float) -> str:
    if value > 0:
        return "higher_in_winners"
    if value < 0:
        return "higher_in_losers"
    return "flat"
