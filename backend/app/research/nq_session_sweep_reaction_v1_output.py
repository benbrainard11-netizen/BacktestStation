"""Output shaping and summary metrics for NQ Session Sweep Reaction V1."""

from __future__ import annotations

import datetime as dt
from dataclasses import asdict

import pandas as pd

from app.research.nq_session_sweep_reaction_v1_types import (
    SimulatedTrade,
    SweepEvent,
    SweepReactionConfig,
    TradePlan,
)
from app.research.nq_session_sweep_reaction_v1_utils import ET


def trades_frame(trades: list[SimulatedTrade]) -> pd.DataFrame:
    rows = [asdict(t) for t in trades]
    out = pd.DataFrame(rows)
    if out.empty:
        return pd.DataFrame(
            columns=[
                "trade_id",
                "session_date",
                "side",
                "entry_ts",
                "exit_ts",
                "entry_price",
                "exit_price",
                "pnl",
                "r_multiple",
                "exit_reason",
            ]
        )
    out["hold_minutes"] = (
        pd.to_datetime(out["exit_ts"], utc=True)
        - pd.to_datetime(out["entry_ts"], utc=True)
    ).dt.total_seconds() / 60.0
    return out


def equity_frame(
    trades: list[SimulatedTrade],
    initial_equity: float,
) -> pd.DataFrame:
    equity = initial_equity
    peak = initial_equity
    rows = [
        {
            "ts": None,
            "equity": equity,
            "drawdown": 0.0,
            "event": "start",
        }
    ]
    for trade in sorted(trades, key=lambda t: t.exit_ts):
        equity += trade.pnl
        peak = max(peak, equity)
        rows.append(
            {
                "ts": trade.exit_ts,
                "equity": float(equity),
                "drawdown": float(equity - peak),
                "event": trade.trade_id,
            }
        )
    return pd.DataFrame(rows)


def session_row(
    plan: TradePlan,
    status: str,
    skip_reason: str,
    sweep: SweepEvent | None = None,
    *,
    confirmation: float | None = None,
    risk_pts: float | None = None,
    trade_id: str | None = None,
) -> dict[str, object]:
    return {
        "session_date": plan.session_date,
        "next_session_date": plan.next_session_date,
        "status": status,
        "skip_reason": skip_reason,
        "trade_id": trade_id,
        "armed_side": plan.armed_side,
        "trade_side": plan.trade_side,
        "anchor_high": plan.anchor_high,
        "anchor_low": plan.anchor_low,
        "anchor_range": plan.anchor_range,
        "session_close_position": plan.session_close_position,
        "session_close_bias": plan.session_close_bias,
        "prior20_median_range": plan.prior20_median_range,
        "first_sweep_side": sweep.side if sweep else None,
        "first_sweep_ts": sweep.ts if sweep else None,
        "first_sweep_price": sweep.price if sweep else None,
        "post_sweep_30s_mean_imbalance": confirmation,
        "risk_pts": risk_pts,
    }


def session_skip_row(
    config: SweepReactionConfig,
    period,
    reason: str,
    **extra,
) -> dict[str, object]:
    label_date = period.end_utc.astimezone(ET).date().isoformat()
    session_date = extra.pop("session_date", label_date)
    return {
        "session_date": session_date,
        "next_session_date": None,
        "status": "skipped",
        "skip_reason": reason,
        "trade_id": None,
        "symbol": config.symbol,
        **extra,
    }


