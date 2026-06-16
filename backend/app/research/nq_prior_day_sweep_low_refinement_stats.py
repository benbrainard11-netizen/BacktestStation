"""Table builders for prior-day low sweep refinement diagnostics."""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.research.nq_liquidity_sweep_outcomes_stats_metrics import auc, cliffs_delta

CONT = "continuation_breakout"
REV = "failed_breakout_reversal"

CATEGORICAL_FACTORS = (
    "variant_id",
    "overnight_range_location_vs_sweep",
    "overnight_range_location",
    "overnight_trend_vs_sweep",
    "time_of_day_bucket",
    "opening_drive_aligned",
    "rth_gap_vs_sweep",
    "rth_gap_bucket",
    "pre60_dir_aggr_ratio_band",
    "reclaimed_0_30s",
)

NUMERIC_FEATURES = (
    "post_5_30s_trade_events_per_second",
    "sweep_0_5s_trade_events_per_second",
    "post_5_30s_mbp_events_per_second",
    "sweep_0_5s_mbp_events_per_second",
    "sweep_distance_pts",
    "time_to_reclaim_seconds",
    "pre_60s_directional_aggressive_trade_ratio",
    "directional_overnight_trend_pts",
    "directional_rth_gap_pts",
    "sweep_minutes_after_rth_open",
)


def event_continuation(events: pd.DataFrame) -> pd.DataFrame:
    rows = []
    labeled = events.loc[events["fixed_outcome_label"].isin([CONT, REV])]
    for scope, frame in scopes(labeled):
        cont = int((frame["fixed_outcome_label"] == CONT).sum())
        rev = int((frame["fixed_outcome_label"] == REV).sum())
        total = cont + rev
        rows.append(
            {
                "scope": scope,
                "sweeps": total,
                "continuations": cont,
                "reversals": rev,
                "continuation_rate": cont / total if total else np.nan,
            }
        )
    return pd.DataFrame(rows)


