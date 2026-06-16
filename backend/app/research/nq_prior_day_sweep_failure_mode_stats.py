"""Summary helpers for prior-day sweep failure-mode diagnostics."""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.research.nq_liquidity_sweep_outcomes_stats_metrics import auc, cliffs_delta

CATEGORICAL_FACTORS = [
    "variant_id",
    "entry_method",
    "target_method",
    "time_of_day_bucket",
    "level_type",
    "trade_side",
    "overnight_range_location_vs_sweep",
    "overnight_range_location",
    "overnight_trend_vs_sweep",
    "rth_gap_vs_sweep",
    "rth_gap_bucket",
    "opening_drive_aligned",
    "pre60_dir_aggr_ratio_band",
    "reclaimed_0_30s",
]

NUMERIC_FEATURES = [
    "sweep_minutes_after_rth_open",
    "sweep_distance_pts",
    "sweep_distance_ticks",
    "time_to_reclaim_seconds",
    "pre_60s_directional_aggressive_trade_ratio",
    "sweep_0_5s_mbp_events_per_second",
    "sweep_0_5s_trade_events_per_second",
    "post_5_30s_mbp_events_per_second",
    "post_5_30s_trade_events_per_second",
]


def categorical_summary(trades: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for scope, frame in scopes(trades):
        if frame.empty:
            continue
        baseline = float((frame["trade_result"] == "win").mean())
        for factor in CATEGORICAL_FACTORS:
            if factor not in frame.columns:
                continue
            values = frame[factor].fillna("missing").astype(str)
            for category, group in frame.groupby(values, sort=True):
                wins = int((group["trade_result"] == "win").sum())
                losses = int((group["trade_result"] == "loss").sum())
                total = wins + losses
                win_rate = wins / total if total else np.nan
                monthly = category_monthly_direction(frame, values, category)
                rows.append(
                    {
                        "scope": scope,
                        "factor": factor,
                        "category": category,
                        "trades": total,
                        "wins": wins,
                        "losses": losses,
                        "win_rate": win_rate,
                        "baseline_win_rate": baseline,
                        "win_rate_delta": win_rate - baseline,
                        "net_pnl": float(group["pnl_num"].sum()),
                        "avg_pnl": float(group["pnl_num"].mean()),
                        "median_pnl": float(group["pnl_num"].median()),
                        "months_evaluated": int(monthly["months_evaluated"]),
                        "months_above_baseline": int(monthly["months_above_baseline"]),
                        "monthly_direction_rate": float(monthly["direction_rate"]),
                    }
                )
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return out.sort_values(
        ["scope", "factor", "trades", "win_rate_delta"],
        ascending=[True, True, False, False],
    ).reset_index(drop=True)


def numeric_summary(trades: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for scope, frame in scopes(trades):
        for feature in NUMERIC_FEATURES:
            if feature not in frame.columns:
                continue
            feature_frame = frame.loc[frame[feature].notna()]
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
            monthly = monthly_direction(feature_frame, feature, median_diff)
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
                    "effect_direction": direction(median_diff),
                    "months_evaluated": int(monthly["months_evaluated"]),
                    "months_same_direction": int(monthly["months_same_direction"]),
                    "monthly_direction_rate": float(monthly["direction_rate"]),
                }
            )
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return out.sort_values(
        ["scope", "separation_auc", "sample_size"],
        ascending=[True, False, False],
    ).reset_index(drop=True)


def variant_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for scope, frame in scopes(df):
        for variant_id, group in frame.groupby("variant_id", sort=True):
            filled = group.loc[group["status"] == "filled"]
            win_loss = filled.loc[filled["trade_result"].isin(["win", "loss"])]
            pnl = pd.to_numeric(group["pnl_num"], errors="coerce").fillna(0.0)
            rows.append(
                {
                    "scope": scope,
                    "variant_id": variant_id,
                    "attempts": int(len(group)),
                    "filled_trades": int(len(filled)),
                    "skips": int((group["status"] == "skipped").sum()),
                    "wins": int((win_loss["trade_result"] == "win").sum()),
                    "losses": int((win_loss["trade_result"] == "loss").sum()),
                    "win_rate": float((win_loss["trade_result"] == "win").mean())
                    if len(win_loss)
                    else np.nan,
                    "net_pnl": float(pnl.sum()),
                    "avg_pnl_per_attempt": float(pnl.mean()),
                }
            )
    return pd.DataFrame(rows)


def hypotheses(numeric: pd.DataFrame) -> pd.DataFrame:
    if numeric.empty:
        return numeric
    full = numeric.loc[numeric["scope"] == "full"].copy()
    holdout = numeric.loc[numeric["scope"] == "holdout"].copy()
    merged = full.merge(holdout, on="feature", suffixes=("_full", "_holdout"))
    if merged.empty:
        return merged
    merged["same_direction"] = (
        merged["effect_direction_full"] == merged["effect_direction_holdout"]
    )
    merged["hypothesis_score"] = (
        merged["separation_auc_full"]
        + merged["separation_auc_holdout"]
        + merged["monthly_direction_rate_full"]
        + merged["monthly_direction_rate_holdout"]
        + merged["same_direction"].astype(float)
    )
    return merged.sort_values(
        ["same_direction", "hypothesis_score", "sample_size_holdout"],
        ascending=[False, False, False],
    ).reset_index(drop=True)


def scopes(df: pd.DataFrame) -> list[tuple[str, pd.DataFrame]]:
    return [("full", df), ("holdout", df.loc[df["is_holdout"]].copy())]


def monthly_direction(
    df: pd.DataFrame,
    feature: str,
    global_diff: float,
) -> dict[str, float]:
    expected = direction(global_diff)
    evaluated = 0
    same = 0
    for _, group in df.groupby(df["session_date"].dt.to_period("M"), sort=True):
        wins = group.loc[group["trade_result"] == "win", feature].to_numpy(float)
        losses = group.loc[group["trade_result"] == "loss", feature].to_numpy(float)
        if len(wins) == 0 or len(losses) == 0:
            continue
        evaluated += 1
        diff = float(np.median(wins) - np.median(losses))
        same += int(direction(diff) == expected)
    return {
        "months_evaluated": float(evaluated),
        "months_same_direction": float(same),
        "direction_rate": float(same / evaluated) if evaluated else 0.0,
    }


def category_monthly_direction(
    frame: pd.DataFrame,
    values: pd.Series,
    category: str,
) -> dict[str, float]:
    evaluated = 0
    above = 0
    months = frame["session_date"].dt.to_period("M")
    for month in sorted(months.dropna().unique()):
        month_frame = frame.loc[months == month]
        month_values = values.loc[months == month]
        category_frame = month_frame.loc[month_values == category]
        if category_frame.empty:
            continue
        evaluated += 1
        month_baseline = float((month_frame["trade_result"] == "win").mean())
        category_rate = float((category_frame["trade_result"] == "win").mean())
        above += int(category_rate > month_baseline)
    return {
        "months_evaluated": float(evaluated),
        "months_above_baseline": float(above),
        "direction_rate": float(above / evaluated) if evaluated else 0.0,
    }


def direction(value: float) -> str:
    if value > 0:
        return "higher_in_winners"
    if value < 0:
        return "higher_in_losers"
    return "flat"