def replay_row(
    *,
    event_type: str,
    session_date: str,
    next_session_date: str,
    ts: dt.datetime,
    price: float | None,
    plan: TradePlan,
    note: str,
    trade_id: str | None = None,
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    row = {
        "session_date": session_date,
        "next_session_date": next_session_date,
        "trade_id": trade_id,
        "event_type": event_type,
        "ts": ts,
        "price": price,
        "note": note,
        "armed_side": plan.armed_side,
        "trade_side": plan.trade_side,
        "anchor_high": plan.anchor_high,
        "anchor_low": plan.anchor_low,
        "anchor_mid": (plan.anchor_high + plan.anchor_low) / 2,
    }
    if extra:
        row.update(extra)
    return row


def simulated_trade(
    *,
    trade_id: str,
    plan: TradePlan,
    sweep: SweepEvent,
    qty: int,
    entry_ts: dt.datetime,
    exit_ts: dt.datetime,
    entry_price: float,
    exit_price: float,
    stop_price: float,
    target_price: float,
    risk_pts: float,
    pnl: float,
    r_multiple: float,
    exit_reason: str,
    fill_confidence: str,
    sweep_extreme: float,
    reclaim_bar_start: dt.datetime,
    reclaim_bar_end: dt.datetime,
    confirmation_end: dt.datetime,
    confirmation: float,
) -> SimulatedTrade:
    return SimulatedTrade(
        trade_id=trade_id,
        session_date=plan.session_date,
        next_session_date=plan.next_session_date,
        side=plan.trade_side,
        qty=qty,
        entry_ts=entry_ts,
        exit_ts=exit_ts,
        entry_price=entry_price,
        exit_price=exit_price,
        stop_price=stop_price,
        target_price=target_price,
        risk_pts=risk_pts,
        pnl=pnl,
        r_multiple=r_multiple,
        exit_reason=exit_reason,
        fill_confidence=fill_confidence,
        sweep_side=sweep.side,
        sweep_ts=sweep.ts,
        sweep_price=sweep.price,
        sweep_extreme=sweep_extreme,
        reclaim_bar_start=reclaim_bar_start,
        reclaim_bar_end=reclaim_bar_end,
        confirmation_end=confirmation_end,
        post_sweep_30s_mean_imbalance=confirmation,
        anchor_high=plan.anchor_high,
        anchor_low=plan.anchor_low,
        anchor_range=plan.anchor_range,
        session_close_position=plan.session_close_position,
        session_close_bias=plan.session_close_bias,
        prior20_median_range=plan.prior20_median_range,
    )


def summarize_results(
    *,
    trades_df: pd.DataFrame,
    sessions_df: pd.DataFrame,
    equity_df: pd.DataFrame,
    config: SweepReactionConfig,
    start: dt.date,
    end: dt.date,
) -> dict[str, object]:
    trade_count = int(len(trades_df))
    net_pnl = sum_col(trades_df, "pnl")
    net_r = sum_col(trades_df, "r_multiple")
    wins = trades_df.loc[trades_df["pnl"] > 0] if not trades_df.empty else trades_df
    losses = trades_df.loc[trades_df["pnl"] < 0] if not trades_df.empty else trades_df
    gross_profit = sum_col(wins, "pnl")
    gross_loss = abs(sum_col(losses, "pnl"))
    skip_counts = (
        sessions_df["status"].value_counts(dropna=False).to_dict()
        if "status" in sessions_df.columns
        else {}
    )
    reason_counts = (
        sessions_df["skip_reason"].value_counts(dropna=False).to_dict()
        if "skip_reason" in sessions_df.columns
        else {}
    )
    return {
        "strategy": "nq_session_sweep_reaction_v1",
        "symbol": config.symbol,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "sessions": int(len(sessions_df)),
        "trade_count": trade_count,
        "entry_count": trade_count,
        "net_pnl": float(net_pnl),
        "net_r": float(net_r),
        "win_rate": float(len(wins) / trade_count) if trade_count else 0.0,
        "avg_r": float(net_r / trade_count) if trade_count else 0.0,
        "median_r": median_col(trades_df, "r_multiple"),
        "profit_factor": float(gross_profit / gross_loss) if gross_loss > 0 else None,
        "max_drawdown": min_col(equity_df, "drawdown"),
        "avg_hold_minutes": mean_col(trades_df, "hold_minutes"),
        "long_trades": count_equal(trades_df, "side", "long"),
        "short_trades": count_equal(trades_df, "side", "short"),
        "target_exits": count_equal(trades_df, "exit_reason", "target"),
        "stop_exits": count_equal(trades_df, "exit_reason", "stop"),
        "forced_flat_exits": count_equal(trades_df, "exit_reason", "forced_flat"),
        "ambiguous_fill_count": count_equal(
            trades_df,
            "fill_confidence",
            "ambiguous",
        ),
        "status_counts": {str(k): int(v) for k, v in skip_counts.items()},
        "skip_reason_counts": {str(k): int(v) for k, v in reason_counts.items()},
        "config": asdict(config),
    }


def sum_col(df: pd.DataFrame, column: str) -> float:
    if df.empty or column not in df.columns:
        return 0.0
    return float(pd.to_numeric(df[column], errors="coerce").fillna(0).sum())


def mean_col(df: pd.DataFrame, column: str) -> float | None:
    if df.empty or column not in df.columns:
        return None
    value = pd.to_numeric(df[column], errors="coerce").mean()
    return None if pd.isna(value) else float(value)


def median_col(df: pd.DataFrame, column: str) -> float | None:
    if df.empty or column not in df.columns:
        return None
    value = pd.to_numeric(df[column], errors="coerce").median()
    return None if pd.isna(value) else float(value)


def min_col(df: pd.DataFrame, column: str) -> float:
    if df.empty or column not in df.columns:
        return 0.0
    value = pd.to_numeric(df[column], errors="coerce").min()
    return 0.0 if pd.isna(value) else float(value)


def count_equal(df: pd.DataFrame, column: str, value: str) -> int:
    if df.empty or column not in df.columns:
        return 0
    return int((df[column] == value).sum())