def strategy_summary(attempts: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame([strategy_row(scope, frame) for scope, frame in scopes(attempts)])


def variant_summary(attempts: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for scope, frame in scopes(attempts):
        for variant_id, group in frame.groupby("variant_id", sort=True):
            row = strategy_row(scope, group)
            row["variant_id"] = variant_id
            rows.append(row)
    return pd.DataFrame(rows)


def categorical_summary(trades: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for scope, frame in scopes(trades):
        baseline = float((frame["trade_result"] == "win").mean()) if len(frame) else np.nan
        for factor in CATEGORICAL_FACTORS:
            if factor not in frame.columns:
                continue
            values = frame[factor].fillna("missing").astype(str)
            for category, group in frame.groupby(values, sort=True):
                rows.append(category_row(scope, frame, factor, category, group, baseline))
    return pd.DataFrame(rows)


def numeric_summary(trades: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for scope, frame in scopes(trades):
        for feature in NUMERIC_FEATURES:
            rows.extend(numeric_rows(scope, frame, feature))
    return pd.DataFrame(rows)


def context_validation(categorical: pd.DataFrame) -> pd.DataFrame:
    in_sample = categorical.loc[categorical["scope"] == "in_sample"]
    holdout = categorical.loc[categorical["scope"] == "holdout"]
    merged = in_sample.merge(holdout, on=["factor", "category"], suffixes=("_is", "_ho"))
    if merged.empty:
        return merged
    merged["same_improving_direction"] = (
        (merged["win_rate_delta_is"] > 0) & (merged["win_rate_delta_ho"] > 0)
    )
    merged["verdict"] = merged.apply(context_verdict, axis=1)
    verdict_rank = {
        "survived_holdout": 0,
        "holdout_only_hint": 1,
        "weak_or_negative": 2,
        "weakened_or_reversed": 3,
        "too_sparse": 4,
    }
    merged["verdict_rank"] = merged["verdict"].map(verdict_rank).fillna(9)
    return merged.sort_values(
        ["verdict_rank", "win_rate_delta_ho", "trades_ho"],
        ascending=[True, False, False],
    ).reset_index(drop=True)


def numeric_validation(numeric: pd.DataFrame) -> pd.DataFrame:
    in_sample = numeric.loc[numeric["scope"] == "in_sample"]
    holdout = numeric.loc[numeric["scope"] == "holdout"]
    merged = in_sample.merge(holdout, on="feature", suffixes=("_is", "_ho"))
    if merged.empty:
        return merged
    merged["same_direction"] = merged["effect_direction_is"] == merged["effect_direction_ho"]
    merged["verdict"] = merged.apply(numeric_verdict, axis=1)
    return merged.sort_values(
        ["same_direction", "separation_auc_ho", "sample_size_ho"],
        ascending=[False, False, False],
    ).reset_index(drop=True)


def monthly_summary(attempts: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    rows = []
    labeled = events.loc[events["fixed_outcome_label"].isin([CONT, REV])]
    for month, group in attempts.groupby("month", sort=True):
        event_month = labeled.loc[labeled["month"] == month]
        strategy = strategy_row("month", group)
        cont = int((event_month["fixed_outcome_label"] == CONT).sum())
        rev = int((event_month["fixed_outcome_label"] == REV).sum())
        total = cont + rev
        rows.append(
            {
                "month": month,
                **{k: v for k, v in strategy.items() if k != "scope"},
                "labeled_sweeps": total,
                "event_continuation_rate": cont / total if total else np.nan,
            }
        )
    return pd.DataFrame(rows)


def strategy_row(scope: str, frame: pd.DataFrame) -> dict[str, object]:
    filled = frame.loc[frame["status"] == "filled"]
    win_loss = filled.loc[filled["trade_result"].isin(["win", "loss"])]
    pnl = pd.to_numeric(frame["pnl_num"], errors="coerce").fillna(0.0)
    exit_reason = filled.get("exit_reason", pd.Series("", index=filled.index))
    target = int((exit_reason == "target").sum())
    stop = int((exit_reason == "stop").sum())
    forced = int((exit_reason == "forced_flat").sum())
    return {
        "scope": scope,
        "attempts": int(len(frame)),
        "filled_trades": int(len(filled)),
        "skips": int((frame["status"] == "skipped").sum()),
        "target_exits": target,
        "target_rate": target / len(filled) if len(filled) else np.nan,
        "stop_exits": stop,
        "stop_rate": stop / len(filled) if len(filled) else np.nan,
        "forced_flat_exits": forced,
        "forced_flat_rate": forced / len(filled) if len(filled) else np.nan,
        "wins": int((win_loss["trade_result"] == "win").sum()),
        "losses": int((win_loss["trade_result"] == "loss").sum()),
        "win_rate": float((win_loss["trade_result"] == "win").mean())
        if len(win_loss)
        else np.nan,
        "net_pnl": float(pnl.sum()),
        "avg_pnl_per_attempt": float(pnl.mean()),
    }


def category_row(
    scope: str,
    frame: pd.DataFrame,
    factor: str,
    category: str,
    group: pd.DataFrame,
    baseline: float,
) -> dict[str, object]:
    wins = int((group["trade_result"] == "win").sum())
    losses = int((group["trade_result"] == "loss").sum())
    total = wins + losses
    monthly = category_monthly_direction(frame, factor, category)
    return {
        "scope": scope,
        "factor": factor,
        "category": category,
        "trades": total,
        "wins": wins,
        "losses": losses,
        "win_rate": wins / total if total else np.nan,
        "baseline_win_rate": baseline,
        "win_rate_delta": (wins / total) - baseline if total else np.nan,
        "net_pnl": float(group["pnl_num"].sum()),
        "avg_pnl": float(group["pnl_num"].mean()),
        "months_evaluated": int(monthly["months_evaluated"]),
        "months_above_baseline": int(monthly["months_above_baseline"]),
        "monthly_direction_rate": float(monthly["direction_rate"]),
    }


def numeric_rows(scope: str, frame: pd.DataFrame, feature: str) -> list[dict[str, object]]:
    if feature not in frame.columns:
        return []
    feature_frame = frame.loc[frame[feature].notna()]
    wins = feature_frame.loc[feature_frame["trade_result"] == "win", feature].to_numpy(float)
    losses = feature_frame.loc[feature_frame["trade_result"] == "loss", feature].to_numpy(float)
    if len(wins) == 0 or len(losses) == 0:
        return []
    median_diff = float(np.median(wins) - np.median(losses))
    feature_auc = auc(wins, losses)
    return [
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
        }
    ]


def category_monthly_direction(
    frame: pd.DataFrame,
    factor: str,
    category: str,
) -> dict[str, float]:
    months = frame["session_date"].dt.to_period("M")
    values = frame[factor].fillna("missing").astype(str)
    evaluated = 0
    above = 0
    for month in sorted(months.dropna().unique()):
        month_frame = frame.loc[months == month]
        category_frame = month_frame.loc[values.loc[months == month] == category]
        if category_frame.empty:
            continue
        evaluated += 1
        baseline = float((month_frame["trade_result"] == "win").mean())
        category_rate = float((category_frame["trade_result"] == "win").mean())
        above += int(category_rate > baseline)
    return {
        "months_evaluated": float(evaluated),
        "months_above_baseline": float(above),
        "direction_rate": float(above / evaluated) if evaluated else 0.0,
    }


def context_verdict(row: pd.Series) -> str:
    if int(row["trades_is"]) < 10 or int(row["trades_ho"]) < 10:
        return "too_sparse"
    if row["win_rate_delta_is"] > 0 and row["win_rate_delta_ho"] > 0 and row["net_pnl_ho"] > 0:
        return "survived_holdout"
    if row["win_rate_delta_is"] > 0 and row["win_rate_delta_ho"] <= 0:
        return "weakened_or_reversed"
    if row["win_rate_delta_is"] <= 0 and row["win_rate_delta_ho"] > 0:
        return "holdout_only_hint"
    return "weak_or_negative"


def numeric_verdict(row: pd.Series) -> str:
    if int(row["sample_size_ho"]) < 20:
        return "too_sparse"
    if row["same_direction"]:
        return "same_direction_hypothesis"
    return "reversed_or_flat"


def scopes(df: pd.DataFrame) -> list[tuple[str, pd.DataFrame]]:
    return [
        ("full", df),
        ("in_sample", df.loc[~df["is_holdout"]].copy()),
        ("holdout", df.loc[df["is_holdout"]].copy()),
    ]


def direction(value: float) -> str:
    if value > 0:
        return "higher_in_winners"
    if value < 0:
        return "higher_in_losers"
    return "flat"
