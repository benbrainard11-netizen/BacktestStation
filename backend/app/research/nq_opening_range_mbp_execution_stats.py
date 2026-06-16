"""Summary tables for the middle-third OR MBP execution study."""

from __future__ import annotations

from typing import Any

import pandas as pd

from app.research.nq_opening_range_mbp_execution_types import (
    OpeningRangeMbpExecutionConfig,
)

CONTINUATION = "continuation_breakout"
REVERSAL = "failed_breakout_reversal"


def outcome_summary(events: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for scope, frame in scopes(events):
        rows.append(outcome_row(scope, "all", "all", frame))
        for side, group in frame.groupby("first_break_side", sort=True):
            rows.append(outcome_row(scope, "first_break_side", str(side), group))
    return pd.DataFrame(rows)


def variant_summary(attempts: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for variant_id, group in attempts.groupby("variant_id", sort=True):
        rows.append(variant_row("full", variant_id, group))
        rows.append(variant_row("in_sample", variant_id, group.loc[~group["is_holdout"]]))
        rows.append(variant_row("holdout", variant_id, group.loc[group["is_holdout"]]))
    return pd.DataFrame(rows)


def monthly_summary(attempts: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (variant_id, month), group in attempts.groupby(["variant_id", "month"], sort=True):
        rows.append(variant_row("month", variant_id, group) | {"month": month})
    return pd.DataFrame(rows)


def walk_forward_summary(
    attempts: pd.DataFrame,
    config: OpeningRangeMbpExecutionConfig,
) -> pd.DataFrame:
    rows = []
    months = sorted(attempts["month"].dropna().astype(str).unique())
    for variant_id, group in attempts.groupby("variant_id", sort=True):
        for idx in range(config.walk_forward_min_train_months, len(months)):
            train = group.loc[group["month"].isin(months[:idx])]
            test = group.loc[group["month"] == months[idx]]
            rows.append(walk_row(variant_id, months[idx], train, test))
    return pd.DataFrame(rows)


def stability_summary(
    variants: pd.DataFrame,
    walk_forward: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    full = variants.loc[variants["scope"] == "full"].set_index("variant_id")
    holdout = variants.loc[variants["scope"] == "holdout"].set_index("variant_id")
    for variant_id in sorted(full.index):
        if walk_forward.empty or "variant_id" not in walk_forward.columns:
            wf = pd.DataFrame()
        else:
            wf = walk_forward.loc[walk_forward["variant_id"] == variant_id]
        test_folds = len(wf)
        positive_folds = int((wf["test_net_pnl"] > 0).sum()) if test_folds else 0
        rows.append(
            {
                "variant_id": variant_id,
                "full_signals": int(full.loc[variant_id, "signals"]),
                "full_trades": int(full.loc[variant_id, "trades"]),
                "full_net_pnl": float(full.loc[variant_id, "net_pnl"]),
                "full_avg_pnl_per_signal": float(full.loc[variant_id, "avg_pnl_per_signal"]),
                "holdout_signals": int(holdout.loc[variant_id, "signals"]),
                "holdout_trades": int(holdout.loc[variant_id, "trades"]),
                "holdout_net_pnl": float(holdout.loc[variant_id, "net_pnl"]),
                "holdout_avg_pnl_per_signal": float(
                    holdout.loc[variant_id, "avg_pnl_per_signal"]
                ),
                "walk_forward_folds": test_folds,
                "walk_forward_positive_folds": positive_folds,
                "walk_forward_positive_fold_rate": positive_folds / test_folds
                if test_folds
                else 0.0,
                "walk_forward_net_pnl": float(wf["test_net_pnl"].sum())
                if test_folds
                else 0.0,
                "read": stability_read(full.loc[variant_id], holdout.loc[variant_id], wf),
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["read", "holdout_avg_pnl_per_signal", "walk_forward_positive_fold_rate"],
        ascending=[True, False, False],
    )


def study_summary(
    events: pd.DataFrame,
    attempts: pd.DataFrame,
    outcomes: pd.DataFrame,
    stability: pd.DataFrame,
    config: OpeningRangeMbpExecutionConfig,
) -> dict[str, object]:
    return {
        "symbol": config.symbol,
        "context_bucket": config.context_bucket,
        "qualified_middle_third_sessions": int(len(events)),
        "mbp_labeled_events": int(events["outcome_label"].isin([CONTINUATION, REVERSAL]).sum())
        if not events.empty
        else 0,
        "attempt_rows": int(len(attempts)),
        "baseline_outcomes": outcomes.to_dict("records"),
        "best_stability_rows": stability.to_dict("records"),
        "execution_assumptions": {
            "entry_styles": ["immediate_break", "first_retest", "confirmation_30s"],
            "stop": "opposite side of opening range",
            "target": "one opening-range width beyond first break",
            "confirmation_seconds": config.confirmation_seconds,
            "retest_deadline_minutes": config.retest_deadline_minutes,
            "slippage_ticks_each_side": config.slippage_ticks,
            "commission_per_contract_per_side": config.commission_per_contract,
        },
    }


def outcome_row(scope: str, factor: str, category: str, frame: pd.DataFrame) -> dict[str, object]:
    labeled = frame.loc[frame["outcome_label"].isin([CONTINUATION, REVERSAL])]
    continuations = int((labeled["outcome_label"] == CONTINUATION).sum())
    reversals = int((labeled["outcome_label"] == REVERSAL).sum())
    return {
        "scope": scope,
        "factor": factor,
        "category": category,
        "events": int(len(frame)),
        "labeled_count": int(len(labeled)),
        "continuations": continuations,
        "reversals": reversals,
        "ambiguous": int((frame["outcome_label"] == "ambiguous").sum()),
        "no_break": int((frame["outcome_label"] == "no_break").sum()),
        "continuation_rate": continuations / len(labeled) if len(labeled) else None,
    }


def variant_row(scope: str, variant_id: str, group: pd.DataFrame) -> dict[str, object]:
    trades = group.loc[group["status"] == "filled"]
    pnl = pd.to_numeric(group.get("pnl"), errors="coerce").fillna(0.0)
    trade_pnl = pd.to_numeric(trades.get("pnl"), errors="coerce").fillna(0.0)
    wins = trade_pnl.loc[trade_pnl > 0]
    losses = trade_pnl.loc[trade_pnl < 0]
    return {
        "scope": scope,
        "variant_id": variant_id,
        "entry_style": variant_id,
        "signals": int(len(group)),
        "trades": int(len(trades)),
        "skips": int((group["status"] == "skipped").sum()) if len(group) else 0,
        "net_pnl": float(pnl.sum()),
        "avg_pnl_per_signal": float(pnl.sum() / len(group)) if len(group) else 0.0,
        "avg_pnl_per_trade": float(trade_pnl.mean()) if len(trades) else 0.0,
        "win_rate": float((trade_pnl > 0).mean()) if len(trades) else 0.0,
        "profit_factor": profit_factor(wins, losses),
    }


def walk_row(
    variant_id: str,
    test_month: str,
    train: pd.DataFrame,
    test: pd.DataFrame,
) -> dict[str, object]:
    train_pnl = pd.to_numeric(train.get("pnl"), errors="coerce").fillna(0.0)
    test_pnl = pd.to_numeric(test.get("pnl"), errors="coerce").fillna(0.0)
    return {
        "variant_id": variant_id,
        "test_month": test_month,
        "train_signals": int(len(train)),
        "test_signals": int(len(test)),
        "train_net_pnl": float(train_pnl.sum()),
        "test_net_pnl": float(test_pnl.sum()),
        "train_avg_pnl_per_signal": float(train_pnl.sum() / len(train)) if len(train) else 0.0,
        "test_avg_pnl_per_signal": float(test_pnl.sum() / len(test)) if len(test) else 0.0,
        "test_positive": bool(test_pnl.sum() > 0),
    }


def stability_read(full: pd.Series, holdout: pd.Series, walk_forward: pd.DataFrame) -> str:
    if int(full["trades"]) < 20 or int(holdout["trades"]) < 5 or len(walk_forward) < 3:
        return "too_sparse"
    positive_rate = float((walk_forward["test_net_pnl"] > 0).mean())
    if float(holdout["avg_pnl_per_signal"]) > 0 and positive_rate >= 0.60:
        return "stable_positive"
    if float(holdout["avg_pnl_per_signal"]) < 0 and positive_rate <= 0.40:
        return "stable_negative"
    return "mixed"


def scopes(events: pd.DataFrame) -> list[tuple[str, pd.DataFrame]]:
    return [
        ("full", events.copy()),
        ("in_sample", events.loc[~events["is_holdout"]].copy()),
        ("holdout", events.loc[events["is_holdout"]].copy()),
    ]


def profit_factor(wins: pd.Series, losses: pd.Series) -> float | None:
    gross_profit = float(wins.sum())
    gross_loss = abs(float(losses.sum()))
    if gross_loss == 0:
        return None if gross_profit == 0 else float("inf")
    return gross_profit / gross_loss


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value
