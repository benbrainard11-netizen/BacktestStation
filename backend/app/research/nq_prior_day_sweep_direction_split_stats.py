"""Table builders for prior-day sweep direction-split diagnostics."""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.research.nq_liquidity_sweep_outcomes_stats_metrics import auc, cliffs_delta

CONT = "continuation_breakout"
REV = "failed_breakout_reversal"
POST_SWEEP_FEATURES = (
    "post_5_30s_trade_events_per_second",
    "sweep_0_5s_trade_events_per_second",
    "post_5_30s_mbp_events_per_second",
)


def event_continuation_summary(events: pd.DataFrame) -> pd.DataFrame:
    rows = []
    labeled = events.loc[events["fixed_outcome_label"].isin([CONT, REV])].copy()
    for scope, frame in scopes(labeled):
        for level_type, group in frame.groupby("level_type", sort=True):
            cont = int((group["fixed_outcome_label"] == CONT).sum())
            rev = int((group["fixed_outcome_label"] == REV).sum())
            total = cont + rev
            rows.append(
                {
                    "scope": scope,
                    "level_type": level_type,
                    "sweeps": total,
                    "continuations": cont,
                    "reversals": rev,
                    "continuation_rate": cont / total if total else np.nan,
                    "failure_rate": rev / total if total else np.nan,
                }
            )
    return pd.DataFrame(rows)


