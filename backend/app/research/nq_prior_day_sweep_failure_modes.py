"""Failure-mode diagnostics for prior-day sweep strategy attempts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from app.research.nq_prior_day_sweep_failure_mode_stats import (
    NUMERIC_FEATURES,
    categorical_summary,
    hypotheses,
    numeric_summary,
    variant_summary,
)


def run_prior_day_sweep_failure_mode_analysis(
    *,
    attempts_path: Path,
    events_path: Path,
    holdout_start: str = "2026-02-01",
    holdout_end: str = "2026-05-24",
) -> dict[str, object]:
    attempts = pd.read_csv(attempts_path)
    events = pd.read_csv(events_path)
    joined = _prepare_attempts(attempts, events, holdout_start, holdout_end)
    trades = _win_loss_trades(joined)

    categorical = categorical_summary(trades)
    numeric = numeric_summary(trades)
    variants = variant_summary(joined)
    hypothesis_rows = hypotheses(numeric)
    summary = _summary(joined, trades, categorical, numeric, hypothesis_rows)

    return {
        "joined_attempts": joined,
        "trade_rows": trades,
        "categorical_summary": categorical,
        "numeric_summary": numeric,
        "variant_summary": variants,
        "hypotheses": hypothesis_rows,
        "summary": summary,
    }


def write_prior_day_sweep_failure_mode_outputs(
    result: dict[str, object],
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    mapping = {
        "joined_attempts": "prior_day_sweep_failure_mode_attempts.csv",
        "trade_rows": "prior_day_sweep_failure_mode_trades.csv",
        "categorical_summary": "prior_day_sweep_failure_mode_categorical.csv",
        "numeric_summary": "prior_day_sweep_failure_mode_numeric.csv",
        "variant_summary": "prior_day_sweep_failure_mode_variants.csv",
        "hypotheses": "prior_day_sweep_failure_mode_hypotheses.csv",
    }
    for key, filename in mapping.items():
        value = result[key]
        assert isinstance(value, pd.DataFrame)
        value.to_csv(output_dir / filename, index=False)
    (output_dir / "prior_day_sweep_failure_mode_summary.json").write_text(
        json.dumps(_json_safe(result["summary"]), indent=2),
        encoding="utf-8",
    )


def _prepare_attempts(
    attempts: pd.DataFrame,
    events: pd.DataFrame,
    holdout_start: str,
    holdout_end: str,
) -> pd.DataFrame:
    event_features = [
        column
        for column in events.columns
        if column == "event_id" or column not in attempts.columns
    ]
    out = attempts.merge(events[event_features], on="event_id", how="left").copy()
    out["session_date"] = pd.to_datetime(out["session_date"], errors="coerce")
    out["pnl_num"] = pd.to_numeric(out["pnl"], errors="coerce")
    out["is_holdout"] = (
        (out["session_date"] >= pd.Timestamp(holdout_start))
        & (out["session_date"] < pd.Timestamp(holdout_end))
    )
    out["trade_result"] = np.select(
        [
            out["status"] != "filled",
            out["pnl_num"] > 0,
            out["pnl_num"] < 0,
        ],
        ["skipped", "win", "loss"],
        default="flat",
    )
    for column in ("level_price", "sweep_price", "ticks_through_level_x"):
        if column in out.columns:
            out[column] = pd.to_numeric(out[column], errors="coerce")
    out["sweep_distance_pts"] = (out["sweep_price"] - out["level_price"]).abs()
    out["sweep_distance_ticks"] = out["sweep_distance_pts"] / 0.25
    out["time_to_reclaim_seconds"] = pd.to_numeric(
        out.get("time_to_reclaim_level_0_30s"),
        errors="coerce",
    )
    out["reclaimed_0_30s"] = out["time_to_reclaim_seconds"].notna()
    for column in NUMERIC_FEATURES:
        if column in out.columns:
            out[column] = pd.to_numeric(out[column], errors="coerce")
    return out


def _win_loss_trades(df: pd.DataFrame) -> pd.DataFrame:
    return df.loc[df["trade_result"].isin(["win", "loss"])].copy()


def _summary(
    joined: pd.DataFrame,
    trades: pd.DataFrame,
    categorical: pd.DataFrame,
    numeric: pd.DataFrame,
    hypotheses: pd.DataFrame,
) -> dict[str, object]:
    return {
        "attempt_rows": int(len(joined)),
        "filled_win_loss_trades": int(len(trades)),
        "wins": int((trades["trade_result"] == "win").sum()),
        "losses": int((trades["trade_result"] == "loss").sum()),
        "holdout_trades": int(trades["is_holdout"].sum()),
        "holdout_wins": int(((trades["is_holdout"]) & (trades["trade_result"] == "win")).sum()),
        "holdout_losses": int(((trades["is_holdout"]) & (trades["trade_result"] == "loss")).sum()),
        "categorical_rows": int(len(categorical)),
        "numeric_rows": int(len(numeric)),
        "top_numeric_hypotheses": _json_safe(hypotheses.head(5).to_dict("records")),
    }


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
