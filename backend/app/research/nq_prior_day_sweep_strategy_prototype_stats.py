"""Summary and walk-forward metrics for the prior-day sweep prototype."""

from __future__ import annotations

from typing import Any

import pandas as pd

from app.research.nq_prior_day_sweep_strategy_prototype_types import (
    PriorDaySweepPrototypeConfig,
)


def variant_summary(
    attempts: pd.DataFrame,
    config: PriorDaySweepPrototypeConfig,
) -> pd.DataFrame:
    rows = []
    for variant_id, group in attempts.groupby("variant_id", sort=True):
        trades = group.loc[group["status"] == "filled"].copy()
        pnl = pd.to_numeric(group.get("pnl"), errors="coerce").fillna(0.0)
        trade_pnl = pd.to_numeric(trades.get("pnl"), errors="coerce").fillna(0.0)
        rows.append(_variant_row(variant_id, group, trades, pnl, trade_pnl, config))
    return pd.DataFrame(rows).sort_values(
        ["avg_pnl_per_signal", "net_pnl", "trades"],
        ascending=[False, False, False],
    ).reset_index(drop=True)


def monthly_summary(attempts: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (variant_id, month), group in attempts.groupby(["variant_id", "month"], sort=True):
        pnl = pd.to_numeric(group.get("pnl"), errors="coerce").fillna(0.0)
        trades = group.loc[group["status"] == "filled"]
        rows.append(
            {
                "variant_id": variant_id,
                "month": month,
                "signals": int(len(group)),
                "trades": int(len(trades)),
                "net_pnl": float(pnl.sum()),
                "avg_pnl_per_signal": float(pnl.sum() / len(group)) if len(group) else 0.0,
                "avg_pnl_per_trade": float(pnl.sum() / len(trades)) if len(trades) else 0.0,
            }
        )
    return pd.DataFrame(rows)


def walk_forward_summary(
    attempts: pd.DataFrame,
    config: PriorDaySweepPrototypeConfig,
) -> pd.DataFrame:
    months = sorted(attempts["month"].dropna().unique())
    rows = []
    for variant_id, group in attempts.groupby("variant_id", sort=True):
        for idx in range(config.walk_forward_min_train_months, len(months)):
            train = group.loc[group["month"].isin(months[:idx])]
            test = group.loc[group["month"] == months[idx]]
            rows.append(_walk_row(variant_id, months[idx], train, test))
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return out.sort_values(["variant_id", "test_month"]).reset_index(drop=True)


def study_summary(
    qualified: pd.DataFrame,
    attempts: pd.DataFrame,
    summary: pd.DataFrame,
    walk: pd.DataFrame,
    config: PriorDaySweepPrototypeConfig,
) -> dict[str, object]:
    return {
        "symbol": config.symbol,
        "sequencing_source": config.sequencing_source,
        "qualified_sweeps": int(len(qualified)),
        "variants_tested": int(summary["variant_id"].nunique()) if not summary.empty else 0,
        "attempt_rows": int(len(attempts)),
        "top_by_avg_pnl_per_signal": _top(summary),
        "walk_forward_positive_test_fold_rate": _positive_fold_rate(walk),
        "costs": {
            "commission_per_contract_per_side": config.commission_per_contract,
            "slippage_ticks_each_side": config.slippage_ticks,
            "qty": config.qty,
            "contract_value_per_point": config.contract_value,
        },
        "context_gate": (
            "prior-day high/low sweep and at least 2 of: overnight location aligned, "
            "RTH gap aligned, opening-drive timing"
        ),
    }


def _variant_row(
    variant_id: str,
    group: pd.DataFrame,
    trades: pd.DataFrame,
    pnl: pd.Series,
    trade_pnl: pd.Series,
    config: PriorDaySweepPrototypeConfig,
) -> dict[str, object]:
    wins = trade_pnl.loc[trade_pnl > 0]
    losses = trade_pnl.loc[trade_pnl < 0]
    return {
        "variant_id": variant_id,
        "entry_method": group["entry_method"].iloc[0],
        "stop_method": group["stop_method"].iloc[0],
        "target_method": group["target_method"].iloc[0],
        "signals": int(len(group)),
        "trades": int(len(trades)),
        "skips": int((group["status"] == "skipped").sum()),
        "net_pnl": float(pnl.sum()),
        "avg_pnl_per_signal": float(pnl.sum() / len(group)) if len(group) else 0.0,
        "avg_pnl_per_trade": float(trade_pnl.mean()) if len(trades) else 0.0,
        "win_rate": float((trade_pnl > 0).mean()) if len(trades) else 0.0,
        "profit_factor": _profit_factor(wins, losses),
        "avg_r": _mean_col(trades, "r_multiple"),
        "max_drawdown": _max_drawdown(trade_pnl, config.initial_equity),
    }


def _walk_row(
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
        "train_trades": int((train["status"] == "filled").sum()) if len(train) else 0,
        "test_trades": int((test["status"] == "filled").sum()) if len(test) else 0,
        "train_avg_pnl_per_signal": float(train_pnl.sum() / len(train)) if len(train) else 0.0,
        "test_avg_pnl_per_signal": float(test_pnl.sum() / len(test)) if len(test) else 0.0,
        "train_positive": bool(train_pnl.sum() > 0),
        "test_positive": bool(test_pnl.sum() > 0),
        "test_net_pnl": float(test_pnl.sum()),
    }


def _profit_factor(wins: pd.Series, losses: pd.Series) -> float | None:
    gross_profit = float(wins.sum())
    gross_loss = abs(float(losses.sum()))
    if gross_loss == 0:
        return None if gross_profit == 0 else float("inf")
    return gross_profit / gross_loss


def _mean_col(df: pd.DataFrame, col: str) -> float:
    if df.empty or col not in df.columns:
        return 0.0
    return float(pd.to_numeric(df[col], errors="coerce").mean())


def _max_drawdown(pnls: pd.Series, initial_equity: float) -> float:
    equity = initial_equity
    peak = initial_equity
    max_dd = 0.0
    for pnl in pnls:
        equity += float(pnl)
        peak = max(peak, equity)
        max_dd = min(max_dd, equity - peak)
    return float(max_dd)


def _top(df: pd.DataFrame) -> dict[str, object] | None:
    if df.empty:
        return None
    return _json_safe(df.iloc[0].to_dict())


def _positive_fold_rate(walk: pd.DataFrame) -> float | None:
    if walk.empty:
        return None
    return float(walk["test_positive"].mean())


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value