def strategy_direction_summary(joined: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for scope, frame in scopes(joined):
        for level_type, group in frame.groupby("level_type", sort=True):
            rows.append(strategy_row(scope, level_type, group))
    return pd.DataFrame(rows)


def strategy_variant_direction_summary(joined: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for scope, frame in scopes(joined):
        for (level_type, variant_id), group in frame.groupby(
            ["level_type", "variant_id"],
            sort=True,
        ):
            row = strategy_row(scope, level_type, group)
            row["variant_id"] = variant_id
            rows.append(row)
    return pd.DataFrame(rows)


def categorical_effect_summary(trades: pd.DataFrame, factor: str) -> pd.DataFrame:
    rows = []
    for scope, frame in scopes(trades):
        for level_type, direction in frame.groupby("level_type", sort=True):
            baseline = float((direction["trade_result"] == "win").mean())
            values = direction[factor].fillna("missing").astype(str)
            for category, group in direction.groupby(values, sort=True):
                rows.append(
                    category_row(
                        scope,
                        level_type,
                        factor,
                        category,
                        group,
                        direction,
                        baseline,
                    )
                )
    return pd.DataFrame(rows)


def numeric_direction_summary(
    trades: pd.DataFrame,
    features: tuple[str, ...],
) -> pd.DataFrame:
    rows = []
    for scope, frame in scopes(trades):
        for level_type, direction in frame.groupby("level_type", sort=True):
            for feature in features:
                rows.extend(numeric_feature_rows(scope, level_type, direction, feature))
    return pd.DataFrame(rows)


def direction_comparison(
    event_summary: pd.DataFrame,
    strategy_summary: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    for scope in ("full", "holdout"):
        event_scope = event_summary.loc[event_summary["scope"] == scope]
        strategy_scope = strategy_summary.loc[strategy_summary["scope"] == scope]
        high_event = row_by_level(event_scope, "prior_day_high")
        low_event = row_by_level(event_scope, "prior_day_low")
        high_strategy = row_by_level(strategy_scope, "prior_day_high")
        low_strategy = row_by_level(strategy_scope, "prior_day_low")
        rows.append(
            {
                "scope": scope,
                "event_low_minus_high_continuation_rate": diff(
                    low_event,
                    high_event,
                    "continuation_rate",
                ),
                "strategy_low_minus_high_win_rate": diff(
                    low_strategy,
                    high_strategy,
                    "win_rate",
                ),
                "strategy_low_minus_high_target_rate": diff(
                    low_strategy,
                    high_strategy,
                    "target_rate",
                ),
                "strategy_low_minus_high_avg_pnl": diff(
                    low_strategy,
                    high_strategy,
                    "avg_pnl_per_attempt",
                ),
                "strategy_low_minus_high_net_pnl": diff(
                    low_strategy,
                    high_strategy,
                    "net_pnl",
                ),
            }
        )
    return pd.DataFrame(rows)


def strategy_row(scope: str, level_type: str, group: pd.DataFrame) -> dict[str, object]:
    filled = group.loc[group["status"] == "filled"]
    win_loss = filled.loc[filled["trade_result"].isin(["win", "loss"])]
    pnl = pd.to_numeric(group["pnl_num"], errors="coerce").fillna(0.0)
    exit_reason = filled.get("exit_reason", pd.Series("", index=filled.index))
    target_exits = int((exit_reason == "target").sum())
    stop_exits = int((exit_reason == "stop").sum())
    forced_flat_exits = int((exit_reason == "forced_flat").sum())
    return {
        "scope": scope,
        "level_type": level_type,
        "attempts": int(len(group)),
        "filled_trades": int(len(filled)),
        "skips": int((group["status"] == "skipped").sum()),
        "target_exits": target_exits,
        "target_rate": target_exits / len(filled) if len(filled) else np.nan,
        "stop_exits": stop_exits,
        "stop_rate": stop_exits / len(filled) if len(filled) else np.nan,
        "forced_flat_exits": forced_flat_exits,
        "forced_flat_rate": forced_flat_exits / len(filled) if len(filled) else np.nan,
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
    level_type: str,
    factor: str,
    category: str,
    group: pd.DataFrame,
    direction: pd.DataFrame,
    baseline: float,
) -> dict[str, object]:
    wins = int((group["trade_result"] == "win").sum())
    losses = int((group["trade_result"] == "loss").sum())
    trades_count = wins + losses
    win_rate = wins / trades_count if trades_count else np.nan
    monthly = category_monthly_direction(direction, category, factor)
    return {
        "scope": scope,
        "level_type": level_type,
        "factor": factor,
        "category": category,
        "trades": trades_count,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "direction_baseline_win_rate": baseline,
        "win_rate_delta": win_rate - baseline,
        "net_pnl": float(group["pnl_num"].sum()),
        "avg_pnl": float(group["pnl_num"].mean()),
        "months_evaluated": int(monthly["months_evaluated"]),
        "months_above_direction_baseline": int(monthly["months_above_baseline"]),
        "monthly_direction_rate": float(monthly["direction_rate"]),
    }


def numeric_feature_rows(
    scope: str,
    level_type: str,
    direction: pd.DataFrame,
    feature: str,
) -> list[dict[str, object]]:
    if feature not in direction.columns:
        return []
    frame = direction.loc[direction[feature].notna()]
    wins = frame.loc[frame["trade_result"] == "win", feature].to_numpy(float)
    losses = frame.loc[frame["trade_result"] == "loss", feature].to_numpy(float)
    if len(wins) == 0 or len(losses) == 0:
        return []
    median_diff = float(np.median(wins) - np.median(losses))
    feature_auc = auc(wins, losses)
    return [
        {
            "scope": scope,
            "level_type": level_type,
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
        }
    ]


def category_monthly_direction(
    direction: pd.DataFrame,
    category: str,
    factor: str,
) -> dict[str, float]:
    values = direction[factor].fillna("missing").astype(str)
    evaluated = 0
    above = 0
    months = direction["session_date"].dt.to_period("M")
    for month in sorted(months.dropna().unique()):
        month_frame = direction.loc[months == month]
        month_values = values.loc[months == month]
        category_frame = month_frame.loc[month_values == category]
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


def scopes(df: pd.DataFrame) -> list[tuple[str, pd.DataFrame]]:
    return [("full", df), ("holdout", df.loc[df["is_holdout"]].copy())]


def row_by_level(df: pd.DataFrame, level_type: str) -> pd.Series | None:
    row = df.loc[df["level_type"] == level_type]
    return None if row.empty else row.iloc[0]


def diff(left: pd.Series | None, right: pd.Series | None, column: str) -> float | None:
    if left is None or right is None:
        return None
    return float(left[column]) - float(right[column])
